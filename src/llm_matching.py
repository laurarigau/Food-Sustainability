"""LLM ingredient matcher: "retrieve, then let an LLM choose".

Why: the embedding matcher (ai_matching.py) fails mostly on Spanish/Catalan words and on
food *state* (raw vs cooked, canned vs dry). An LLM knows that "merluza" is hake and that a
recipe weight is usually raw, so we use it in two small steps:

  1. NORMALISE  — the LLM turns the ingredient (any language) into an English and a French
                  search name, e.g. "merluza" -> "hake, raw" / "merlu, cru".
  2. RETRIEVE   — RapidFuzz finds the top-k Agribalyse foods for those names
                  (English LCI Name + French name, candidates filtered like ai_matching "strict").
                  Cheap, local, no big model to download.
  3. CHOOSE     — the LLM gets the numbered candidates and returns ONE code or NONE,
                  plus a confidence (high / medium / low).
  4. VERIFY     — (optional, verify=True) a second, simple yes/no question: "is <chosen food> the
                  same food as <ingredient>?". If the answer is no, the match becomes "uncertain".
                  This turns absurd picks (arroz -> "Carrot, canned") into "no number shown".

Same output format as RapidFuzzMatcher, so the rest of the pipeline does not change.
Score = confidence mapped to a number (high 1.0, medium 0.6, low 0.3, NONE 0.0).
Below the threshold the match is "uncertain" (the threshold is chosen on TUNE, like the others).

The LLM only sees general labelling rules (the team criteria of dev log 05, written in general
form). No TEST label is shown to it.

Few-shot (fewshot=True, dev log 09): the NORMALISE step also gets a few worked examples, all taken
from the TUNE split (Catalan and Spanish words), because most remaining errors were Catalan words
the model did not translate. TUNE is the split we are allowed to learn from; TEST stays untouched.

Every LLM answer is stored in data/llm_cache.json, so a run can be repeated for free and the
results are reproducible. Delete the file (or use cache=False) to ask the LLM again.

Two providers (choose with provider=...):
  - "hf"        : free, open model run locally with transformers (default Qwen/Qwen2.5-7B-Instruct,
                  4-bit). Run it in Google Colab with a GPU: notebooks/07_llm_matching_colab.ipynb
  - "anthropic" : Claude API (pip install anthropic; export ANTHROPIC_API_KEY=...)
  - "ollama"    : free local model on a laptop (https://ollama.com, then `ollama pull qwen2.5:7b`).
                  Used by the app's "Analyse your recipe" tab when Ollama is running.
Any other provider: pass `complete=my_function`, where my_function(system, user) -> str.
"""
import hashlib
import json
import os
import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from matching import DATA_DIR, load_agribalyse

DEFAULT_PROVIDER = "hf"
DEFAULT_MODELS = {"hf": "Qwen/Qwen2.5-7B-Instruct", "anthropic": "claude-haiku-5-5", "ollama": "qwen2.5:7b"}
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_THRESHOLD = 0.6          # placeholder; evaluate_matching.py chooses it on TUNE
DEFAULT_K = 20                   # candidates shown to the LLM
CACHE_FILE = DATA_DIR / "llm_cache.json"
CONFIDENCE_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.3}

# Same exclusions as ai_matching "light": no sweets, pizzas, soups, sandwiches...
# NOT "strict": Agribalyse files "Tofu, plain" under "plats composés", so strict would remove it.
# The LLM rejects composed dishes itself.
EXCLUDED_GROUPS = {"produits sucrés", "glaces et sorbets", "aliments infantiles"}
EXCLUDED_SUBGROUPS = {
    "feuilletées et autres entrées", "pizzas, tartes et crêpes salées", "sandwichs", "soupes",
    "gâteaux et pâtisseries", "céréales de petit-déjeuner et biscuits", "boisson alcoolisées", "eaux",
}

