"""AI ingredient matcher: multilingual sentence embeddings + FAISS nearest-neighbour search.

It finds the Agribalyse food whose name is closest in MEANING (not in letters),
so "garbanzos", "cigrons" and "chickpea" can all land on "Chick pea, canned, drained".

Same output format as RapidFuzzMatcher, so the rest of the pipeline does not change.
Score = cosine similarity (0-1). Below the threshold the match is "uncertain".

Needs: pip install -r requirements-ai.txt   (run it in Google Colab)
"""
import numpy as np
import pandas as pd

from matching import load_agribalyse

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_THRESHOLD = 0.5  # choose it on the TUNE split only (see evaluate_matching.py)

# Candidate models to compare on the tune split (all multilingual, small enough for Colab)
CANDIDATE_MODELS = [
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "intfloat/multilingual-e5-small",
]


def _prefixes(model_name: str) -> tuple[str, str]:
    # E5 models expect "query: " / "passage: " prefixes
    return ("query: ", "passage: ") if "e5" in model_name.lower() else ("", "")


class EmbeddingMatcher:
    def __init__(self, agribalyse: pd.DataFrame | None = None, model_name: str = DEFAULT_MODEL,
                 threshold: float = DEFAULT_THRESHOLD, encoder=None):
        import faiss

        self.agb = agribalyse if agribalyse is not None else load_agribalyse()
        self.model_name = model_name
        self.threshold = threshold
        if encoder is None:
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer(model_name)
        self.encoder = encoder
        self.q_prefix, self.p_prefix = _prefixes(model_name)

        passages = [self.p_prefix + n for n in self.agb["agribalyse_name"].tolist()]
        emb = self._encode(passages)
        self.index = faiss.IndexFlatIP(emb.shape[1])  # inner product = cosine on normalised vectors
        self.index.add(emb)

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
