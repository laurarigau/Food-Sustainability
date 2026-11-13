"""Ingredient -> Agribalyse matching.

Baseline: RapidFuzz string matching on the English Agribalyse names (LCI Name).
The AI matcher (sentence-transformers + FAISS) will expose the same function
signature, so the rest of the pipeline does not need to change.

Output of every matcher (agreed format):
    {"ingredient": str, "agribalyse_code": str | None, "agribalyse_name": str | None,
     "co2e_per_kg": float | None, "score": float, "uncertain": bool}
"""
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AGRIBALYSE_FILE = DATA_DIR / "agribalyse_synthese.csv"

# Below this score (0-100) the match is flagged as "uncertain" and no CO2e is shown.
# 75 = value chosen on the TUNE split by evaluate_matching.py (see dev log 05).
DEFAULT_THRESHOLD = 75


def load_agribalyse(path: Path = AGRIBALYSE_FILE) -> pd.DataFrame:
    """Load Agribalyse synthese and keep one row per food code."""
    df = pd.read_csv(path, sep=None, engine="python")
    df = df.dropna(subset=["Code AGB", "LCI Name"]).drop_duplicates("Code AGB")
    df = df.rename(columns={
        "Code AGB": "agribalyse_code",
        "LCI Name": "agribalyse_name",
        "Changement climatique": "co2e_per_kg",
        "Nom du Produit en Français": "name_fr",
        "Groupe d'aliment": "group",
        "Sous-groupe d'aliment": "subgroup",
    })
    df["agribalyse_code"] = df["agribalyse_code"].astype(str).str.strip()
    cols = ["agribalyse_code", "agribalyse_name", "co2e_per_kg", "name_fr", "group", "subgroup"]
    return df[cols].reset_index(drop=True)


class RapidFuzzMatcher:
    """Finds the Agribalyse food whose name is most similar, letter by letter."""

    def __init__(self, agribalyse: pd.DataFrame | None = None, threshold: float = DEFAULT_THRESHOLD):
        self.agb = agribalyse if agribalyse is not None else load_agribalyse()
        self.names = self.agb["agribalyse_name"].str.lower().tolist()
        self.threshold = threshold

    def match(self, ingredient: str) -> dict:
        query = ingredient.lower().strip()
        name, score, idx = process.extractOne(query, self.names, scorer=fuzz.WRatio)
        row = self.agb.iloc[idx]
        uncertain = score < self.threshold
        return {
            "ingredient": ingredient,
            "agribalyse_code": row["agribalyse_code"],
            "agribalyse_name": row["agribalyse_name"],
            "co2e_per_kg": None if uncertain else float(row["co2e_per_kg"]),
            "score": float(score),
            "uncertain": bool(uncertain),
        }


if __name__ == "__main__":
    m = RapidFuzzMatcher()
    for ing in ["chickpea", "garbanzos", "chorizo", "tomato", "mushroom"]:
        print(m.match(ing))
