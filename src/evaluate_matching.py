"""Evaluate an ingredient matcher against the hand-verified labels.

Usage:
    python src/evaluate_matching.py            # choose threshold on TUNE, report TEST
    python src/evaluate_matching.py --details  # also print every TEST row

A prediction is correct when:
  - the label has an Agribalyse code and the matcher returns that code (not uncertain), or
  - the label is "NO MATCH" and the matcher says "uncertain".
"""
import argparse
from pathlib import Path

import pandas as pd

from matching import DATA_DIR, RapidFuzzMatcher

LABELS_FILE = DATA_DIR / "ingredient_labels.csv"


def is_correct(label_code, pred: dict) -> bool:
    if pd.isna(label_code) or str(label_code).strip() == "":
        return pred["uncertain"]
    return (not pred["uncertain"]) and str(pred["agribalyse_code"]) == str(label_code).strip()


def run(matcher, labels: pd.DataFrame) -> pd.DataFrame:
    preds = [matcher.match(t) for t in labels["ingredient_text"]]
    out = labels[["label_id", "ingredient_text", "language", "split", "agribalyse_code", "agribalyse_name"]].copy()
    out["pred_code"] = [p["agribalyse_code"] for p in preds]
    out["pred_name"] = [p["agribalyse_name"] for p in preds]
    out["score"] = [p["score"] for p in preds]
    out["uncertain"] = [p["uncertain"] for p in preds]
    out["correct"] = [is_correct(c, p) for c, p in zip(labels["agribalyse_code"], preds)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--details", action="store_true")
    args = ap.parse_args()

    labels = pd.read_csv(LABELS_FILE, dtype={"agribalyse_code": str})
    matcher = RapidFuzzMatcher()

    # 1. Choose the "uncertain" threshold on TUNE only
    tune = labels[labels.split == "tune"]
    best_t, best_acc = None, -1.0
    for t in range(0, 101, 5):
        matcher.threshold = t
        acc = run(matcher, tune)["correct"].mean()
        if acc > best_acc:
            best_t, best_acc = t, acc
    matcher.threshold = best_t
    print(f"Threshold chosen on TUNE: {best_t}  (tune accuracy {best_acc:.0%})")

    # 2. Report on TEST (never used to choose anything)
    test = run(matcher, labels[labels.split == "test"])
    n = len(test)
    print(f"\nRapidFuzz baseline on TEST: {test.correct.sum()}/{n} correct ({test.correct.mean():.0%})")
    print(test.groupby("language")["correct"].agg(["sum", "count"]).rename(columns={"sum": "correct", "count": "n"}))

    if args.details:
        pd.set_option("display.width", 200, "display.max_colwidth", 45)
        print(test[["ingredient_text", "agribalyse_name", "pred_name", "score", "uncertain", "correct"]].to_string(index=False))

    out_file = DATA_DIR / "results_rapidfuzz_test.csv"
    test.to_csv(out_file, index=False)
    print(f"\nSaved row-by-row results to {out_file.relative_to(DATA_DIR.parent)}")


if __name__ == "__main__":
    main()