NORMALISE_SYSTEM = """You help link recipe ingredients to the Agribalyse food database (French, names in English and French).
The ingredient can be in English, Spanish or Catalan.
Return ONLY a JSON object:
{"english": "<plain food name in English, as a food database would write it>",
 "synonyms": ["<up to 3 other English names a food database could use, e.g. 'garden peas', 'haricot bean'>"],
 "french": "<the same food in French>",
 "state": "<raw | dry | canned | cooked | fresh | other>"}
Rules: recipe weights are for the ingredient as bought, so prefer raw (meat, fish, vegetables), dry (rice, pasta)
or canned (beans in a can). Give the base food, never a dish (e.g. "salmon", not "salmon pie")."""

CHOOSE_SYSTEM = """You link one recipe ingredient to ONE food of the Agribalyse database.
You get the ingredient and a numbered list of candidate foods. Choose the candidate that is the SAME food.
Labelling rules of our team:
- Same food first, then the right state. Recipe weights are as bought: raw for meat, fish, eggs and vegetables;
  dry/raw for rice and pasta; canned and drained for beans/chickpeas sold in cans.
- For a generic ingredient ("beef", "chicken") a common plain cut is fine (minced beef, chicken breast).
- Never choose a dish, sauce, oil, juice, salt, sweet or a product that only CONTAINS the food
  (e.g. not "celery salt" for celery, not "salmon oil" for salmon, not "lemon juice" for lemon).
- If no candidate is the same food, answer NONE. Do not use a different food as a substitute.
Return ONLY a JSON object: {"code": "<candidate code or NONE>", "confidence": "high|medium|low", "reason": "<max 12 words>"}"""

# Worked examples for the NORMALISE step. ONLY TUNE-split words (data/ingredient_labels.csv, split=tune).
FEWSHOT_EXAMPLES = """
Examples (Catalan words often look nothing like Spanish: translate from Catalan when the word is not Spanish):
- "llenties" (Catalan) -> {"english": "lentil", "synonyms": ["lentils"], "french": "lentille", "state": "dry"}
- "lluç" (Catalan) -> {"english": "hake", "synonyms": ["european hake"], "french": "merlu", "state": "raw"}
- "tonyina" (Catalan) -> {"english": "tuna", "synonyms": ["tuna, canned"], "french": "thon", "state": "canned"}
- "ou" (Catalan) -> {"english": "egg", "synonyms": ["hen egg"], "french": "oeuf", "state": "raw"}
- "pebrot" (Catalan) -> {"english": "sweet pepper", "synonyms": ["bell pepper"], "french": "poivron", "state": "raw"}
- "judías blancas" (Spanish) -> {"english": "haricot bean", "synonyms": ["white bean"], "french": "haricot blanc", "state": "canned"}"""

VERIFY_SYSTEM = """Check a link between a recipe ingredient and a food database entry.
The ingredient can be in English, Spanish or Catalan. Translate it in your head first.
Answer "yes" if the database food IS the same food (a different state, cut or preparation is still "yes":
"lentil" and "Lentil, dried" -> yes; "beef" and "Beef, steak, raw" -> yes).
Answer "no" if it is a different food, or a product that only contains it or is made from it
("arroz" and "Carrot, canned" -> no; "lemon" and "Lemon juice" -> no).
Return ONLY a JSON object: {"same_food": "yes|no"}"""


_LEGACY_PROMPTS = {NORMALISE_SYSTEM, CHOOSE_SYSTEM, VERIFY_SYSTEM}


def hf_complete(model_name: str = DEFAULT_MODELS["hf"], load_in_4bit: bool = True):
    """Return complete(system, user) -> str with an open model (greedy decoding = reproducible).

    On a GPU the model is loaded in 4-bit (fits the free Colab T4). Needs:
        pip install transformers accelerate bitsandbytes
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_name)
    kwargs = {"device_map": "auto"}
    if load_in_4bit and torch.cuda.is_available():
        from transformers import BitsAndBytesConfig
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    else:
        kwargs["torch_dtype"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
    model.eval()

    def complete(system: str, user: str) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=150, do_sample=False,
                                 pad_token_id=tok.pad_token_id or tok.eos_token_id)
        return tok.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    return complete


def ollama_available(timeout: float = 0.5) -> bool:
    """True when an Ollama server is running on this computer."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=timeout):
            return True
    except Exception:
        return False


