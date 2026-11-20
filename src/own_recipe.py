"""Analyse a recipe written by the user ("Analyse your recipe" tab of the app).

The user writes one ingredient per line, in English, Spanish or Catalan:
    300 g merluza
    200g arroz
    1 kg de patates      (kg is converted to g)

Each ingredient is linked to Agribalyse in this order:
  1. Already confirmed by the team: the 100 labelled ingredient names (EN/ES/CA) in
     data/ingredient_labels.csv. This is the "memory" of human-confirmed matches.
  2. Live AI: the LLM matcher (llm_matching.py) through a local Ollama model, if it is running.
  3. The user chooses: the app shows the closest Agribalyse foods (RapidFuzz on English and
     French names) and the user picks one. Human in the loop when the AI is not available or not sure.
"""
import re

import pandas as pd

from matching import DATA_DIR, load_agribalyse

LINE = re.compile(
    r"^\s*(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|gr|grams?|gramos?|grams)?\.?\s+"
    r"(?:(?:de|of|d')\s+)?(?P<name>.+?)\s*$",
    re.IGNORECASE,
)

SOURCE_KNOWN = "Confirmed before by the team"
SOURCE_LIVE_AI = "AI (live)"
SOURCE_USER = "Chosen by you"


def parse_recipe(text: str) -> tuple[pd.DataFrame, list[str]]:
    """Lines like '300 g merluza' -> DataFrame(ingredient, quantity_g). Also returns unreadable lines."""
    rows, errors = [], []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = LINE.match(raw)
        if not m:
            errors.append(raw.strip())
            continue
        qty = float(m["qty"].replace(",", "."))
        if (m["unit"] or "g").lower() == "kg":
            qty *= 1000
        rows.append({"ingredient": m["name"].strip().lower(), "quantity_g": qty})
    return pd.DataFrame(rows, columns=["ingredient", "quantity_g"]), errors


class RecipeAnalyser:
    def __init__(self, agribalyse: pd.DataFrame | None = None, live_ai=None):
        """live_ai: an object with .match(name) (e.g. LLMMatcher with provider="ollama"), or None."""
        from llm_matching import LLMMatcher

        self.agb = agribalyse if agribalyse is not None else load_agribalyse()
        self.by_code = self.agb.set_index("agribalyse_code")
        labels = pd.read_csv(DATA_DIR / "ingredient_labels.csv", dtype={"agribalyse_code": str})
        self.known = {str(t).strip().lower(): c for t, c in zip(labels["ingredient_text"], labels["agribalyse_code"])}
        self.known.update({str(t).strip().lower(): c for t, c in
                           zip(labels["canonical_ingredient"], labels["agribalyse_code"])})
        self.live_ai = live_ai
        self._retriever = LLMMatcher(agribalyse=self.agb, cache=False, complete=lambda s, u: "{}")

    def _row(self, code: str, source: str) -> dict:
        r = self.by_code.loc[code]
        return {"agribalyse_code": code, "agribalyse_name": r["agribalyse_name"],
                "co2e_per_kg": float(r["co2e_per_kg"]), "source": source}

    def candidates(self, name: str, n: int = 8) -> list[tuple[str, str]]:
        """Closest Agribalyse foods for the user to choose from: [(code, English name)]."""
        rows = self._retriever.retrieve([name], [name])[:n]
        r = self._retriever.agb
        return [(r.at[i, "agribalyse_code"], r.at[i, "agribalyse_name"]) for i in rows]

    def resolve(self, name: str) -> dict:
        """Automatic match for one ingredient, or {'source': None} when the user must choose."""
        key = name.strip().lower()
        if key in self.known:
            code = self.known[key]
            if pd.isna(code):
                return {"agribalyse_code": None, "agribalyse_name": None, "co2e_per_kg": None,
                        "source": "No equivalent in Agribalyse (team)"}
            return self._row(code, SOURCE_KNOWN)
        if self.live_ai is not None:
            r = self.live_ai.match(name)
            if not r["uncertain"] and r["agribalyse_code"]:
                return self._row(r["agribalyse_code"], SOURCE_LIVE_AI)
        return {"agribalyse_code": None, "agribalyse_name": None, "co2e_per_kg": None, "source": None}

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
