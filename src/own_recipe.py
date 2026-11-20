"""Analyse a recipe written by the user ("Analyse your recipe" tab of the app).

The user writes one ingredient per line, in English, Spanish or Catalan:
    300 g merluza
    200g arroz
    1 kg de patates      (kg is converted to g)
    2 huevos / 2 ous     (pieces: typical weight, marked as "estimated")
    2 cucharadas de aceite de oliva, mig kg de patates, tomàquet 400 g

Each ingredient is linked to Agribalyse in this order:
  1. Already confirmed by the team: the 100 labelled ingredient names (EN/ES/CA) in
     data/ingredient_labels.csv. This is the "memory" of human-confirmed matches.
  2. Live AI: the LLM matcher (llm_matching.py) through a local Ollama model, if it is running.
  3. The user chooses: the app shows the closest Agribalyse foods (the AI's own candidates first,
     then RapidFuzz on English and French names) and the user picks one. Human in the loop when the
     AI is not available or not sure. The choice is saved in data/user_confirmations.csv, so next
     time the same ingredient is recognised automatically (dev log 09). That file is NEVER used to
     score the AI (evaluate_matching.py only reads ingredient_labels.csv).

Then suggest_swaps() proposes lower-carbon alternatives for the biggest emitters (e.g. beef -> lentils)
with the saving in kg and %. Same weight is assumed (declared simplification, not a nutrition rule).
"""
import re
from datetime import datetime

import pandas as pd

from matching import DATA_DIR, load_agribalyse

SOURCE_KNOWN = "Confirmed before by the team"
SOURCE_LIVE_AI = "AI (live)"
SOURCE_USER = "Chosen by you"
SOURCE_REMEMBERED = "Chosen before by a user"

CONFIRMATIONS_FILE = DATA_DIR / "user_confirmations.csv"

# ----------------------------------------------------------------------------- parsing
NUMBER_WORDS = {"un": 1, "una": 1, "uno": 1, "a": 1, "an": 1, "one": 1, "dos": 2, "two": 2, "tres": 3,
                "three": 3, "quatre": 4, "cuatro": 4, "four": 4, "cinc": 5, "cinco": 5, "five": 5,
                "mig": 0.5, "mitja": 0.5, "medio": 0.5, "media": 0.5, "half": 0.5}
WEIGHT_UNITS = {"kg": 1000, "kilo": 1000, "kilos": 1000, "g": 1, "gr": 1, "grs": 1, "gramo": 1, "gramos": 1,
                "gram": 1, "grams": 1, "l": 1000, "litro": 1000, "litros": 1000, "litre": 1000, "liter": 1000,
                "ml": 1, "cl": 10, "dl": 100}                     # liquids: 1 ml ~ 1 g
OTHER_UNITS = {                                                   # declared estimates (grams per unit)
    "cucharada": 14, "cucharadas": 14, "cda": 14, "cdas": 14, "cullerada": 14, "cullerades": 14,
    "tbsp": 14, "tablespoon": 14, "tablespoons": 14,
    "cucharadita": 5, "cucharaditas": 5, "cdta": 5, "culleradeta": 5, "culleradetes": 5,
    "tsp": 5, "teaspoon": 5, "teaspoons": 5,
    "taza": 200, "tazas": 200, "tassa": 200, "tasses": 200, "cup": 200, "cups": 200,
    "lata": 400, "latas": 400, "llauna": 400, "llaunes": 400, "can": 400, "cans": 400,
    "diente": 5, "dientes": 5, "gra": 5, "grans": 5, "clove": 5, "cloves": 5,
    "placa": 18, "placas": 18, "làmina": 18, "làmines": 18, "sheet": 18, "sheets": 18,
    "rebanada": 30, "rebanadas": 30, "llesca": 30, "llesques": 30, "slice": 30, "slices": 30,
}
UNITS = {**WEIGHT_UNITS, **OTHER_UNITS}
# typical weight of ONE piece, by keyword (EN / ES / CA). Declared estimates.
PIECE_GRAMS = [
    (r"huevo|\bous?\b|egg", 60), (r"cebolla|ceba|onion", 150), (r"\bajo|\ball\b|garlic", 5),
    (r"tomate|tom[aà]quet|tomato", 120), (r"zanahoria|pastanaga|carrot", 80),
    (r"patata|potato", 170), (r"lim[oó]n|llimona|lemon", 100), (r"pimiento|pebrot|pepper", 150),
    (r"calabac[ií]n|carbass[oó]|zucchini|courgette", 200), (r"aguacate|alvocat|avocado", 170),
    (r"berenjena|alberg[ií]nia|aubergine|eggplant", 250),
]
DEFAULT_PIECE_GRAMS = 100
SERVINGS = re.compile(r"(\d+)\s*(personas|persones|persona|people|servings|raciones|racions|comensales)", re.I)

