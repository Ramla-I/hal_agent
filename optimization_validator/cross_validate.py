"""Validator cross-validation harness (paper section "Benchmarking the Validator as
a Noisy Labeler").

Protocol:
  1. Build a corrupted, (Peripheral, Register)-folded benchmark from a verified
     datasheet (kfold.make_benchmark_with_folds): 30% of invariants are replaced by
     realistic corruptions; folds group whole registers.
  2. Run the Validator ONCE over every invariant in the benchmark (per-register
     batched inference, reusing the project's prompt builders + semantic retrieval).
     Each invariant is evaluated exactly once — as a member of its held-out fold.
  3. k-fold: for each fold i, tune the decision threshold on the *training* partition
     (all rows not in fold i, whose judgments we already have) to maximise F1, then
     evaluate fold i at that threshold to get a per-fold confusion matrix.
  4. Aggregate per-fold confusion matrices into the final Validator confusion matrix
     and report F1 (primary metric) plus sensitivity alpha and specificity beta.
  5. Calibrate downstream measurements: pi (Rogan-Gladen) and validated-set precision
     P(C=1|V=1) (calibration.calibrate).

The Validator emits a binary `is_true` plus a `confidence_score`. We turn that into a
single tunable score, score = confidence if is_true else (1 - confidence) — a
pseudo-probability that the invariant is correct — and threshold it. threshold = 0.5
reproduces the raw is_true judgment (when confidence > 0.5).

"Run across models" is the `MODELS` list in __main__. Per-fold prompt-wording and
in-context-example tuning is human-driven and scaffolded via the FP/FN error-analysis
CSV this harness writes; the automated per-fold tuning here is over the decision
threshold (see Divergence log in docs/validator_paper_plan.md).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Optional

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import client_groq, client_openai  # noqa: E402
from context_retrieval.search import search_context  # noqa: E402
from defs import ContextRetrievalParameters, ContextRetrievalMethod  # noqa: E402
from prompts.validator import (  # noqa: E402
    create_batched_validator_system_prompt,
    create_batched_validator_file_search_query,
    create_batched_validator_user_prompt,
)
from utils.parse_output import get_json_block_from_response  # noqa: E402
from utils.utils import get_model_string  # noqa: E402

from optimization_validator.calibration import ConfusionMatrix, calibrate  # noqa: E402
from optimization_validator.kfold import make_benchmark_with_folds  # noqa: E402

# Models routed to Groq; everything else goes to the OpenAI client.
_GROQ_MODELS = {"gpt-oss-120b", "gpt-oss-20b"}


def pick_client(model_name: str):
    return client_groq if model_name in _GROQ_MODELS else client_openai


def _create_response(client, model_name: str, input_list: list, reasoning_effort: Optional[str]):
    kwargs = dict(model=get_model_string(model_name), input=input_list)
    if reasoning_effort is not None:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return client.responses.create(**kwargs)


def pseudo_score(is_true: bool, confidence: float) -> float:
    """Pseudo-probability that the invariant is correct (C=1).

    confidence is the model's confidence *in its own judgment*, so we map a confident
    "true" near 1 and a confident "false" near 0.
    """
    c = max(0.0, min(1.0, float(confidence)))
    return c if is_true else (1.0 - c)


# --------------------------------------------------------------------------- #
# Inference
# --------------------------------------------------------------------------- #

@dataclass
class Judgment:
    row_id: int
    is_true: bool
    confidence: float
    reasoning: str
    error: str = ""


# Max invariants validated in a single LLM call. Large registers (e.g. exti.emr has
# 57 invariants) otherwise produce JSON arrays that overflow the model's output-token
# limit and truncate — `json.loads` then fails and the WHOLE register defaulted to
# reject. We chunk to this size and split-and-retry on any failure (see _judge_register).
DEFAULT_MAX_PER_CALL = 12


def _judge_chunk(client, model_name, system_text, peripheral, register, chunk,
                 file_search, reasoning_effort) -> tuple[dict, bool]:
    """One LLM call for `chunk` rows of a register. Returns ({row_id: Judgment}, ok).

    ok is False if the call errored, the JSON didn't parse, or it didn't return every
    invariant's index — the caller then splits and retries.
    """
    try:
        invariants = [{
            "field_name": r["field_name"], "key": r["key"], "value": r["correct_value"],
            "peripheral": r["peripheral"], "register": r["register"],
        } for r in chunk]
        user_prompt = create_batched_validator_user_prompt(
            [(peripheral, register)], invariants, file_search)
        input_list = [
            {"role": "developer", "content": [{"type": "input_text", "text": system_text}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ]
        response = _create_response(client, model_name, input_list, reasoning_effort)
        text = response.output_text or ""
        block = get_json_block_from_response(text)
        results = json.loads(block) if block else None
        if isinstance(results, list):
            by_index = {int(r.get("invariant_index", -1)): r for r in results}
            if all(j in by_index for j in range(len(chunk))):
                res = {}
                for j, r in enumerate(chunk):
                    o = by_index[j]
                    res[r["row_id"]] = Judgment(
                        r["row_id"], bool(o.get("is_true", False)),
                        float(o.get("confidence_score", 0.0)), text)
                return res, True
        return {}, False  # parsed but incomplete / wrong shape
    except Exception as exc:
        return {"__error__": str(exc)}, False


def _judge_register(client, model_name, system_text, peripheral, register, rows,
                    file_search, reasoning_effort, max_per_call) -> dict:
    """Judge all invariants of one register, chunked to <=max_per_call per call.

    On any call/parse/incompleteness failure, split the chunk in half and retry, down
    to a single invariant. A size-1 chunk that still fails is marked parse_error
    (a genuine failure, not a batch-truncation artifact).
    """
    judgments: dict = {}

    def _recurse(chunk):
        res, ok = _judge_chunk(client, model_name, system_text, peripheral, register,
                               chunk, file_search, reasoning_effort)
        if ok:
            judgments.update(res)
            return
        if len(chunk) > 1:
            mid = len(chunk) // 2
            _recurse(chunk[:mid])
            _recurse(chunk[mid:])
            return
        err = res.get("__error__", "parse_failed_single")
        r = chunk[0]
        judgments[r["row_id"]] = Judgment(r["row_id"], False, 0.0, "", f"error: {err}")

    for i in range(0, len(rows), max_per_call):
        _recurse(rows[i:i + max_per_call])
    return judgments


def evaluate_rows(
    rows_df: pd.DataFrame,
    model_name: str,
    retrieve_fn,
    reasoning_effort: Optional[str] = None,
    extra_system_text: str = "",
    progress: bool = True,
    progress_label: str = "",
    max_per_call: int = DEFAULT_MAX_PER_CALL,
    access_legend: str = "",
) -> pd.DataFrame:
    """Run the Validator over the given rows (batched per register).

    `retrieve_fn(peripheral, register) -> (text, embedding_ids)` is the retrieval
    backend (OpenEvolve / OpenAI file search / local DB) — see make_retriever().
    `rows_df` must carry a stable `row_id` column (set by the caller). Returns a copy
    with added columns: is_true, confidence_score, score, reasoning, parse_error,
    file_search_chars, reg_in_context (retrieval-coverage instrumentation). Rows the
    model failed to judge get is_true=False, confidence=0.0 and a parse_error note.

    `extra_system_text` is appended to the system prompt — used to inject the per-fold
    mined in-context examples without mutating the shared prompt module.
    """
    client = pick_client(model_name)
    df = rows_df.copy()
    system_text = create_batched_validator_system_prompt(access_legend)
    if extra_system_text:
        system_text = system_text + "\n\n" + extra_system_text

    judgments: dict[int, Judgment] = {}
    coverage: dict[int, tuple] = {}  # row_id -> (file_search_chars, reg_in_context)
    groups = list(df.groupby(["peripheral", "register"]))
    for gi, ((peripheral, register), group) in enumerate(groups):
        if progress:
            print(f"  [{model_name}{progress_label}] register {gi + 1}/{len(groups)}: "
                  f"{peripheral}.{register} ({len(group)} invariants)")
        rows = group.to_dict("records")
        try:
            file_search, _ = retrieve_fn(peripheral, register)
        except Exception as exc:  # retrieval failure -> can't judge this register
            file_search = ""
            for r in rows:
                judgments[r["row_id"]] = Judgment(r["row_id"], False, 0.0, "", f"retrieval_error: {exc}")
                coverage[r["row_id"]] = (0, False)
            continue

        file_search = file_search or ""
        # Coverage signal: does the retrieved text even mention this register?
        reg_in_context = register.lower() in file_search.lower()
        cov = (len(file_search), reg_in_context)
        for r in rows:
            coverage[r["row_id"]] = cov

        # Chunk + split-and-retry so a large register can't fail as one giant batch.
        judgments.update(_judge_register(
            client, model_name, system_text, peripheral, register, rows,
            file_search, reasoning_effort, max_per_call))

    df["is_true"] = df["row_id"].map(lambda i: judgments[i].is_true)
    df["confidence_score"] = df["row_id"].map(lambda i: judgments[i].confidence)
    df["parse_error"] = df["row_id"].map(lambda i: judgments[i].error)
    df["reasoning"] = df["row_id"].map(lambda i: judgments[i].reasoning)
    df["file_search_chars"] = df["row_id"].map(lambda i: coverage.get(i, (0, False))[0])
    df["reg_in_context"] = df["row_id"].map(lambda i: coverage.get(i, (0, False))[1])
    df["score"] = df.apply(lambda r: pseudo_score(r["is_true"], r["confidence_score"]), axis=1)
    return df


def evaluate_benchmark(
    benchmark: pd.DataFrame,
    model_name: str,
    retrieve_fn,
    reasoning_effort: Optional[str] = None,
    progress: bool = True,
    max_per_call: int = DEFAULT_MAX_PER_CALL,
    access_legend: str = "",
) -> pd.DataFrame:
    """Baseline pass: run the Validator over every benchmark row with the base prompt."""
    df = benchmark.reset_index(drop=True).copy()
    df["row_id"] = df.index
    return evaluate_rows(df, model_name, retrieve_fn, reasoning_effort,
                         progress=progress, max_per_call=max_per_call,
                         access_legend=access_legend)


# --------------------------------------------------------------------------- #
# In-context example mining (per-fold tuning)
# --------------------------------------------------------------------------- #

def mine_examples(train_judged: pd.DataFrame, max_per_class: int = 6, seed: int = 0) -> str:
    """Build a few-shot example block from the Validator's mistakes on TRAINING rows.

    Mistakes (at the raw is_true judgment) are the corner cases the spec says to target:
      * false positive  — judged true (accept) but actually corrupted  -> teach: reject
      * false negative  — judged false (reject) but actually correct    -> teach: accept
    We sample up to `max_per_class` of each, balanced, and render them with their
    verified labels. Examples come only from the training partition (folds != held-out),
    so the held-out fold is never used to tune itself.

    Returns "" when there are no usable mistakes (the prompt is left unchanged).
    """
    import random as _random
    rng = _random.Random(seed)

    pred_accept = train_judged["is_true"].astype(bool)
    gold = train_judged["is_correct"].astype(bool)
    fps = train_judged[pred_accept & (~gold)]
    fns = train_judged[(~pred_accept) & gold]

    def _sample(frame):
        recs = frame.to_dict("records")
        rng.shuffle(recs)
        return recs[:max_per_class]

    chosen = [(r, False) for r in _sample(fps)] + [(r, True) for r in _sample(fns)]
    if not chosen:
        return ""
    rng.shuffle(chosen)

    lines = [
        "# ADDITIONAL CALIBRATION EXAMPLES",
        "These are real invariants from OTHER registers in this datasheet, each with its",
        "human-verified correct label. They were chosen because they are corner cases the",
        "Validator has gotten wrong. Use them to calibrate your judgments.",
        "",
    ]
    for i, (r, correct_is_true) in enumerate(chosen, 1):
        field = r.get("field_name") or ""
        verdict = "TRUE (the value matches the datasheet — accept)" if correct_is_true \
            else "FALSE (the value does NOT match the datasheet — reject)"
        lines.append(
            f'Example {i}: peripheral="{r["peripheral"]}", register="{r["register"]}", '
            f'field_name="{field}", key="{r["key"]}", value="{r["correct_value"]}"'
        )
        lines.append(f"  Correct label: {verdict}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Thresholding + folds
# --------------------------------------------------------------------------- #

def confusion_at(scores, golds, tau: float) -> ConfusionMatrix:
    """Confusion matrix when predicting V=1 iff score >= tau. gold True => C=1."""
    tp = fp = tn = fn = 0
    for s, g in zip(scores, golds):
        v1 = s >= tau
        if g and v1:
            tp += 1
        elif (not g) and v1:
            fp += 1
        elif (not g) and (not v1):
            tn += 1
        else:
            fn += 1
    return ConfusionMatrix(tp=tp, fp=fp, tn=tn, fn=fn)


def tune_threshold(scores, golds, grid=None) -> float:
    """Pick the threshold maximising F1 on (scores, golds). Ties -> lower threshold."""
    if grid is None:
        uniq = sorted(set(scores))
        # Candidate cut points: just below each observed score, plus the extremes.
        grid = [0.0] + [u for u in uniq] + [1.0001]
    best_tau, best_f1 = 0.5, -1.0
    for tau in grid:
        f1 = confusion_at(scores, golds, tau).f1
        if f1 > best_f1:
            best_f1, best_tau = f1, tau
    return best_tau


@dataclass
class FoldResult:
    fold: int
    tau: float
    cm: ConfusionMatrix


def cross_validate(evaluated: pd.DataFrame, k: int) -> dict:
    """k-fold: tune threshold on training rows, evaluate on held-out fold.

    `evaluated` must have columns: fold, is_correct, score. Returns a dict with
    per-fold results, the aggregated tuned confusion matrix, the untuned (tau=0.5)
    confusion matrix, and the calibration result.
    """
    fold_results: list[FoldResult] = []
    agg = ConfusionMatrix(0, 0, 0, 0)
    for f in range(k):
        train = evaluated[evaluated["fold"] != f]
        test = evaluated[evaluated["fold"] == f]
        if len(test) == 0:
            continue
        tau = tune_threshold(list(train["score"]), list(train["is_correct"]))
        cm = confusion_at(list(test["score"]), list(test["is_correct"]), tau)
        fold_results.append(FoldResult(fold=f, tau=tau, cm=cm))
        agg = agg + cm

    untuned = confusion_at(list(evaluated["score"]), list(evaluated["is_correct"]), 0.5)
    calib = calibrate(agg)
    return {
        "fold_results": fold_results,
        "aggregated": agg,
        "untuned_tau0.5": untuned,
        "calibration": calib,
    }


def cross_validate_mined(
    baseline: pd.DataFrame,
    model_name: str,
    retrieve_fn,
    k: int,
    reasoning_effort: Optional[str],
    max_per_class: int = 6,
    seed: int = 0,
    max_per_call: int = DEFAULT_MAX_PER_CALL,
    access_legend: str = "",
) -> dict:
    """Per-fold tuning with mined in-context examples + decision threshold.

    For each fold f: mine the Validator's mistakes on the TRAINING partition
    (folds != f) from `baseline`, inject them as few-shot examples, RE-EVALUATE the
    held-out fold f with the augmented prompt, and score it at a threshold tuned on the
    baseline training scores. Both knobs (examples, threshold) are fit on training only.

    Returns a dict with per-fold results, the aggregated tuned confusion matrix, the
    concatenated per-fold tuned judgments, and the calibration result.
    """
    fold_results: list[FoldResult] = []
    agg = ConfusionMatrix(0, 0, 0, 0)
    tuned_parts = []
    fold_prompts = []  # the actual prompt version used for each held-out fold
    base_system = create_batched_validator_system_prompt(access_legend)
    for f in range(k):
        train = baseline[baseline["fold"] != f]
        test = baseline[baseline["fold"] == f]
        if len(test) == 0:
            continue
        examples = mine_examples(train, max_per_class=max_per_class, seed=seed + f)
        full_system = base_system + ("\n\n" + examples if examples else "")
        n_ex = examples.count("Example ") if examples else 0
        fold_prompts.append({
            "fold": f, "n_mined_examples": n_ex,
            "examples_block": examples, "full_system_prompt": full_system,
        })
        test2 = evaluate_rows(
            test, model_name, retrieve_fn, reasoning_effort,
            extra_system_text=examples, progress_label=f" fold{f}/tuned",
            max_per_call=max_per_call, access_legend=access_legend)
        tau = tune_threshold(list(train["score"]), list(train["is_correct"]))
        cm = confusion_at(list(test2["score"]), list(test2["is_correct"]), tau)
        fold_results.append(FoldResult(fold=f, tau=tau, cm=cm))
        agg = agg + cm
        part = test2.copy()
        part["fold"] = f
        part["tau"] = tau
        part["n_mined_examples"] = n_ex
        tuned_parts.append(part)

    tuned_eval = pd.concat(tuned_parts, ignore_index=True) if tuned_parts else baseline.iloc[0:0].copy()
    return {
        "fold_results": fold_results,
        "aggregated": agg,
        "tuned_eval": tuned_eval,
        "calibration": calibrate(agg),
        "base_system_prompt": base_system,
        "fold_prompts": fold_prompts,
    }


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def _write_prompt_versions(out_dir: str, model_name: str, tuned_cv: dict) -> None:
    """Save the base prompt and each fold's mined-example-augmented system prompt.

    Layout under <out_dir>/prompts/:
      baseline_system_prompt.txt        — the unmodified base prompt (all baseline calls)
      fold{f}_system_prompt.txt         — full system prompt used for held-out fold f
      fold{f}_examples.txt              — just the mined in-context examples block
      prompt_versions_{model}.md        — index: per fold, # examples + the block inline
    """
    pdir = os.path.join(out_dir, "prompts")
    os.makedirs(pdir, exist_ok=True)

    base = tuned_cv.get("base_system_prompt", "")
    with open(os.path.join(pdir, "baseline_system_prompt.txt"), "w") as fh:
        fh.write(base)

    md = [f"# Validator prompt versions — {model_name}", "",
          "`baseline` uses the base system prompt below for every call. Each fold's",
          "tuned pass appends in-context examples mined from that fold's TRAINING",
          "partition (folds != held-out), so the held-out fold never tunes itself.", ""]
    for fp in tuned_cv.get("fold_prompts", []):
        f = fp["fold"]
        with open(os.path.join(pdir, f"fold{f}_system_prompt.txt"), "w") as fh:
            fh.write(fp["full_system_prompt"])
        with open(os.path.join(pdir, f"fold{f}_examples.txt"), "w") as fh:
            fh.write(fp["examples_block"] or "(no mistakes mined on training folds; base prompt used)")
        md.append(f"## Fold {f} — {fp['n_mined_examples']} mined example(s)")
        md.append("")
        md.append("```")
        md.append(fp["examples_block"] or "(no examples added; base prompt used)")
        md.append("```")
        md.append("")
    md.append("## Base system prompt")
    md.append("")
    md.append("```")
    md.append(base)
    md.append("```")
    with open(os.path.join(pdir, f"prompt_versions_{model_name}.md"), "w") as fh:
        fh.write("\n".join(md))


def _agg_summary_row(model_name: str, variant: str, cv: dict) -> dict:
    agg = cv["aggregated"]
    calib = cv["calibration"]
    return {
        "model": model_name, "variant": variant, "n": agg.total,
        "tp": agg.tp, "fp": agg.fp, "tn": agg.tn, "fn": agg.fn,
        "f1": agg.f1, "precision": agg.precision, "recall": agg.recall, "accuracy": agg.accuracy,
        "alpha": agg.alpha, "beta": agg.beta,
        "r_hat": calib.r_hat, "pi": calib.pi, "pi_raw": calib.pi_raw,
        "validated_precision": calib.validated_precision,
        "identifiable": calib.identifiable, "note": calib.note,
    }


def write_outputs(out_dir: str, model_name: str, baseline_eval: pd.DataFrame,
                  baseline_cv: dict, tuned_cv: dict) -> None:
    """Write baseline (threshold-only) and tuned (mined examples + threshold) results.

    `tuned_cv` is the headline; `baseline_cv` is reported alongside to show the lift
    from per-fold in-context example tuning.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Per-row judgments (auditable; includes reasoning). Baseline = pass 1 over all
    # rows; tuned = per-fold pass 2 on the held-out folds with mined examples.
    baseline_eval.to_csv(os.path.join(out_dir, f"judgments_{model_name}.csv"), index=False)
    tuned_cv["tuned_eval"].to_csv(os.path.join(out_dir, f"judgments_tuned_{model_name}.csv"), index=False)

    # FP/FN error-analysis at tau=0.5 on the baseline — exactly the rows mining learns from.
    ev = baseline_eval.copy()
    ev["pred_v1"] = ev["score"] >= 0.5
    fp_fn = ev[((ev["pred_v1"]) & (~ev["is_correct"])) | ((~ev["pred_v1"]) & (ev["is_correct"]))]
    cols = ["peripheral", "register", "field_name", "key", "correct_value", "is_correct",
            "corruption_type", "is_true", "confidence_score", "score", "reasoning"]
    fp_fn[[c for c in cols if c in fp_fn.columns]].to_csv(
        os.path.join(out_dir, f"error_analysis_{model_name}.csv"), index=False)

    # Per-fold confusion + thresholds, baseline vs tuned side by side.
    per_fold_rows = []
    base_by_fold = {fr.fold: fr for fr in baseline_cv["fold_results"]}
    for fr in tuned_cv["fold_results"]:
        b = base_by_fold.get(fr.fold)
        per_fold_rows.append({
            "fold": fr.fold, "tau": fr.tau,
            "tuned_tp": fr.cm.tp, "tuned_fp": fr.cm.fp, "tuned_tn": fr.cm.tn, "tuned_fn": fr.cm.fn,
            "tuned_f1": fr.cm.f1,
            "baseline_f1": b.cm.f1 if b else None,
        })
    pd.DataFrame(per_fold_rows).to_csv(os.path.join(out_dir, f"per_fold_{model_name}.csv"), index=False)

    # Aggregated confusion + calibration -> JSON + a 2-row summary CSV (baseline, tuned).
    summary = {
        "model": model_name,
        "baseline_threshold_only": {
            "aggregated_confusion": baseline_cv["aggregated"].to_dict(),
            "calibration": baseline_cv["calibration"].to_dict(),
        },
        "tuned_mined_examples": {
            "aggregated_confusion": tuned_cv["aggregated"].to_dict(),
            "calibration": tuned_cv["calibration"].to_dict(),
        },
    }
    with open(os.path.join(out_dir, f"summary_{model_name}.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    pd.DataFrame([
        _agg_summary_row(model_name, "baseline_threshold_only", baseline_cv),
        _agg_summary_row(model_name, "tuned_mined_examples", tuned_cv),
    ]).to_csv(os.path.join(out_dir, f"summary_{model_name}.csv"), index=False)

    # Prompt versions: persist the exact system prompt used for each held-out fold so
    # the in-context examples added by mining are fully auditable.
    _write_prompt_versions(out_dir, model_name, tuned_cv)

    b_agg, t_agg = baseline_cv["aggregated"], tuned_cv["aggregated"]
    t_calib = tuned_cv["calibration"]
    print(f"  wrote outputs to {out_dir}")
    print(f"  baseline F1={b_agg.f1:.3f}  ->  tuned F1={t_agg.f1:.3f}  (lift {t_agg.f1 - b_agg.f1:+.3f})")
    print(f"  tuned: alpha={t_agg.alpha}  beta={t_agg.beta}  "
          f"pi={t_calib.pi}  validated_precision={t_calib.validated_precision}")


