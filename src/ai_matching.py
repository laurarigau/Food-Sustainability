"""AI ingredient matcher: multilingual sentence embeddings + FAISS nearest-neighbour search.

It finds the Agribalyse food whose name is closest in MEANING (not in letters),
so "garbanzos", "cigrons" and "chickpea" can all land on "Chick pea, canned, drained".

Same output format as RapidFuzzMatcher, so the rest of the pipeline does not change.
Score = cosine similarity (0-1). Below the threshold the match is "uncertain".

Options (revision 2, chosen on the TUNE split only):
  - candidates: which Agribalyse foods can be returned
        "all"   : every food (revision 1)
        "light" : no desserts, sweets, baby food, alcohol, pizzas/tarts, sandwiches, soups, starters
        "strict": "light" + no composite dishes (plats composés) and no composed salads
  - passage: text embedded for each Agribalyse food
        "en"    : English name (LCI Name)
        "en_fr" : English name + French name (closer to Spanish/Catalan words)

Needs: pip install -r requirements-ai.txt   (run it in Google Colab)
"""
import numpy as np
import pandas as pd

from matching import load_agribalyse

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # best on tune in revision 1
DEFAULT_THRESHOLD = 0.70
DEFAULT_CANDIDATES = "all"
DEFAULT_PASSAGE = "en"

CANDIDATE_MODELS = [
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "intfloat/multilingual-e5-small",
    "sentence-transformers/LaBSE",      # trained to align translations (word level too)
    "BAAI/bge-m3",                      # strong multilingual retrieval model
]

EXCLUDED_GROUPS = {"produits sucrés", "glaces et sorbets", "aliments infantiles"}
EXCLUDED_SUBGROUPS_LIGHT = {
    "feuilletées et autres entrées", "pizzas, tartes et crêpes salées", "sandwichs", "soupes",
    "gâteaux et pâtisseries", "céréales de petit-déjeuner et biscuits", "boisson alcoolisées", "eaux",
}
EXCLUDED_SUBGROUPS_STRICT = EXCLUDED_SUBGROUPS_LIGHT | {"plats composés", "salades composées et crudités"}

_ENCODERS: dict = {}
_PASSAGE_CACHE: dict = {}


def filter_candidates(agb: pd.DataFrame, candidates: str) -> pd.DataFrame:
    if candidates == "all":
        return agb.reset_index(drop=True)
    excluded = EXCLUDED_SUBGROUPS_LIGHT if candidates == "light" else EXCLUDED_SUBGROUPS_STRICT
    keep = ~agb["group"].isin(EXCLUDED_GROUPS) & ~agb["subgroup"].isin(excluded)
    return agb[keep].reset_index(drop=True)


def _prefixes(model_name: str) -> tuple[str, str]:
    # E5 models expect "query: " / "passage: " prefixes
    return ("query: ", "passage: ") if "e5" in model_name.lower() else ("", "")


def _get_encoder(model_name: str):
    if model_name not in _ENCODERS:
        from sentence_transformers import SentenceTransformer
        _ENCODERS[model_name] = SentenceTransformer(model_name)
    return _ENCODERS[model_name]


class EmbeddingMatcher:
    def __init__(self, agribalyse: pd.DataFrame | None = None, model_name: str = DEFAULT_MODEL,
                 threshold: float = DEFAULT_THRESHOLD, candidates: str = DEFAULT_CANDIDATES,
                 passage: str = DEFAULT_PASSAGE, encoder=None):
        import faiss

        agb_all = agribalyse if agribalyse is not None else load_agribalyse()
        self.model_name, self.threshold = model_name, threshold
        self.candidates, self.passage = candidates, passage
        self.encoder = encoder if encoder is not None else _get_encoder(model_name)
        self.q_prefix, self.p_prefix = _prefixes(model_name)

        # Encode every Agribalyse food once per (model, passage) and reuse it for every candidate filter
        key = (model_name, passage, id(self.encoder) if encoder is not None else None)
        if key not in _PASSAGE_CACHE:
            if passage == "en_fr":
                texts = (agb_all["agribalyse_name"] + " / " + agb_all["name_fr"].fillna("")).tolist()
            else:
                texts = agb_all["agribalyse_name"].tolist()
            _PASSAGE_CACHE[key] = (agb_all["agribalyse_code"].tolist(),
                                   self._encode([self.p_prefix + t for t in texts]))
        codes, emb = _PASSAGE_CACHE[key]
        pos = {c: i for i, c in enumerate(codes)}

        self.agb = filter_candidates(agb_all, candidates)
        sub = emb[[pos[c] for c in self.agb["agribalyse_code"]]]
        self.index = faiss.IndexFlatIP(sub.shape[1])  # inner product = cosine on normalised vectors
        self.index.add(np.ascontiguousarray(sub))

    def _encode(self, texts: list[str]) -> np.ndarray:
        emb = self.encoder.encode(texts, normalize_embeddings=True, convert_to_numpy=True,
                                  batch_size=64, show_progress_bar=False)
        return np.asarray(emb, dtype="float32")

    def match_many(self, ingredients: list[str]) -> list[dict]:
        q = self._encode([self.q_prefix + i.lower().strip() for i in ingredients])
        scores, idx = self.index.search(q, 1)
        out = []
        for ing, s, i in zip(ingredients, scores[:, 0], idx[:, 0]):
            row = self.agb.iloc[int(i)]
            uncertain = float(s) < self.threshold
            out.append({
                "ingredient": ing,
                "agribalyse_code": row["agribalyse_code"],
                "agribalyse_name": row["agribalyse_name"],
                "co2e_per_kg": None if uncertain else float(row["co2e_per_kg"]),
                "score": float(s),
                "uncertain": bool(uncertain),
            })
        return out

    def match(self, ingredient: str) -> dict:
        return self.match_many([ingredient])[0]


if __name__ == "__main__":
    m = EmbeddingMatcher()
    for r in m.match_many(["chickpea", "garbanzos", "cigrons", "chorizo", "tomato", "pollo", "mushroom"]):
        print(r)
