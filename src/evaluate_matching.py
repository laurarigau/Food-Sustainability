"""Evaluate an ingredient matcher against the hand-verified labels.

Usage:
    python src/evaluate_matching.py                       # RapidFuzz baseline
    python src/evaluate_matching.py --matcher ai          # AI matcher (default model)
    python src/evaluate_matching.py --matcher ai --model intfloat/multilingual-e5-small
    python src/evaluate_matching.py --details             # also print every TEST row

Method (same for every matcher, so the comparison is fair):
  1. The "uncertain" threshold is chosen on the TUNE split only.
  2. Accuracy is reported on the TEST split, which is never used to choose anything.

A prediction is correct when:
  - the label has an Agribalyse code and the matcher returns that code (not uncertain), or
  - the label is "NO MATCH" and the matcher says "uncertain".
"""
import argparse

import numpy as np
import pandas as pd

from matching import DATA_DIR, RapidFuzzMatcher

LABELS_FILE = DATA_DIR / "ingredient_labels.csv"


def load_labels() -> pd.DataFrame:
    return pd.read_csv(LABELS_FILE, dtype={"agribalyse_code": str})


def predict(matcher, labels: pd.DataFrame) -> pd.DataFrame:
    """Raw predictions (best match + score) without any threshold."""
    texts = labels["ingredient_text"].tolist()
    preds = matcher.match_many(texts) if hasattr(matcher, "match_many") else [matcher.match(t) for t in texts]
    out = labels[["label_id", "ingredient_text", "language", "split", "agribalyse_code", "agribalyse_name"]].copy()
    out["pred_code"] = [str(p["agribalyse_code"]) for p in preds]
    out["pred_name"] = [p["agribalyse_name"] for p in preds]
    out["score"] = [p["score"] for p in preds]
    return out


def apply_threshold(pred: pd.DataFrame, threshold: float) -> pd.DataFrame:
    out = pred.copy()
    out["uncertain"] = out["score"] < threshold
    no_match = out["agribalyse_code"].isna() | (out["agribalyse_code"].astype(str).str.strip() == "")
    same = out["pred_code"] == out["agribalyse_code"].astype(str).str.strip()
    out["correct"] = np.where(no_match, out["uncertain"], (~out["uncertain"]) & same)
    return out


def choose_threshold(pred_tune: pd.DataFrame, grid) -> tuple[float, float]:
    best_t, best_acc = None, -1.0
    for t in grid:
        acc = apply_threshold(pred_tune, t)["correct"].mean()
        if acc > best_acc:
            best_t, best_acc = float(t), float(acc)
    return best_t, best_acc


def evaluate(matcher, grid, labels: pd.DataFrame | None = None) -> dict:
    labels = load_labels() if labels is None else labels
    pred = predict(matcher, labels)
    t, tune_acc = choose_threshold(pred[pred.split == "tune"], grid)
    test = apply_threshold(pred[pred.split == "test"], t)
    return {"threshold": t, "tune_acc": tune_acc, "test": test,
            "test_correct": int(test.correct.sum()), "test_n": len(test)}


def build_matcher(name: str, model: str | None = None):
    if name == "rapidfuzz":
        return RapidFuzzMatcher(threshold=0), np.arange(0, 101, 5)
    if name == "ai":
        from ai_matching import DEFAULT_MODEL, EmbeddingMatcher
        return EmbeddingMatcher(model_name=model or DEFAULT_MODEL, threshold=0.0), np.round(np.arange(0, 1.0001, 0.05), 2)
    raise ValueError(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matcher", default="rapidfuzz", choices=["rapidfuzz", "ai"])
    ap.add_argument("--model", default=None, help="sentence-transformers model name (AI matcher only)")
    ap.add_argument("--details", action="store_true")
    args = ap.parse_args()

    matcher, grid = build_matcher(args.matcher, args.model)
    r = evaluate(matcher, grid)
    label = args.matcher if args.matcher == "rapidfuzz" else f"ai ({matcher.model_name})"
    print(f"Matcher: {label}")
    print(f"Threshold chosen on TUNE: {r['threshold']}  (tune accuracy {r['tune_acc']:.0%})")
    print(f"\nTEST: {r['test_correct']}/{r['test_n']} correct ({r['test_correct'] / r['test_n']:.0%})")
    print(r["test"].groupby("language")["correct"].agg(["sum", "count"]).rename(columns={"sum": "correct", "count": "n"}))

    if args.details:
        pd.set_option("display.width", 200, "display.max_colwidth", 45)
        print(r["test"][["ingredient_text", "agribalyse_name", "pred_name", "score", "uncertain", "correct"]].to_string(index=False))

    out_file = DATA_DIR / f"results_{args.matcher}_test.csv"
    r["test"].to_csv(out_file, index=False)
    print(f"\nSaved row-by-row results to data/{out_file.name}")


if __name__ == "__main__":
    main()