def run_model(
    verified_csv: str,
    model_name: str,
    out_dir: str,
    retrieve_fn,
    k: int = 5,
    corruption_fraction: float = 0.30,
    seed: int = 0,
    reasoning_effort: Optional[str] = None,
    limit_registers: Optional[int] = None,
    max_per_class: int = 6,
    max_per_call: int = DEFAULT_MAX_PER_CALL,
    access_legend: str = "",
) -> dict:
    """End-to-end for one model.

    Pass 1: evaluate every invariant with the base prompt (baseline).
    Pass 2: per fold, mine training-fold mistakes -> few-shot examples -> re-evaluate
    the held-out fold (tuned). Both passes are cross-validated (threshold tuned on
    training); the tuned aggregate is the headline, baseline is reported for the lift.

    `retrieve_fn(peripheral, register) -> (text, ids)` is the retrieval backend.
    """
    benchmark = make_benchmark_with_folds(
        verified_csv, k=k, corruption_fraction=corruption_fraction, seed=seed)
    if limit_registers is not None:
        # Smoke mode: keep only the first N (peripheral, register) groups.
        keep = (benchmark[["peripheral", "register"]].drop_duplicates().head(limit_registers))
        benchmark = benchmark.merge(keep, on=["peripheral", "register"], how="inner").reset_index(drop=True)
        # Re-fold the smaller slice so k folds remain populated.
        from optimization_validator.kfold import assign_folds
        benchmark = assign_folds(benchmark.drop(columns=["fold"]), k=k, seed=seed)

    print(f"[{model_name}] benchmark: {len(benchmark)} invariants, "
          f"{benchmark[['peripheral','register']].drop_duplicates().shape[0]} registers, "
          f"{int(benchmark['is_correct'].sum())} correct / {int((~benchmark['is_correct']).sum())} corrupted")

    print(f"[{model_name}] pass 1/2: baseline evaluation (base prompt)")
    baseline_eval = evaluate_benchmark(
        benchmark, model_name, retrieve_fn, reasoning_effort=reasoning_effort,
        max_per_call=max_per_call, access_legend=access_legend)
    baseline_cv = cross_validate(baseline_eval, k=k)
    cov = baseline_eval["reg_in_context"].mean() if "reg_in_context" in baseline_eval else float("nan")
    n_parse_err = (baseline_eval["parse_error"].fillna("") != "").sum()
    print(f"[{model_name}] retrieval coverage: register name present for {cov:.0%} of invariants; "
          f"{n_parse_err} rows with parse/retrieval errors")

    print(f"[{model_name}] pass 2/2: per-fold tuning with mined in-context examples")
    tuned_cv = cross_validate_mined(
        baseline_eval, model_name, retrieve_fn, k=k, reasoning_effort=reasoning_effort,
        max_per_class=max_per_class, seed=seed, max_per_call=max_per_call,
        access_legend=access_legend)

    write_outputs(out_dir, model_name, baseline_eval, baseline_cv, tuned_cv)
    return {"baseline": baseline_cv, "tuned": tuned_cv}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

