"""Evaluate an ingredient matcher against the hand-verified labels.

Usage:
    python src/evaluate_matching.py                       # RapidFuzz baseline
    python src/evaluate_matching.py --matcher ai          # AI matcher (default model)
    python src/evaluate_matching.py --matcher ai --model intfloat/multilingual-e5-small
    python src/evaluate_matching.py --details             # also print every TEST row
    python src/evaluate_matching.py --matcher llm                          # open LLM, free (GPU: use Colab, notebook 07)
    python src/evaluate_matching.py --matcher llm --provider anthropic     # Claude API (needs ANTHROPIC_API_KEY)

Method (same for every matcher, so the comparison is fair):
  1. The "uncertain" threshold is chosen on the TUNE split only.
  2. Accuracy is reported on the TEST split, which is never used to choose anything.

Objective used to choose the threshold on TUNE (--objective):
  - "accuracy" (default, the rule used in dev logs 05 and 04): maximise correct answers.
  - "safe": maximise correct answers minus `penalty` x confident errors. A confident error
    (a wrong food WITH a CO2e number) is worse than saying "uncertain" (no number), so this
    objective prefers a higher threshold. Decide the objective BEFORE looking at TEST.

    python src/evaluate_matching.py --matcher ai --candidates strict --objective safe

A prediction is correct when:
  - the label has an Agribalyse code and the matcher returns that code (not uncertain), or
  - the label is "NO MATCH" and the matcher says "uncertain".

Second metric, "CO2e OK" (what matters for the user): correct, OR a different Agribalyse food whose
CO2e per kg is within +-25% of the labelled one (e.g. "Green lentil, cooked" vs "Lentil, cooked").
"""
import argparse

import numpy as np
import pandas as pd

from matching import DATA_DIR, RapidFuzzMatcher, load_agribalyse

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
    # Wrong food AND a CO2e number shown: the dangerous error for the user
    out["confident_error"] = (~out["correct"]) & (~out["uncertain"])
    out["co2e_ok"] = out["correct"] | (~out["uncertain"] & ~no_match & _within(out, 0.25))
    return out


_CO2E: dict = {}


def _within(out: pd.DataFrame, tol: float) -> pd.Series:
    """True when the predicted food's CO2e/kg is within +-tol of the labelled food's."""
    if not _CO2E:
        agb = load_agribalyse()
        _CO2E.update(zip(agb["agribalyse_code"], pd.to_numeric(agb["co2e_per_kg"], errors="coerce")))
    true = out["agribalyse_code"].astype(str).str.strip().map(_CO2E)
    pred = out["pred_code"].map(_CO2E)
    return ((pred - true).abs() / true <= tol).fillna(False)


def objective_value(scored: pd.DataFrame, objective: str = "accuracy", penalty: float = 1.0) -> float:
    if objective == "accuracy":
        return float(scored["correct"].mean())
    if objective == "safe":
        return float(scored["correct"].mean() - penalty * scored["confident_error"].mean())
    raise ValueError(f"Unknown objective: {objective}")


def choose_threshold(pred_tune: pd.DataFrame, grid, objective: str = "accuracy",
                     penalty: float = 1.0) -> tuple[float, float]:
    """Best threshold on TUNE for the objective. Returns (threshold, tune accuracy at that threshold)."""
    best_t, best_val = None, -np.inf
    for t in grid:
        val = objective_value(apply_threshold(pred_tune, t), objective, penalty)
        if val > best_val:
            best_t, best_val = float(t), val
    return best_t, float(apply_threshold(pred_tune, best_t)["correct"].mean())

def evaluate_tune(matcher, grid, labels=None, objective: str = "accuracy", penalty: float = 1.0):
    """Evaluate only on TUNE, without accessing TEST."""
    labels = load_labels() if labels is None else labels
    tune_labels = labels[labels["split"] == "tune"]

    pred_tune = predict(matcher, tune_labels)
    threshold, tune_acc = choose_threshold(pred_tune, grid, objective, penalty)

    return {
        "threshold": threshold,
        "tune_acc": tune_acc
    }

def evaluate(matcher, grid, labels: pd.DataFrame | None = None, objective: str = "accuracy",
             penalty: float = 1.0) -> dict:
    labels = load_labels() if labels is None else labels
    pred = predict(matcher, labels)
    t, tune_acc = choose_threshold(pred[pred.split == "tune"], grid, objective, penalty)
    test = apply_threshold(pred[pred.split == "test"], t)
    return {"threshold": t, "tune_acc": tune_acc, "test": test,
            "test_correct": int(test.correct.sum()), "test_n": len(test),
            "test_uncertain": int(test.uncertain.sum()),
            "test_confident_errors": int(test.confident_error.sum()),
            "test_co2e_ok": int(test.co2e_ok.sum())}


