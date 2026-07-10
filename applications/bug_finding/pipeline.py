"""Bug-finding pipeline: diff → analyze → classify → report.

``run_bug_finding`` is the single entry point s0's evaluation step hands off to.
It operates on an already-generated run (the generator runs upstream in s0), so
for each SVD file it: computes the typed diff in memory, filters to real SVD bugs
with the analyzer, groups them into bug classes, and writes one review CSV.
"""
from __future__ import annotations

import glob
import os

from utils.utils import setup_logger
from .models import Bug, BugClass, BugStatus
from .diff import diff_generator_against_svd
from .classify import (
    run_analyzer, attach_evidence, classify_bug_classes, split_mechanical_fps,
    load_generator_evidence,
)
from .report import write_review_csv, write_consolidated_from_dir

logger = setup_logger(__name__)


def run_bug_finding(
    svd_dir: str,
    agent_output_dir: str,
    results_dir: str,
    run_analyzer_enabled: bool = True,
    analyzer_models: list[str] | None = None,
) -> dict[str, list[BugClass]]:
    """Find SVD bugs for every SVD file in *svd_dir* against *agent_output_dir*.

    For each SVD it writes ``{results_dir}/{svd}/{svd}_review.csv`` (and the
    analyzer's usage/verdicts alongside) and returns ``{svd_name: [BugClass]}``.

    Args:
        run_analyzer_enabled: if False, skip the LLM filter and treat every
            value-mismatch diff as a (zero-confidence) candidate bug.
        analyzer_models: model list for the analyzer (default
            config.STAGE_MODELS["analyzer"]).
    """
    svd_files = sorted(glob.glob(os.path.join(svd_dir, "*.svd"))
                       + glob.glob(os.path.join(svd_dir, "*.xml")))   # NXP SVDs use .xml
    if not svd_files:
        logger.warning("No SVD files in %s — nothing to do", svd_dir)
        return {}

    results: dict[str, list[BugClass]] = {}
    for svd_path in svd_files:
        svd_name = os.path.splitext(os.path.basename(svd_path))[0]
        out_dir = os.path.join(results_dir, svd_name)

        diffs = diff_generator_against_svd(svd_path, agent_output_dir)

        # Deterministic pre-filter: route clear generator FPs out of the analyzer,
        # but keep them in the CSV pre-marked false_positive (so the FP rate stays
        # visible) rather than silently dropping them.
        fp_pairs, candidates = split_mechanical_fps(diffs)
        fp_bugs = [
            Bug(diff=d, status=BugStatus.FALSE_POSITIVE, datasheet_evidence=f"[auto-FP: {reason}]")
            for d, reason in fp_pairs
        ]

        if run_analyzer_enabled:
            analyzer_bugs = run_analyzer(svd_name, candidates, out_dir, models=analyzer_models)
        else:
            analyzer_bugs = [Bug(diff=d) for d in candidates]
        # Generator reasoning is attached to the CSV as evidence for the human
        # reviewer (the analyzer itself stays context-free; the validator retrieves
        # datasheet context downstream).
        ev_by_reg, ev_by_per = load_generator_evidence(agent_output_dir)
        attach_evidence(analyzer_bugs, ev_by_reg, ev_by_per)

        bugs = analyzer_bugs + fp_bugs
        bug_classes = classify_bug_classes(bugs, svd_name)

        review_path = os.path.join(out_dir, f"{svd_name}_review.csv")
        n_rows = write_review_csv(bug_classes, review_path)
        logger.info(
            "Bug finding for %s: %d rows (%d analyzer-confirmed, %d auto-FP) in %d classes → %s",
            svd_name, n_rows, len(analyzer_bugs), len(fp_bugs), len(bug_classes), review_path,
        )
        results[svd_name] = bug_classes

    # Consolidated, run-level review file: one RM has several SVDs, so a reviewer
    # wants a single sheet for the whole RM with bugs DEDUPED across its SVDs
    # (svd_files lists which share each bug; per-SVD confidence dropped). Reviewer
    # tp_fp labels are preserved across re-runs.
    if results:
        n_total = write_consolidated_from_dir(results_dir)
        logger.info("Consolidated review (deduped across SVDs): %d bugs → %s", n_total, results_dir)

    return results