# vs_id for rm0041 (config.user_contexts) — OpenAI file-search vector store.
RM0041_VS_ID = "vs_6892501067b08191ac63cc6de06ee629"
# Default evolved retrieval program for rm0041.
RM0041_OE_PROGRAM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "openevolve_retrieval", "output_rm0041", "best", "best_program.py")


def _openai_file_search_params(vs_id: str, num_embeddings: int = 4) -> ContextRetrievalParameters:
    return ContextRetrievalParameters(
        context_retrieval_method=ContextRetrievalMethod.OPENAI_FILE_SEARCH,
        pages_after_keyword=0, remove_tables=False, number_embeddings=num_embeddings,
        re_ranking=True, score_threshold=0.25, vs_id=vs_id, regex="",
    )


def _openevolve_params(oe_program_path: str) -> ContextRetrievalParameters:
    # The OPENEVOLVE path in retrieve_context() calls search_openevolve() directly;
    # most fields below are unused by it but required by the pydantic model.
    return ContextRetrievalParameters(
        context_retrieval_method=ContextRetrievalMethod.OPENEVOLVE,
        pages_after_keyword=0, remove_tables=False, number_embeddings=6,
        re_ranking=False, score_threshold=0.0, vs_id="", regex="",
        oe_program_path=oe_program_path,
    )