_NUM = r"(\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)"
_LEAD = re.compile(rf"^\s*(?:{_NUM}|([a-zà-ú]+))\s*([a-zà-ú.]+)?\s*(?:de |d'|d’|of )?(.*)$", re.I)
_TRAIL = re.compile(rf"^(.*?)[\s:,-]+{_NUM}\s*([a-zà-ú.]+)?\s*$", re.I)


def _unit(u: str | None) -> str | None:
    if not u:
        return None
    u = u.lower()
    return u if u in UNITS else (u.rstrip(".") if u.rstrip(".") in UNITS else None)


def _to_number(text: str) -> float:
    text = text.replace(",", ".").replace(" ", "")
    if "/" in text:
        a, b = text.split("/")
        return float(a) / float(b)
    return float(text)


def parse_line(line: str) -> dict | None:
    """'200 g de ternera picada' -> {'ingredient': 'ternera picada', 'quantity_g': 200, 'estimated': False}.
    None when there is no quantity (the line is reported to the user)."""
    line = re.sub(r"^\s*[-*•·–]\s*", "", line.strip())
    line = re.sub(r"^\d+[.)]\s+", "", line)                       # "1. " / "1) "
    line = re.sub(r"\(.*?\)", "", line).strip(" .;")
    qty, unit, name = None, None, line
    m = _LEAD.match(line)
    if m and (m.group(1) or (m.group(2) and m.group(2).lower() in NUMBER_WORDS)):
        qty = _to_number(m.group(1)) if m.group(1) else NUMBER_WORDS[m.group(2).lower()]
        unit, name = m.group(3), m.group(4)
        if unit and not _unit(unit):
            name, unit = f"{unit} {name}".strip(), None             # "2 huevos": "huevos" is the name
    else:
        m = _TRAIL.match(line)
        if m:
            name, qty, unit = m.group(1), _to_number(m.group(2)), m.group(3)
            if unit and not _unit(unit):
                name, unit = f"{name} {unit}", None
    name = re.sub(r"^(de |d'|d’|of )", "", name.strip(), flags=re.I).strip(" ,.-").lower()
    if qty is None or not name:
        return None
    if _unit(unit):
        u = _unit(unit)
        return {"ingredient": name, "quantity_g": round(qty * UNITS[u], 1), "estimated": u not in WEIGHT_UNITS}
    grams = next((g for pattern, g in PIECE_GRAMS if re.search(pattern, name, re.I)), DEFAULT_PIECE_GRAMS)
    return {"ingredient": name, "quantity_g": round(qty * grams, 1), "estimated": True}


def parse_servings(text: str) -> int | None:
    m = SERVINGS.search(text or "")
    return int(m.group(1)) if m else None


def parse_recipe(text: str) -> tuple[pd.DataFrame, list[str]]:
    """One ingredient per line -> DataFrame(ingredient, quantity_g, estimated). Also returns unreadable lines
    (no quantity, e.g. 'sal al gusto'). A title line like 'Lasaña (4 personas)' is ignored."""
    rows, errors = [], []
    for raw in text.splitlines():
        if not raw.strip() or SERVINGS.search(raw) or raw.strip().endswith(":"):
            continue
        r = parse_line(raw)
        if r is None:
            errors.append(raw.strip())
        else:
            rows.append(r)
    return pd.DataFrame(rows, columns=["ingredient", "quantity_g", "estimated"]), errors



