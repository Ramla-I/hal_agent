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
from .models import Bug, BugClass
from .diff import diff_generator_against_svd
from .classify import run_analyzer, attach_evidence, classify_bug_classes
from .report import write_review_csv

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
    svd_files = sorted(glob.glob(os.path.join(svd_dir, "*.svd")))
    if not svd_files:
        logger.warning("No SVD files in %s — nothing to do", svd_dir)
        return {}

    results: dict[str, list[BugClass]] = {}
    for svd_path in svd_files:
        svd_name = os.path.splitext(os.path.basename(svd_path))[0]
        out_dir = os.path.join(results_dir, svd_name)

        diffs = diff_generator_against_svd(svd_path, agent_output_dir)

        if run_analyzer_enabled:
            bugs = run_analyzer(svd_name, diffs, out_dir, models=analyzer_models)
        else:
            bugs = [Bug(diff=d) for d in diffs if d.is_value_mismatch]

        attach_evidence(bugs, agent_output_dir)
        bug_classes = classify_bug_classes(bugs, svd_name)

        review_path = os.path.join(out_dir, f"{svd_name}_review.csv")
        n_rows = write_review_csv(bug_classes, review_path)
        logger.info(
            "Bug finding for %s: %d bugs in %d classes → %s",
            svd_name, n_rows, len(bug_classes), review_path,
        )
        results[svd_name] = bug_classes

    return results