def build_matcher(name: str, model: str | None = None, candidates: str | None = None, passage: str | None = None,
                  provider: str = "hf", verify: bool = False):
    if name == "rapidfuzz":
        return RapidFuzzMatcher(threshold=0), np.arange(0, 101, 5)
    if name == "ai":
        from ai_matching import DEFAULT_CANDIDATES, DEFAULT_MODEL, DEFAULT_PASSAGE, EmbeddingMatcher
        m = EmbeddingMatcher(model_name=model or DEFAULT_MODEL, threshold=0.0,
                             candidates=candidates or DEFAULT_CANDIDATES, passage=passage or DEFAULT_PASSAGE)
        return m, np.round(np.arange(0, 1.0001, 0.05), 2)
    if name == "llm":
        from llm_matching import LLMMatcher
        m = LLMMatcher(model=model, provider=provider, threshold=0.0, verify=verify)
        # scores are confidence levels: low 0.3, medium 0.6, high 1.0. Score 0 (NONE, or rejected by the
        # verify step) must always be "uncertain", so the lowest threshold is 0.3, not 0.
        return m, [0.3, 0.6, 1.0]
    raise ValueError(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matcher", default="rapidfuzz", choices=["rapidfuzz", "ai", "llm"])
    ap.add_argument("--model", default=None, help="sentence-transformers model (ai) or LLM model (llm)")
    ap.add_argument("--candidates", default=None, choices=["all", "light", "strict"])
    ap.add_argument("--passage", default=None, choices=["en", "en_fr"])
    ap.add_argument("--objective", default="accuracy", choices=["accuracy", "safe"])
    ap.add_argument("--penalty", type=float, default=1.0, help="weight of a confident error (objective 'safe')")
    ap.add_argument("--provider", default="hf", choices=["hf", "anthropic"], help="LLM matcher only")
    ap.add_argument("--verify", action="store_true", help="LLM matcher only: extra yes/no check of the chosen food")
    ap.add_argument("--details", action="store_true")
    args = ap.parse_args()

    matcher, grid = build_matcher(args.matcher, args.model, args.candidates, args.passage, args.provider, args.verify)
    r = evaluate(matcher, grid, objective=args.objective, penalty=args.penalty)
    if args.matcher == "rapidfuzz":
        label = "rapidfuzz"
    elif args.matcher == "llm":
        label = f"llm ({matcher.model_name}, retrieve top-{matcher.k} + choose" + (" + verify)" if matcher.verify else ")")
    else:
        label = f"ai ({matcher.model_name}, candidates={matcher.candidates}, passage={matcher.passage})"
    print(f"Matcher: {label}")
    print(f"Objective: {args.objective}" + (f" (penalty {args.penalty})" if args.objective == "safe" else ""))
    print(f"Threshold chosen on TUNE: {r['threshold']}  (tune accuracy {r['tune_acc']:.0%})")
    print(f"\nTEST: {r['test_correct']}/{r['test_n']} correct ({r['test_correct'] / r['test_n']:.0%})")
    print(f"      {r['test_uncertain']} uncertain (no number), "
          f"{r['test_confident_errors']} confident errors (wrong food with a CO2e number)")
    print(f"      CO2e OK (right food, or CO2e within +-25%): {r['test_co2e_ok']}/{r['test_n']}")
    print(r["test"].groupby("language")[["correct", "co2e_ok"]].sum().join(
        r["test"].groupby("language").size().rename("n")))

    if args.details:
        pd.set_option("display.width", 200, "display.max_colwidth", 45)
        print(r["test"][["ingredient_text", "agribalyse_name", "pred_name", "score", "uncertain", "correct"]].to_string(index=False))

    # One file per configuration, so a new run never overwrites an earlier result
    tag = args.matcher
    if args.matcher == "ai":
        tag += f"_{matcher.model_name.split('/')[-1]}_{matcher.candidates}_{matcher.passage}"
    if args.matcher == "llm":
        tag += f"_{matcher.model_name.split('/')[-1]}" + ("_verify" if matcher.verify else "")
    if args.objective != "accuracy":
        tag += f"_{args.objective}"
    out_file = DATA_DIR / f"results_{tag}_test.csv"
    r["test"].to_csv(out_file, index=False)
    print(f"\nSaved row-by-row results to data/{out_file.name}")


if __name__ == "__main__":
    main()