class RecipeAnalyser:
    def __init__(self, agribalyse: pd.DataFrame | None = None, live_ai=None,
                 confirmations_file=CONFIRMATIONS_FILE):
        """live_ai: an object with .match(name) (e.g. LLMMatcher with provider="ollama"), or None."""
        from llm_matching import LLMMatcher

        self.agb = agribalyse if agribalyse is not None else load_agribalyse()
        self.by_code = self.agb.set_index("agribalyse_code")
        labels = pd.read_csv(DATA_DIR / "ingredient_labels.csv", dtype={"agribalyse_code": str})
        self.known = {str(t).strip().lower(): c for t, c in zip(labels["ingredient_text"], labels["agribalyse_code"])}
        self.known.update({str(t).strip().lower(): c for t, c in
                           zip(labels["canonical_ingredient"], labels["agribalyse_code"])})
        self.confirmations_file = confirmations_file
        self.remembered: dict[str, str] = {}
        if confirmations_file.exists():
            conf = pd.read_csv(confirmations_file, dtype=str)
            self.remembered = dict(zip(conf["ingredient"], conf["agribalyse_code"]))
        self.live_ai = live_ai
        self._retriever = LLMMatcher(agribalyse=self.agb, cache=False, complete=lambda s, u: "{}")

    def _row(self, code: str, source: str) -> dict:
        r = self.by_code.loc[code]
        return {"agribalyse_code": code, "agribalyse_name": r["agribalyse_name"],
                "co2e_per_kg": float(r["co2e_per_kg"]), "source": source}

    def candidates(self, name: str, n: int = 8, first: list[str] | None = None) -> list[tuple[str, str]]:
        """Closest Agribalyse foods for the user to choose from: [(code, English name)].
        `first`: codes to show on top (the live AI's own candidates, when it was not sure)."""
        rows = self._retriever.retrieve([name], [name])[:n]
        r = self._retriever.agb
        codes = list(dict.fromkeys([c for c in (first or []) if c in self.by_code.index]
                                   + [r.at[i, "agribalyse_code"] for i in rows]))[:n]
        return [(c, self.by_code.at[c, "agribalyse_name"]) for c in codes]

    def remember(self, name: str, code: str) -> None:
        """Save the user's choice: next time this ingredient is recognised automatically."""
        key = name.strip().lower()
        self.remembered[key] = code
        row = pd.DataFrame([{"ingredient": key, "agribalyse_code": code,
                             "agribalyse_name": self.by_code.at[code, "agribalyse_name"],
                             "chosen_at": datetime.now().isoformat(timespec="seconds")}])
        old = (pd.read_csv(self.confirmations_file, dtype=str) if self.confirmations_file.exists()
               else row.iloc[0:0])
        pd.concat([old[old["ingredient"] != key], row], ignore_index=True).to_csv(self.confirmations_file, index=False)

    def resolve(self, name: str) -> dict:
        """Automatic match for one ingredient, or {'source': None} when the user must choose."""
        key = name.strip().lower()
        if key not in self.known:                      # simple plural: "cebollas" -> "cebolla", "ous" -> "ou"
            key = next((k for k in (key[:-1], key[:-2]) if key.endswith("s") and k in self.known), key)
        if key in self.known:
            code = self.known[key]
            if pd.isna(code):
                return {"agribalyse_code": None, "agribalyse_name": None, "co2e_per_kg": None,
                        "source": "No equivalent in Agribalyse (team)"}
            return self._row(code, SOURCE_KNOWN)
        if self.remembered.get(key) in self.by_code.index:
            return self._row(self.remembered[key], SOURCE_REMEMBERED)
        candidate_codes = []
        if self.live_ai is not None:
            try:
                r = self.live_ai.match(name)
            except Exception:                        # Ollama stopped, timeout...: the user chooses
                r = {"uncertain": True, "agribalyse_code": None}
            if not r["uncertain"] and r["agribalyse_code"]:
                return self._row(r["agribalyse_code"], SOURCE_LIVE_AI)
            candidate_codes = list(r.get("candidate_codes") or [])
        return {"agribalyse_code": None, "agribalyse_name": None, "co2e_per_kg": None, "source": None,
                "candidate_codes": candidate_codes}

    def co2e(self, parsed: pd.DataFrame, choices: dict[str, str] | None = None,
             resolved: dict[str, dict] | None = None) -> pd.DataFrame:
        """kg CO2e per ingredient. `choices` = {ingredient: code} picked by the user;
        `resolved` = answers of resolve() already computed (avoids asking the live AI twice)."""
        choices, resolved = choices or {}, resolved or {}
        rows = []
        for _, p in parsed.iterrows():
            if choices.get(p["ingredient"]):
                m = self._row(choices[p["ingredient"]], SOURCE_USER)
            else:
                m = resolved.get(p["ingredient"]) or self.resolve(p["ingredient"])
            kg = None if m["co2e_per_kg"] is None else p["quantity_g"] / 1000 * m["co2e_per_kg"]
            rows.append({**p.to_dict(), **m, "kg_co2e": kg})
        return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- swaps
