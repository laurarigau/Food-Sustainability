"""Run the LLM matcher once on every recipe ingredient and save the answers.

Why: the app should not need a GPU on demo day. The AI answers for the 48 recipe ingredients
are computed once (Colab, notebook 09) and saved to data/ingredient_matches_llm.csv.
The app ("AI + team check") reads this file.

    python src/precompute_matches.py --model Qwen/Qwen2.5-14B-Instruct --verify

Configuration: Qwen2.5-14B-Instruct + verify, the one selected on TUNE in notebook 08.
"""
import argparse

import pandas as pd

from llm_matching import LLMMatcher
from matching import DATA_DIR

OUT_FILE = DATA_DIR / "ingredient_matches_llm.csv"
THRESHOLD = 0.3  # chosen on TUNE in notebook 08 for this configuration


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-14B-Instruct")
    ap.add_argument("--provider", default="hf", choices=["hf", "anthropic", "ollama"])
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    names = sorted(pd.read_csv(DATA_DIR / "recipe_ingredients.csv")["ingredient_clean"].unique())
    m = LLMMatcher(model=args.model, provider=args.provider, threshold=THRESHOLD, verify=args.verify)
    rows = []
    for i, name in enumerate(names, 1):
        r = m.match(name)
        rows.append({k: r[k] for k in ("ingredient", "agribalyse_code", "agribalyse_name", "score",
                                        "uncertain", "rejected_by_verify", "normalised", "reason")})
        print(f"{i:2}/{len(names)}  {name:15} -> {r['agribalyse_name']}  (uncertain={r['uncertain']})")
    out = pd.DataFrame(rows)
    out.insert(0, "model", m.model_name + (" + verify" if args.verify else ""))
    out.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(out)} AI matches to {OUT_FILE}")
    print(f"Confident: {(~out.uncertain).sum()} | uncertain: {out.uncertain.sum()}")


if __name__ == "__main__":
    main()
