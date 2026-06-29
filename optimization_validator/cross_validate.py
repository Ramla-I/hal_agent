"""Validator cross-validation harness (paper section "Benchmarking the Validator as
a Noisy Labeler").

Protocol:
  1. Build a corrupted, (Peripheral, Register)-folded benchmark from a verified
     datasheet (kfold.make_benchmark_with_folds): derived peripherals expanded, 30% of
     invariants replaced by realistic corruptions (peripheral-stratified); folds group
     whole registers.
  2. Pass 1 (baseline): run the Validator over every invariant with the base prompt
     (which already carries static, hand-written reasoning examples), per-register
     batched inference + semantic retrieval. Export the Validator's mistakes as CURATION
     CANDIDATES for a human (export_curation_candidates).
  3. Pass 2 (curated, optional): if a per-vendor curated-examples file is given
     (--curated-examples), re-evaluate every invariant with those human-curated,
     datasheet-grounded examples injected, to measure the lift. Curation is done once per
     manufacturer (a human supplies the datasheet excerpt + conclusion for selected
     candidates); there is NO automatic example mining.
  4. k-fold: for each fold i, tune the gate threshold on the *training* partition, then
     score fold i at that threshold. The default objective is OPERATIONAL: the lowest
     threshold whose training precision clears a target (--target-precision, default
     0.95), maximising yield (recall) under it (--objective f1 restores max-F1).
  5. Aggregate per-fold confusion matrices. Headline numbers: the gate's **precision**
     (quality of the reviewed pile) and **yield/recall** (fraction of real bugs kept —
     the rest dropped unseen). Reported baseline vs curated to show the lift.
  6. Calibrate downstream measurements: pi (Rogan-Gladen) and validated-set precision
     P(C=1|V=1) (calibration.calibrate).

Operational model (the system this harness measures): the generator's candidate bugs go
through the Validator; whatever it gates out (V=0) is **never reviewed**, and the
survivors (V=1) are **ranked by confidence** so a human reviews the most-likely-true
first and stops when labour runs out. This harness therefore also emits, from the
held-out judgments, the artifacts that operation needs: a ranked **review queue**, a
**precision@k** table (front-loading quality), and a **calibration/reliability** table
(so the stopping depth is principled). Because the gate hard-drops V=0, a false negative
is a permanently lost bug — hence reporting recall/yield at the chosen precision, not
just precision.

The Validator emits a binary `is_true` plus a `confidence_score`. We turn that into a
single tunable score, score = confidence if is_true else (1 - confidence) — a
pseudo-probability that the invariant is correct — and threshold it for the gate. For a
gated-in (V=1) survivor at any threshold >= 0.5, score == confidence, so ranking the
queue by score is ranking by the model's confidence.

"Run across models" is the `MODELS` list in __main__. In-context examples are
human-curated once per manufacturer (scaffolded by the exported curation candidates +
FP/FN error analysis); the only automated per-fold tuning here is the decision threshold
(see Divergence log in docs/validator_paper_plan.md).
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


def _extract_usage(response) -> dict:
    """Pull token usage off a Responses-API result, tolerant of field-name variants
    (input/output_tokens vs prompt/completion_tokens) and reasoning-token details."""
    u = getattr(response, "usage", None)
    if u is None:
        return {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0}
    inp = getattr(u, "input_tokens", None)
    if inp is None:
        inp = getattr(u, "prompt_tokens", 0) or 0
    out = getattr(u, "output_tokens", None)
    if out is None:
        out = getattr(u, "completion_tokens", 0) or 0
    total = getattr(u, "total_tokens", None)
    if total is None:
        total = (inp or 0) + (out or 0)
    details = getattr(u, "output_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", 0) if details is not None else 0
    return {"input_tokens": int(inp or 0), "output_tokens": int(out or 0),
            "reasoning_tokens": int(reasoning or 0), "total_tokens": int(total or 0)}


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
                 file_search, reasoning_effort, use_alt_name: bool = True,
                 usage_sink: Optional[list] = None, usage_tag: str = "") -> tuple[dict, bool]:
    """One LLM call for `chunk` rows of a register. Returns ({row_id: Judgment}, ok).

    ok is False if the call errored, the JSON didn't parse, or it didn't return every
    invariant's index — the caller then splits and retries. When `use_alt_name` is set we
    pass each row's `alt_name` (datasheet-printed name) so the prompt can surface it as
    `datasheet_name`.
    """
    try:
        invariants = []
        for r in chunk:
            inv = {
                "field_name": r["field_name"], "key": r["key"], "value": r["correct_value"],
                "peripheral": r["peripheral"], "register": r["register"],
            }
            if use_alt_name and str(r.get("alt_name", "") or "").strip():
                inv["alt_name"] = r["alt_name"]
            invariants.append(inv)
        user_prompt = create_batched_validator_user_prompt(
            [(peripheral, register)], invariants, file_search)
        input_list = [
            {"role": "developer", "content": [{"type": "input_text", "text": system_text}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ]
        response = _create_response(client, model_name, input_list, reasoning_effort)
        if usage_sink is not None:
            rec = _extract_usage(response)  # counts every call, including split-retries
            rec.update(model=model_name, tag=usage_tag, peripheral=peripheral,
                       register=register, n_invariants=len(chunk))
            usage_sink.append(rec)
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
                    file_search, reasoning_effort, max_per_call, use_alt_name: bool = True,
                    usage_sink: Optional[list] = None, usage_tag: str = "") -> dict:
    """Judge all invariants of one register, chunked to <=max_per_call per call.

    On any call/parse/incompleteness failure, split the chunk in half and retry, down
    to a single invariant. A size-1 chunk that still fails is marked parse_error
    (a genuine failure, not a batch-truncation artifact).
    """
    judgments: dict = {}

    def _recurse(chunk):
        res, ok = _judge_chunk(client, model_name, system_text, peripheral, register,
                               chunk, file_search, reasoning_effort, use_alt_name=use_alt_name,
                               usage_sink=usage_sink, usage_tag=usage_tag)
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
    use_alt_name: bool = True,
    usage_sink: Optional[list] = None,
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
    system_text = create_batched_validator_system_prompt(access_legend, name_aliasing=use_alt_name)
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
            file_search, reasoning_effort, max_per_call, use_alt_name=use_alt_name,
            usage_sink=usage_sink, usage_tag=(progress_label.strip() or "baseline")))

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
    use_alt_name: bool = True,
    usage_sink: Optional[list] = None,
    extra_system_text: str = "",
    progress_label: str = "",
) -> pd.DataFrame:
    """Run the Validator over every benchmark row. `extra_system_text` (e.g. the curated
    examples block) is appended to the system prompt for all rows."""
    df = benchmark.reset_index(drop=True).copy()
    df["row_id"] = df.index
    return evaluate_rows(df, model_name, retrieve_fn, reasoning_effort,
                         extra_system_text=extra_system_text, progress=progress,
                         progress_label=progress_label, max_per_call=max_per_call,
                         access_legend=access_legend, use_alt_name=use_alt_name,
                         usage_sink=usage_sink)


# --------------------------------------------------------------------------- #
# Curated in-context examples (human-in-the-loop, once per manufacturer)
# --------------------------------------------------------------------------- #
#
# Tuning is NOT automatic example mining. Instead: a first (baseline) pass surfaces the
# Validator's mistakes as CURATION CANDIDATES (export_curation_candidates); a human keeps
# the instructive ones and supplies, for each, the supporting DATASHEET EXCERPT + the
# correct conclusion (stored once per vendor in a JSON file); a second pass re-evaluates
# with those curated examples injected into the prompt (render/load_curated_examples).
# The datasheet excerpt is what teaches grounded reasoning, not just the verdict.


def render_curated_examples(curated: list) -> str:
    """Render human-curated examples (each invariant + datasheet excerpt + reasoning +
    correct label) into a batched-prompt block. Entries missing a datasheet_excerpt are
    skipped (still un-curated). Returns "" if none are usable."""
    usable = [c for c in (curated or []) if isinstance(c, dict)
              and str(c.get("datasheet_excerpt") or "").strip()]
    if not usable:
        return ""
    lines = [
        "# CURATED EXAMPLES (real cases with datasheet evidence)",
        "Each example is a real invariant with the supporting datasheet text and the",
        "human-verified conclusion. Reason the same way over the facts in this request.",
        "",
    ]
    for i, c in enumerate(usable, 1):
        field = str(c.get("field_name") or "")
        verdict = "TRUE — accept" if c.get("is_true") else "FALSE — reject"
        lines.append(
            f'Example {i}: peripheral="{c.get("peripheral", "")}", '
            f'register="{c.get("register", "")}", field_name="{field}", '
            f'key="{c.get("key", "")}", value="{c.get("value", "")}"'
        )
        lines.append(f'  Datasheet: {str(c.get("datasheet_excerpt") or "").strip()}')
        reasoning = str(c.get("reasoning") or "").strip()
        if reasoning:
            lines.append(f"  Reasoning: {reasoning}")
        lines.append(f"  Conclusion: {verdict}")
    return "\n".join(lines)


def load_curated_examples(path: Optional[str]) -> str:
    """Load a per-vendor curated-examples JSON ({"examples": [...]} or a bare list) and
    render it to a prompt block. Returns "" if path is empty/missing/uncurated."""
    if not path or not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    curated = data.get("examples", []) if isinstance(data, dict) else data
    return render_curated_examples(curated)


def export_curation_candidates(eval_df: pd.DataFrame, path: str, max_per_class: int = 40) -> int:
    """Write the Validator's mistakes (FP/FN at the raw is_true judgment) as a curation
    template: each entry carries the invariant, the validator's wrong verdict, and the
    GROUND-TRUTH label/value, with empty `datasheet_excerpt`/`reasoning` for a human to
    fill (once per manufacturer). Returns the number of candidates written."""
    ev = eval_df.copy()
    pred_accept = ev["is_true"].astype(bool)
    gold = ev["is_correct"].astype(bool)
    fp = ev[pred_accept & (~gold)]
    fn = ev[(~pred_accept) & gold]
    cands = []
    for kind, frame in (("false_positive", fp), ("false_negative", fn)):
        for _, r in frame.head(max_per_class).iterrows():
            cands.append({
                "peripheral": r.get("peripheral", ""), "register": r.get("register", ""),
                "field_name": r.get("field_name", "") or "", "key": r.get("key", ""),
                "value": r.get("correct_value", ""),
                "is_true": bool(r.get("is_correct")),          # the CORRECT label to teach
                "ground_truth_value": r.get("original_value", r.get("correct_value", "")),
                "ground_truth_field_name": r.get("original_field_name", r.get("field_name", "") or ""),
                "validator_said": "accept(true)" if r.get("is_true") else "reject(false)",
                "mistake": kind,
                "datasheet_excerpt": "",   # <- human: paste the supporting datasheet text
                "reasoning": "",           # <- human: why the conclusion holds
            })
    payload = {
        "_comment": ("Curation template (once per vendor). Keep the instructive rows, fill "
                     "datasheet_excerpt + reasoning, then pass --curated-examples <this file>. "
                     "`is_true` is the correct label; rows with an empty datasheet_excerpt are "
                     "ignored."),
        "examples": cands,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return len(cands)


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


def _score_grid(scores):
    uniq = sorted(set(scores))
    # Candidate cut points: each observed score (so >= tau lands on it), plus extremes.
    return [0.0] + [u for u in uniq] + [1.0001]


def tune_threshold(scores, golds, grid=None) -> float:
    """Pick the threshold maximising F1 on (scores, golds). Ties -> lower threshold."""
    if grid is None:
        grid = _score_grid(scores)
    best_tau, best_f1 = 0.5, -1.0
    for tau in grid:
        f1 = confusion_at(scores, golds, tau).f1
        if f1 > best_f1:
            best_f1, best_tau = f1, tau
    return best_tau


def tune_threshold_precision(scores, golds, target_precision: float, grid=None) -> float:
    """Operating point for the operational gate: the threshold that maximises **yield**
    (recall) subject to precision >= target_precision on (scores, golds).

    Among feasible thresholds (training precision >= target, at least one predicted
    positive) pick the one with the highest recall; ties -> lower threshold (more yield).
    If the target is unreachable on this training partition, fall back to the
    highest-precision threshold (then highest recall) so the gate is as clean as it can
    be — the held-out precision will then show the target was missed.
    """
    if grid is None:
        grid = _score_grid(scores)
    best_feasible = None     # (recall, -tau) to maximise
    best_fallback = None     # (precision, recall, -tau) to maximise when infeasible
    for tau in grid:
        cm = confusion_at(scores, golds, tau)
        if (cm.tp + cm.fp) == 0:
            continue  # gate accepts nothing — no precision defined / useless
        fb_key = (cm.precision, cm.recall, -tau)
        if best_fallback is None or fb_key > best_fallback[0]:
            best_fallback = (fb_key, tau)
        if cm.precision >= target_precision:
            key = (cm.recall, -tau)
            if best_feasible is None or key > best_feasible[0]:
                best_feasible = (key, tau)
    if best_feasible is not None:
        return best_feasible[1]
    if best_fallback is not None:
        return best_fallback[1]
    return 1.0001  # degenerate: accept nothing


def make_tuner(objective: str = "precision", target_precision: float = 0.95):
    """Return a `(scores, golds) -> tau` threshold tuner for the chosen objective.

    objective="precision" (default, operational): yield-maximising at precision >= target.
    objective="f1": legacy max-F1 tuning.
    """
    if objective == "f1":
        return lambda scores, golds: tune_threshold(scores, golds)
    if objective == "precision":
        return lambda scores, golds: tune_threshold_precision(scores, golds, target_precision)
    raise ValueError(f"unknown threshold objective: {objective!r} (use 'precision' or 'f1')")


@dataclass
class FoldResult:
    fold: int
    tau: float
    cm: ConfusionMatrix


def cross_validate(evaluated: pd.DataFrame, k: int, tuner=None) -> dict:
    """k-fold: tune threshold on training rows, evaluate on held-out fold.

    `evaluated` must have columns: fold, is_correct, score. `tuner(scores, golds) -> tau`
    selects the gate threshold (defaults to max-F1 for backward compatibility; pass
    make_tuner("precision", target) for the operational gate). Returns a dict with
    per-fold results, the aggregated tuned confusion matrix, the untuned (tau=0.5)
    confusion matrix, and the calibration result.
    """
    tuner = tuner or (lambda scores, golds: tune_threshold(scores, golds))
    fold_results: list[FoldResult] = []
    agg = ConfusionMatrix(0, 0, 0, 0)
    ev = evaluated.copy()
    ev["tau"] = float("nan")
    for f in range(k):
        train = evaluated[evaluated["fold"] != f]
        test = evaluated[evaluated["fold"] == f]
        if len(test) == 0:
            continue
        tau = tuner(list(train["score"]), list(train["is_correct"]))
        cm = confusion_at(list(test["score"]), list(test["is_correct"]), tau)
        fold_results.append(FoldResult(fold=f, tau=tau, cm=cm))
        agg = agg + cm
        ev.loc[ev["fold"] == f, "tau"] = tau

    untuned = confusion_at(list(evaluated["score"]), list(evaluated["is_correct"]), 0.5)
    calib = calibrate(agg)
    return {
        "fold_results": fold_results,
        "aggregated": agg,
        "untuned_tau0.5": untuned,
        "calibration": calib,
        "eval": ev,  # evaluated rows with each row's held-out fold tau attached
    }


# --------------------------------------------------------------------------- #
# Operational artifacts: ranked review queue, precision@k, calibration
# --------------------------------------------------------------------------- #

# Columns surfaced to a human reviewer in the ranked queue (identity + decision signal).
_QUEUE_COLS = ["rank", "score", "confidence_score", "is_true", "is_correct",
               "peripheral", "register", "field_name", "alt_name", "key", "correct_value",
               "corruption_type", "fold", "tau", "reasoning"]


def build_review_queue(tuned_eval: pd.DataFrame) -> pd.DataFrame:
    """The reviewer-facing artifact: gate survivors (score >= the fold's tuned tau),
    ranked by confidence descending. Each row is a candidate bug a human would confirm
    against the datasheet, highest-confidence first; `is_correct` marks whether it is in
    fact a real bug (for offline precision@k). V=0 rows are intentionally absent — they
    are the candidates the gate drops unseen.
    """
    te = tuned_eval.copy()
    if len(te) == 0 or "tau" not in te.columns:
        te["v1"] = False
    else:
        te["v1"] = te["score"] >= te["tau"]
    surv = te[te["v1"]].copy()
    # score == confidence for V=1 survivors (tau >= 0.5); confidence_score breaks ties.
    surv = surv.sort_values(["score", "confidence_score"], ascending=False).reset_index(drop=True)
    surv.insert(0, "rank", range(1, len(surv) + 1))
    return surv


def precision_at_k_table(queue: pd.DataFrame,
                         fractions=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)) -> pd.DataFrame:
    """Front-loading quality of the ranked queue: precision among the top-k, the true
    bugs found by then, and what fraction of all queued true bugs that is. This is the
    "review the top X% -> catch Y% of the bugs" curve the reviewer time budget reads."""
    n = len(queue)
    total_true = int(queue["is_correct"].sum()) if n else 0
    rows = []
    for frac in fractions:
        k = max(1, int(round(frac * n))) if n else 0
        top = queue.iloc[:k]
        tp = int(top["is_correct"].sum()) if k else 0
        rows.append({
            "fraction": frac,
            "k": k,
            "precision_at_k": (tp / k) if k else float("nan"),
            "true_bugs_found": tp,
            "yield_of_queue": (tp / total_true) if total_true else float("nan"),
            "min_score_in_topk": float(top["score"].min()) if k else float("nan"),
        })
    return pd.DataFrame(rows)


def reliability_table(queue: pd.DataFrame, n_bins: int = 10) -> pd.DataFrame:
    """Calibration of the confidence on the reviewed (survivor) set: per confidence bin,
    mean confidence vs empirical precision (fraction actually real). If these track, a
    reviewer can convert a confidence cutoff into an expected hit-rate and stop at the
    depth their labour budget justifies.
    """
    cols = ["bin_lo", "bin_hi", "n", "mean_confidence", "empirical_precision"]
    if len(queue) == 0:
        return pd.DataFrame(columns=cols)
    conf = queue["confidence_score"].astype(float)
    rows = []
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        if b == n_bins - 1:
            sel = queue[(conf >= lo) & (conf <= hi)]
        else:
            sel = queue[(conf >= lo) & (conf < hi)]
        if len(sel) == 0:
            continue
        rows.append({
            "bin_lo": lo, "bin_hi": hi, "n": len(sel),
            "mean_confidence": float(sel["confidence_score"].astype(float).mean()),
            "empirical_precision": float(sel["is_correct"].mean()),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def _write_prompt_versions(out_dir: str, model_name: str, base_system_prompt: str,
                           curated_block: str) -> None:
    """Persist the exact prompts used: the base system prompt (baseline pass) and the
    curated-examples block appended for the curated pass (empty if none)."""
    pdir = os.path.join(out_dir, "prompts")
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "base_system_prompt.txt"), "w") as fh:
        fh.write(base_system_prompt)
    with open(os.path.join(pdir, "curated_examples_block.txt"), "w") as fh:
        fh.write(curated_block or "(no curated examples loaded; baseline only)")
    with open(os.path.join(pdir, f"prompt_versions_{model_name}.md"), "w") as fh:
        fh.write("\n".join([
            f"# Validator prompt versions — {model_name}", "",
            "The baseline pass uses the base system prompt (which already carries static",
            "reasoning examples). The curated pass appends the human-curated examples",
            "below (invariant + datasheet excerpt + conclusion), once per manufacturer.", "",
            "## Curated examples block", "", "```", curated_block or "(none)", "```", "",
            "## Base system prompt", "", "```", base_system_prompt, "```",
        ]))


# USD per 1M tokens (input, output). Best-effort defaults — VERIFY against current vendor
# pricing and/or override per run with --price-in / --price-out. Tokens are ALWAYS
# recorded exactly; cost is just tokens*price (left blank when no price is known).
_PRICING = {
    # model_name: (usd_per_1M_input, usd_per_1M_output)
}


def _summarize_usage(usage_rows, model_name="", price_in=None, price_out=None):
    """Aggregate per-call usage records into totals (+ optional $ cost). Returns
    (summary_dict, per_call_DataFrame)."""
    if not usage_rows:
        return {"n_calls": 0, "input_tokens": 0, "output_tokens": 0,
                "reasoning_tokens": 0, "total_tokens": 0,
                "price_in_per_1m": price_in, "price_out_per_1m": price_out,
                "est_cost_usd": None}, pd.DataFrame()
    udf = pd.DataFrame(usage_rows)
    if price_in is None and model_name in _PRICING:
        price_in = _PRICING[model_name][0]
    if price_out is None and model_name in _PRICING:
        price_out = _PRICING[model_name][1]
    tin, tout = int(udf["input_tokens"].sum()), int(udf["output_tokens"].sum())
    cost = (tin / 1e6 * price_in + tout / 1e6 * price_out) \
        if (price_in is not None and price_out is not None) else None
    summary = {
        "n_calls": int(len(udf)),
        "input_tokens": tin, "output_tokens": tout,
        "reasoning_tokens": int(udf["reasoning_tokens"].sum()),
        "total_tokens": int(udf["total_tokens"].sum()),
        "input_tokens_baseline": int(udf[udf["tag"] == "baseline"]["input_tokens"].sum()),
        "output_tokens_baseline": int(udf[udf["tag"] == "baseline"]["output_tokens"].sum()),
        "input_tokens_tuned": int(udf[udf["tag"] != "baseline"]["input_tokens"].sum()),
        "output_tokens_tuned": int(udf[udf["tag"] != "baseline"]["output_tokens"].sum()),
        "price_in_per_1m": price_in, "price_out_per_1m": price_out,
        "est_cost_usd": cost,
    }
    return summary, udf


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


def write_outputs(out_dir: str, model_name: str, baseline_cv: dict, curated_cv: dict,
                  base_system_prompt: str = "", curated_block: str = "",
                  operational_meta: Optional[dict] = None,
                  usage_rows: Optional[list] = None, price_in=None, price_out=None) -> None:
    """Write the cross-validation results + operational artifacts + usage accounting.

    `curated_cv` is the headline (after curated examples); `baseline_cv` is reported
    alongside to show the lift. When no curated examples were loaded, curated_cv ==
    baseline_cv (lift 0). Each cv dict carries `eval` (rows with per-fold tau).
    """
    os.makedirs(out_dir, exist_ok=True)
    curated = curated_cv is not baseline_cv
    final_eval = curated_cv["eval"]

    # Per-row judgments (auditable; includes reasoning + tau). Also the baseline eval when
    # a curated pass changed it.
    final_eval.to_csv(os.path.join(out_dir, f"judgments_{model_name}.csv"), index=False)
    if curated:
        baseline_cv["eval"].to_csv(os.path.join(out_dir, f"judgments_baseline_{model_name}.csv"), index=False)

    # FP/FN error-analysis on the baseline at the raw judgment — the curation candidates.
    bev = baseline_cv["eval"].copy()
    bev["pred_v1"] = bev["is_true"].astype(bool)
    fp_fn = bev[((bev["pred_v1"]) & (~bev["is_correct"])) | ((~bev["pred_v1"]) & (bev["is_correct"]))]
    cols = ["peripheral", "register", "field_name", "alt_name", "key", "correct_value",
            "original_value", "is_correct", "corruption_type", "is_true", "confidence_score",
            "score", "reasoning"]
    fp_fn[[c for c in cols if c in fp_fn.columns]].to_csv(
        os.path.join(out_dir, f"error_analysis_{model_name}.csv"), index=False)

    # Per-fold confusion + thresholds, baseline vs curated side by side.
    per_fold_rows = []
    base_by_fold = {fr.fold: fr for fr in baseline_cv["fold_results"]}
    for fr in curated_cv["fold_results"]:
        b = base_by_fold.get(fr.fold)
        per_fold_rows.append({
            "fold": fr.fold, "tau": fr.tau,
            "tp": fr.cm.tp, "fp": fr.cm.fp, "tn": fr.cm.tn, "fn": fr.cm.fn,
            "f1": fr.cm.f1, "precision": fr.cm.precision, "recall": fr.cm.recall,
            "baseline_f1": b.cm.f1 if b else None,
        })
    pd.DataFrame(per_fold_rows).to_csv(os.path.join(out_dir, f"per_fold_{model_name}.csv"), index=False)

    # Operational artifacts (from the final held-out judgments): ranked review queue,
    # precision@k curve, confidence calibration table.
    queue = build_review_queue(final_eval)
    queue_cols = [c for c in _QUEUE_COLS if c in queue.columns]
    queue[queue_cols].to_csv(os.path.join(out_dir, f"review_queue_{model_name}.csv"), index=False)
    pk = precision_at_k_table(queue)
    pk.to_csv(os.path.join(out_dir, f"precision_at_k_{model_name}.csv"), index=False)
    reliability_table(queue).to_csv(os.path.join(out_dir, f"calibration_{model_name}.csv"), index=False)

    t_agg = curated_cv["aggregated"]
    total_true = int(final_eval["is_correct"].sum()) if len(final_eval) else 0
    n_total = len(final_eval)
    operational = {
        **(operational_meta or {}),
        "curated_examples_used": bool(curated_block),
        "n_candidates": n_total,
        "n_reviewed": int(len(queue)),
        "n_dropped_unseen": int(n_total - len(queue)),
        "gate_precision": t_agg.precision,
        "yield_recall": t_agg.recall,
        "true_bugs_total": total_true,
        "true_bugs_kept": int(t_agg.tp),
        "true_bugs_dropped_unseen": int(t_agg.fn),
        "precision_at_top_decile": (float(pk.iloc[0]["precision_at_k"]) if len(pk) else float("nan")),
    }

    usage_summary, udf = _summarize_usage(usage_rows or [], model_name=model_name,
                                          price_in=price_in, price_out=price_out)
    if len(udf):
        udf.to_csv(os.path.join(out_dir, f"usage_{model_name}.csv"), index=False)

    summary = {
        "model": model_name,
        "operational": operational,
        "usage": usage_summary,
        "baseline": {
            "aggregated_confusion": baseline_cv["aggregated"].to_dict(),
            "calibration": baseline_cv["calibration"].to_dict(),
        },
        "curated": {
            "aggregated_confusion": curated_cv["aggregated"].to_dict(),
            "calibration": curated_cv["calibration"].to_dict(),
        },
    }
    with open(os.path.join(out_dir, f"summary_{model_name}.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    pd.DataFrame([
        _agg_summary_row(model_name, "baseline", baseline_cv),
        _agg_summary_row(model_name, "curated", curated_cv),
    ]).to_csv(os.path.join(out_dir, f"summary_{model_name}.csv"), index=False)

    _write_prompt_versions(out_dir, model_name, base_system_prompt, curated_block)

    b_agg = baseline_cv["aggregated"]
    t_calib = curated_cv["calibration"]
    obj = operational.get("objective", "?")
    tgt = operational.get("target_precision")
    print(f"  wrote outputs to {out_dir}")
    label = "curated" if curated else "baseline-only (no curated examples loaded)"
    print(f"  baseline F1={b_agg.f1:.3f}  ->  {label} F1={t_agg.f1:.3f}  (lift {t_agg.f1 - b_agg.f1:+.3f})")
    print(f"  gate [{obj}{'' if tgt is None else f' target={tgt}'}]: "
          f"precision={t_agg.precision:.3f}  yield/recall={t_agg.recall:.3f}  "
          f"(reviewed {operational['n_reviewed']}/{n_total}, "
          f"dropped {operational['true_bugs_dropped_unseen']} real bugs unseen)")
    print(f"  ranked queue: precision@top-10%={operational['precision_at_top_decile']:.3f}  "
          f"-> review_queue_{model_name}.csv")
    print(f"  calibration: alpha={t_agg.alpha}  beta={t_agg.beta}  "
          f"pi={t_calib.pi}  validated_precision={t_calib.validated_precision}")
    cost = usage_summary.get("est_cost_usd")
    print(f"  usage: {usage_summary['n_calls']} calls  "
          f"in={usage_summary['input_tokens']:,}  out={usage_summary['output_tokens']:,}  "
          f"reasoning={usage_summary['reasoning_tokens']:,}  total={usage_summary['total_tokens']:,}"
          + (f"  est_cost=${cost:.2f}" if cost is not None else "  (set --price-in/--price-out for $)"))


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
    max_per_call: int = DEFAULT_MAX_PER_CALL,
    access_legend: str = "",
    objective: str = "precision",
    target_precision: float = 0.95,
    use_alt_name: bool = True,
    price_in=None,
    price_out=None,
    curated_examples_path: Optional[str] = None,
) -> dict:
    """End-to-end for one model.

    Pass 1 (baseline): evaluate every invariant with the base prompt (which carries the
    static reasoning examples). The Validator's mistakes are exported as CURATION
    CANDIDATES for a human to turn into datasheet-grounded examples (once per vendor).
    Pass 2 (curated): only if `curated_examples_path` is given — re-evaluate every
    invariant with those curated examples injected, to measure the lift. Both passes are
    cross-validated (gate threshold tuned per fold on training scores).

    `objective`/`target_precision` choose the gate operating point. `retrieve_fn` is the
    retrieval backend.
    """
    tuner = make_tuner(objective, target_precision)
    usage_rows: list = []  # per-LLM-call token log, populated across both passes
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

    base_system = create_batched_validator_system_prompt(access_legend, name_aliasing=use_alt_name)

    print(f"[{model_name}] pass 1: baseline evaluation (base prompt + static examples)")
    baseline_eval = evaluate_benchmark(
        benchmark, model_name, retrieve_fn, reasoning_effort=reasoning_effort,
        max_per_call=max_per_call, access_legend=access_legend, use_alt_name=use_alt_name,
        usage_sink=usage_rows)
    baseline_cv = cross_validate(baseline_eval, k=k, tuner=tuner)
    cov = baseline_eval["reg_in_context"].mean() if "reg_in_context" in baseline_eval else float("nan")
    n_parse_err = (baseline_eval["parse_error"].fillna("") != "").sum()
    print(f"[{model_name}] retrieval coverage: register name present for {cov:.0%} of invariants; "
          f"{n_parse_err} rows with parse/retrieval errors")

    # Export curation candidates (the human seeds the per-vendor curated file from these).
    os.makedirs(out_dir, exist_ok=True)
    n_cand = export_curation_candidates(
        baseline_cv["eval"], os.path.join(out_dir, f"curation_candidates_{model_name}.json"))
    print(f"[{model_name}] exported {n_cand} curation candidates -> "
          f"curation_candidates_{model_name}.json")

    # Pass 2 (curated): only if a curated-examples file is provided.
    curated_block = load_curated_examples(curated_examples_path)
    if curated_block:
        n_ex = curated_block.count("Example ")
        print(f"[{model_name}] pass 2: curated evaluation ({n_ex} examples from {curated_examples_path})")
        curated_eval = evaluate_benchmark(
            benchmark, model_name, retrieve_fn, reasoning_effort=reasoning_effort,
            max_per_call=max_per_call, access_legend=access_legend, use_alt_name=use_alt_name,
            usage_sink=usage_rows, extra_system_text=curated_block, progress_label=" curated")
        curated_cv = cross_validate(curated_eval, k=k, tuner=tuner)
    else:
        if curated_examples_path:
            print(f"[{model_name}] --curated-examples {curated_examples_path} has no usable "
                  "examples (fill datasheet_excerpt); reporting baseline only")
        else:
            print(f"[{model_name}] no curated examples; reporting baseline only "
                  "(fill the candidates file, then re-run with --curated-examples)")
        curated_cv = baseline_cv

    write_outputs(out_dir, model_name, baseline_cv, curated_cv,
                  base_system_prompt=base_system, curated_block=curated_block,
                  operational_meta={"objective": objective, "target_precision": target_precision,
                                    "use_alt_name": use_alt_name, "seed": seed,
                                    "corruption_fraction": corruption_fraction},
                  usage_rows=usage_rows, price_in=price_in, price_out=price_out)
    return {"baseline": baseline_cv, "curated": curated_cv}


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
    ap.add_argument("--objective", choices=["precision", "f1"], default="precision",
                    help="gate operating point: 'precision' (default) maximises yield at "
                         "precision >= --target-precision; 'f1' restores max-F1 tuning")
    ap.add_argument("--target-precision", type=float, default=0.95,
                    help="target gate precision for --objective precision (default 0.95)")
    ap.add_argument("--use-alt-name", dest="use_alt_name", action="store_true", default=True,
                    help="use the verified datasheet's alt_name (datasheet-printed name) to "
                         "reduce name-mismatch false negatives — adds a name-aliasing prompt "
                         "rule + a per-row datasheet_name hint (default: on)")
    ap.add_argument("--no-alt-name", dest="use_alt_name", action="store_false",
                    help="ablation: disable alt_name handling (strict SVD-name matching)")
    ap.add_argument("--max-per-call", type=int, default=DEFAULT_MAX_PER_CALL,
                    help="max invariants per LLM call; large registers are chunked + "
                         "split-retried on parse failure (default 12)")
    ap.add_argument("--price-in", type=float, default=None,
                    help="USD per 1M input tokens (for the cost estimate; tokens are "
                         "always recorded regardless)")
    ap.add_argument("--price-out", type=float, default=None,
                    help="USD per 1M output tokens (for the cost estimate)")
    ap.add_argument("--curated-examples", default=None,
                    help="path to a per-vendor curated-examples JSON (datasheet-grounded "
                         "examples) for the second pass; omit to run baseline-only and "
                         "export curation candidates")
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
            access_legend=legend, objective=args.objective,
            target_precision=args.target_precision, use_alt_name=args.use_alt_name,
            price_in=args.price_in, price_out=args.price_out,
            curated_examples_path=args.curated_examples)
        return

    print(f"Running cross-validation for {len(models)} model(s): "
          f"{', '.join(m['model_name'] for m in models)}")
    for cfg in models:
        out_dir = os.path.join(out_root, cfg["model_name"])
        run_model(
            args.verified_csv, cfg["model_name"], out_dir, retrieve_fn,
            k=args.k, corruption_fraction=args.corruption_fraction, seed=args.seed,
            reasoning_effort=cfg.get("reasoning_effort"), max_per_call=args.max_per_call,
            access_legend=legend, objective=args.objective,
            target_precision=args.target_precision, use_alt_name=args.use_alt_name,
            price_in=args.price_in, price_out=args.price_out,
            curated_examples_path=args.curated_examples)


if __name__ == "__main__":
    main()
    # The OpenEvolve backend leaves non-daemon ChromaDB/onnxruntime threads alive,
    # which keeps the interpreter from exiting after all work + outputs are done.
    # Force a clean exit so background/timeout-wrapped runs terminate promptly.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