# Role of a food, from its Agribalyse English name. Alternatives = canonical ingredients of
# data/ingredient_labels.csv (team-verified codes). Same-weight swap: declared simplification.
FAMILIES = [
    ("red meat", r"^(beef|veal|lamb|mutton|horse)\b", ["lentil", "chickpea", "chicken"]),
    ("pork", r"^(pork|ham|bacon|spicy pork sausage|sausage|chorizo|dry-cured)", ["chicken", "white bean", "tofu"]),
    ("poultry", r"^(chicken|turkey|duck)\b", ["tofu", "chickpea", "lentil"]),
    ("shellfish", r"^(shrimp|prawn|lobster|crab|langoustine)", ["hake", "tofu", "chickpea"]),
    ("fish", r"^(salmon|tuna|cod|hake|european hake|sea bass|trout|sole)", ["chickpea", "tofu", "lentil"]),
    ("butter", r"^butter\b", ["olive oil"]),
    ("cheese", r"cheese\b", []),            # no like-for-like swap: suggest using half
]
MIN_CO2E_PER_KG = 4.0                         # only suggest swaps for high-impact foods


def family_of(agribalyse_name) -> tuple[str | None, list[str]]:
    if not isinstance(agribalyse_name, str):
        return None, []
    for fam, pattern, alts in FAMILIES:
        if re.search(pattern, agribalyse_name.lower()):
            return fam, alts
    return None, []


def suggest_swaps(result: pd.DataFrame, agribalyse: pd.DataFrame, max_per_ingredient: int = 2) -> list[dict]:
    """Lower-carbon alternatives for the high-impact ingredients of an analysed recipe (output of co2e()).
    [{ingredient, quantity_g, swap_to, swap_code, kg_saved, pct_of_recipe}], biggest saving first.
    swap_to = "half" means: use half the amount (no like-for-like swap, e.g. cheese)."""
    lab = pd.read_csv(DATA_DIR / "ingredient_labels.csv", dtype=str).dropna(subset=["agribalyse_code"])
    alt_code = dict(zip(lab["canonical_ingredient"], lab["agribalyse_code"].str.strip()))
    co2 = dict(zip(agribalyse["agribalyse_code"], pd.to_numeric(agribalyse["co2e_per_kg"], errors="coerce")))
    known = result.dropna(subset=["kg_co2e"])
    total = float(known["kg_co2e"].sum())
    out = []
    for _, r in known.iterrows():
        if r["co2e_per_kg"] < MIN_CO2E_PER_KG or r["quantity_g"] <= 0:
            continue
        fam, alts = family_of(r["agribalyse_name"])
        options = []
        for a in alts:
            code = alt_code.get(a)
            if code in co2 and co2[code] < r["co2e_per_kg"]:
                options.append({"swap_to": a, "swap_code": code,
                                "kg_saved": r["quantity_g"] / 1000 * (r["co2e_per_kg"] - co2[code])})
        if fam is not None and not options:
            options.append({"swap_to": "half", "swap_code": None, "kg_saved": r["kg_co2e"] / 2})
        options.sort(key=lambda o: -o["kg_saved"])
        for o in options[:max_per_ingredient]:
            out.append({"ingredient": r["ingredient"], "quantity_g": r["quantity_g"], **o,
                        "pct_of_recipe": float(o["kg_saved"] / total) if total else 0.0})
    return sorted(out, key=lambda o: -o["kg_saved"])


def apply_swaps(result: pd.DataFrame, swaps: list[dict], agribalyse: pd.DataFrame) -> pd.DataFrame:
    """The analysed recipe with the chosen swaps applied (what-if)."""
    by_code = agribalyse.set_index("agribalyse_code")
    out = result.copy()
    for s in swaps:
        i = out.index[out["ingredient"] == s["ingredient"]][0]
        if s["swap_code"] is None:                  # "half"
            out.at[i, "quantity_g"] = out.at[i, "quantity_g"] / 2
        else:
            out.at[i, "agribalyse_code"] = s["swap_code"]
            out.at[i, "agribalyse_name"] = by_code.at[s["swap_code"], "agribalyse_name"]
            out.at[i, "co2e_per_kg"] = float(by_code.at[s["swap_code"], "co2e_per_kg"])
        out.at[i, "kg_co2e"] = out.at[i, "quantity_g"] / 1000 * out.at[i, "co2e_per_kg"]
    return out