def make_retriever(params: ContextRetrievalParameters, device_name: str,
                   device_dir: str, manufacturer):
    """Build a `retrieve(peripheral, register) -> (text, embedding_ids)` closure.

    OpenEvolve needs per-register dispatch via retrieve_context() (which builds the
    register query + resolves the chunk index); OpenAI/local file search use a batched
    validator query via search_context().
    """
    from defs import ContextRetrievalMethod as _M
    if params.context_retrieval_method == _M.OPENEVOLVE:
        from context_retrieval.retrieve_context import retrieve_context

        def _retrieve(peripheral, register):
            return retrieve_context(
                params, device_name, device_dir, peripheral, register, manufacturer, output_dir="")
        return _retrieve

    def _retrieve(peripheral, register):
        return search_context(
            create_batched_validator_file_search_query(peripheral, register), params)
    return _retrieve


# Edit this list to run cross-validation across different models.
MODELS = [
    {"model_name": "gpt-oss-120b", "reasoning_effort": None},
    {"model_name": "gpt-4.1-nano", "reasoning_effort": None},
]


def main():
    ap = argparse.ArgumentParser(description="Validator cross-validation harness")
    ap.add_argument("--verified-csv", default="verified_datasheet/stm/rm0041_stm32f100.csv")
    ap.add_argument("--device", default="stm-rm0041")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--corruption-fraction", type=float, default=0.30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--num-embeddings", type=int, default=4)
    ap.add_argument("--vs-id", default=RM0041_VS_ID)
    ap.add_argument("--smoke", action="store_true",
                    help="tiny end-to-end run: 1 model, few registers (proves the harness)")
    ap.add_argument("--smoke-registers", type=int, default=6)
    ap.add_argument("--model", default=None,
                    help="run only this model (overrides the MODELS list); e.g. gpt-oss-120b")
    ap.add_argument("--reasoning-effort", default=None,
                    help="reasoning effort for --model (e.g. low/medium/high); default none")
    ap.add_argument("--retrieval", choices=["openevolve", "openai"], default="openevolve",
                    help="retrieval backend (default: openevolve — the evolved program)")
    ap.add_argument("--oe-program", default=RM0041_OE_PROGRAM,
                    help="path to the OpenEvolve best_program.py (for --retrieval openevolve)")
    ap.add_argument("--device-dir", default="devices/stm/rm0041",
                    help="device asset dir (used by OpenEvolve to locate chunked_datasheets)")
    ap.add_argument("--device-name", default="rm0041")
    ap.add_argument("--vendor", default="stm",
                    help="vendor key for the access-notation legend (see "
                         "optimization_validator/access_notations.json); '' or 'none' to disable")
    ap.add_argument("--max-per-call", type=int, default=DEFAULT_MAX_PER_CALL,
                    help="max invariants per LLM call; large registers are chunked + "
                         "split-retried on parse failure (default 12)")
    ap.add_argument("--out-root", default=None,
                    help="output root (default optimization_validator/<device>/cross_validation)")
    args = ap.parse_args()

    out_root = args.out_root or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.device, "cross_validation")

    if args.retrieval == "openevolve":
        params = _openevolve_params(args.oe_program)
        print(f"Retrieval: OpenEvolve best program ({args.oe_program})")
    else:
        params = _openai_file_search_params(args.vs_id, args.num_embeddings)
        print(f"Retrieval: OpenAI file_search (vs={args.vs_id}, {args.num_embeddings} chunks)")

    from defs import Manufacturer
    retrieve_fn = make_retriever(params, args.device_name, args.device_dir, Manufacturer.STM)

    # Vendor access-notation legend (maps datasheet codes like rc_w0 -> read-write).
    from optimization_validator.access_notation import access_legend as _access_legend
    vendor = "" if args.vendor.lower() in ("", "none") else args.vendor
    legend = _access_legend(vendor) if vendor else ""
    if legend:
        print(f"Access-notation legend: enabled (vendor={vendor})")

    # Restrict to a single model when --model is given, else use the MODELS list.
    models = ([{"model_name": args.model, "reasoning_effort": args.reasoning_effort}]
              if args.model else MODELS)

    if args.smoke:
        k = min(args.k, 3)
        out_dir = os.path.join(out_root, "smoke")
        run_model(
            args.verified_csv, models[0]["model_name"], out_dir, retrieve_fn,
            k=k, corruption_fraction=args.corruption_fraction, seed=args.seed,
            reasoning_effort=models[0].get("reasoning_effort"),
            limit_registers=args.smoke_registers, max_per_call=args.max_per_call,
            access_legend=legend)
        return

    print(f"Running cross-validation for {len(models)} model(s): "
          f"{', '.join(m['model_name'] for m in models)}")
    for cfg in models:
        out_dir = os.path.join(out_root, cfg["model_name"])
        run_model(
            args.verified_csv, cfg["model_name"], out_dir, retrieve_fn,
            k=args.k, corruption_fraction=args.corruption_fraction, seed=args.seed,
            reasoning_effort=cfg.get("reasoning_effort"), max_per_call=args.max_per_call,
            access_legend=legend)


if __name__ == "__main__":
    main()
    # The OpenEvolve backend leaves non-daemon ChromaDB/onnxruntime threads alive,
    # which keeps the interpreter from exiting after all work + outputs are done.
    # Force a clean exit so background/timeout-wrapped runs terminate promptly.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