def ollama_complete(model: str = DEFAULT_MODELS["ollama"]):
    """Return complete(system, user) -> str using a local Ollama model (temperature 0)."""
    import urllib.request

    def complete(system: str, user: str) -> str:
        body = json.dumps({"model": model, "stream": False, "options": {"temperature": 0},
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["message"]["content"]

    return complete


def anthropic_complete(model: str = DEFAULT_MODELS["anthropic"]):
    """Return complete(system, user) -> str using the Anthropic API (temperature 0)."""
    import anthropic

    client = anthropic.Anthropic()

    def complete(system: str, user: str) -> str:
        msg = client.messages.create(model=model, max_tokens=200, temperature=0, system=system,
                                     messages=[{"role": "user", "content": user}])
        return msg.content[0].text

    return complete


def parse_json(text: str) -> dict:
    """First {...} block of the LLM answer; {} if there is none."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


class LLMMatcher:
    def __init__(self, agribalyse: pd.DataFrame | None = None, model: str | None = None,
                 provider: str = DEFAULT_PROVIDER,
                 threshold: float = DEFAULT_THRESHOLD, k: int = DEFAULT_K, complete=None,
                 cache: bool = True, cache_file: Path = CACHE_FILE, verify: bool = False,
                 fewshot: bool = False):
        agb = agribalyse if agribalyse is not None else load_agribalyse()
        keep = ~agb["group"].isin(EXCLUDED_GROUPS) & ~agb["subgroup"].isin(EXCLUDED_SUBGROUPS)
        self.agb = agb[keep].reset_index(drop=True)
        self.by_code = self.agb.set_index("agribalyse_code")
        self.names_en = self.agb["agribalyse_name"].str.lower().tolist()
        self.names_fr = self.agb["name_fr"].fillna("").str.lower().tolist()
        self.provider = provider
        self.model_name = model or DEFAULT_MODELS[provider]
        self.threshold, self.k, self.verify, self.fewshot = threshold, k, verify, fewshot
        self._complete = complete
        self.cache_file, self.use_cache = cache_file, cache
        self.cache = json.loads(cache_file.read_text()) if cache and cache_file.exists() else {}

    # --- LLM calls (cached) -------------------------------------------------------------
    def _ask(self, system: str, user: str) -> dict:
        # old prompts keep their old cache key (existing caches still work); new prompts use a hash
        tag = system[:40] if system in _LEGACY_PROMPTS else hashlib.sha1(system.encode()).hexdigest()[:12]
        key = f"{self.model_name}||{tag}||{user}"
        if key not in self.cache:
            if self._complete is None:
                make = {"hf": hf_complete, "anthropic": anthropic_complete, "ollama": ollama_complete}[self.provider]
                self._complete = make(self.model_name)
            self.cache[key] = self._complete(system, user)
            if self.use_cache:
                self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1))
        return parse_json(self.cache[key])

    # --- steps ----------------------------------------------------------------------------
    def normalise(self, ingredient: str) -> dict:
        system = NORMALISE_SYSTEM + FEWSHOT_EXAMPLES if self.fewshot else NORMALISE_SYSTEM
        return self._ask(system, f"Ingredient: {ingredient}")

    def retrieve(self, queries_en: list[str], queries_fr: list[str]) -> list[int]:
        """Candidate rows for the LLM.

        a) Agribalyse names start with the food ("Beef, minced steak...", "Potato, peeled, raw"),
           so every food whose name STARTS with the query's head word is a candidate (the 25 closest per query).
        b) Plus the top-k RapidFuzz matches over English and French names.
        """
        best: dict[int, float] = {}
        for queries, names in ((queries_en, self.names_en), (queries_fr, self.names_fr)):
            for q in filter(None, (s.lower().strip() for s in queries)):
                head = re.split(r"[,(]", q)[0].strip()
                starts = [i for i, n in enumerate(names) if head and re.match(rf"{re.escape(head)}s?\b", n)]
                # many foods can start with "beef": keep the 25 closest to the full query ("beef, raw")
                for i in sorted(starts, key=lambda i: -fuzz.token_set_ratio(q, names[i]))[:25]:
                    best[i] = max(best.get(i, 0), 101)      # always kept
                for _, score, idx in process.extract(q, names, scorer=fuzz.WRatio, limit=self.k):
                    best[idx] = max(best.get(idx, 0), score)
        return sorted(best, key=best.get, reverse=True)[: 2 * self.k]

    def choose(self, ingredient: str, rows: list[int]) -> dict:
        lines = [f"{self.agb.at[i, 'agribalyse_code']} | {self.agb.at[i, 'agribalyse_name']} | "
                 f"{self.agb.at[i, 'name_fr']}" for i in rows]
        user = f"Ingredient: {ingredient}\n\nCandidates (code | English name | French name):\n" + "\n".join(lines)
        return self._ask(CHOOSE_SYSTEM, user)

    def same_food(self, ingredient: str, code: str) -> bool:
        row = self.by_code.loc[code]
        user = f"Ingredient: {ingredient}\nDatabase food: {row['agribalyse_name']} / {row['name_fr']}"
        return str(self._ask(VERIFY_SYSTEM, user).get("same_food", "no")).lower().startswith("y")

    # --- public API (same format as the other matchers) -----------------------------------
    def match(self, ingredient: str) -> dict:
        norm = self.normalise(ingredient)
        syn = norm.get("synonyms") or []
        q_en = [norm.get("english", ""), *(syn if isinstance(syn, list) else [syn]), ingredient]
        q_fr = [norm.get("french", "")]
        rows = self.retrieve(q_en, q_fr)
        pick = self.choose(ingredient, rows)

        code = str(pick.get("code", "NONE")).strip()
        valid = code in set(self.agb.loc[rows, "agribalyse_code"])
        score = CONFIDENCE_SCORE.get(str(pick.get("confidence", "")).lower(), 0.0) if valid else 0.0
        rejected = bool(valid and self.verify and not self.same_food(ingredient, code))
        if rejected:
            score = 0.0              # keep the code for the error analysis, but show no number
        uncertain = score < self.threshold
        row = self.by_code.loc[code] if valid else None
        return {
            "ingredient": ingredient,
            "agribalyse_code": code if valid else None,
            "agribalyse_name": row["agribalyse_name"] if valid else None,
            "co2e_per_kg": None if (uncertain or not valid) else float(row["co2e_per_kg"]),
            "score": score,
            "uncertain": bool(uncertain),
            # extra fields (ignored by the rest of the pipeline, useful in the app / for review)
            "normalised": norm.get("english"),
            "reason": pick.get("reason"),
            "rejected_by_verify": rejected,
            "candidates": self.agb.loc[rows[:5], "agribalyse_name"].tolist(),
            # for the "you choose" step in the app: the LLM's own pick first, then the next candidates
            "candidate_codes": list(dict.fromkeys(
                ([code] if valid else []) + self.agb.loc[rows[:8], "agribalyse_code"].tolist())),
        }

    def match_many(self, ingredients: list[str]) -> list[dict]:
        return [self.match(i) for i in ingredients]


if __name__ == "__main__":
    m = LLMMatcher()
    for r in m.match_many(["merluza", "cigrons", "pollo", "xampinyons", "lemon"]):
        print({k: r[k] for k in ("ingredient", "normalised", "agribalyse_name", "score", "uncertain", "reason")})
