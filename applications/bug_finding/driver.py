"""CLI: find SVD bugs for a device from an already-generated run.

    python -m applications.bug_finding.driver --device rm0091

Defaults to the latest existing generator run for the device (generation itself
runs upstream via core/s0 — typically `scripts/docker_run.sh s0 --devices <dev>`).
Writes one review CSV per SVD file and prints a summary.
"""
from __future__ import annotations

import argparse
import os
import sys

# Ensure repo root is importable when run as a module from anywhere.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import config
from core.s0_run_full_analysis import resolve_device_paths
from applications.bug_finding.pipeline import run_bug_finding


def _resolve_context(device_name: str):
    for ctx in config.user_contexts:
        if ctx.device_name.lower() == device_name.lower():
            return ctx
    raise SystemExit(
        f"Device {device_name!r} not found in config.user_contexts "
        f"(known: {[c.device_name for c in config.user_contexts]})"
    )


def _latest_run(repo_root: str, ctx) -> int:
    base = os.path.join(repo_root, config.OUTPUT_DIR, ctx.manufacturer.value.lower(), ctx.device_name)
    if not os.path.isdir(base):
        return 0
    runs = [int(d) for d in os.listdir(base) if d.isdigit() and os.path.isdir(os.path.join(base, d))]
    return max(runs) if runs else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Find SVD bugs from a generated run")
    parser.add_argument("--device", required=True, help="Device name (e.g. rm0091)")
    parser.add_argument("--run", type=int, help="Run number (default: latest existing)")
    parser.add_argument("--analyzer-models", default=None,
                        help="Comma-separated analyzer model list "
                             f"(default: {','.join(config.STAGE_MODELS['analyzer'])})")
    parser.add_argument("--no-analyzer", action="store_true",
                        help="Skip the analyzer; treat every value mismatch as a candidate bug")
    args = parser.parse_args()
    analyzer_models = (
        [m.strip() for m in args.analyzer_models.split(",") if m.strip()]
        if args.analyzer_models else None
    )

    ctx = _resolve_context(args.device)
    run_number = args.run or _latest_run(_REPO_ROOT, ctx)
    if run_number <= 0:
        raise SystemExit(
            f"No generator run found for {args.device}. Generate first, e.g. "
            f"`scripts/docker_run.sh s0 --devices {args.device}`."
        )

    paths = resolve_device_paths(ctx, _REPO_ROOT, run_number)
    if not os.path.isdir(paths.agent_output_dir):
        raise SystemExit(f"Agent output dir missing: {paths.agent_output_dir}")

    analyzer_label = "off" if args.no_analyzer else ",".join(analyzer_models or config.STAGE_MODELS["analyzer"])
    print(f"Bug finding: {args.device} (run {run_number}), analyzer={analyzer_label}")
    results = run_bug_finding(
        svd_dir=paths.svd_dir,
        agent_output_dir=paths.agent_output_dir,
        results_dir=paths.results_dir,
        run_analyzer_enabled=not args.no_analyzer,
        analyzer_models=analyzer_models,
    )

    print(f"\n{'SVD':<16} {'bugs':>5} {'classes':>8}")
    print("-" * 32)
    for svd_name, bug_classes in results.items():
        n_bugs = sum(len(bc.bugs) for bc in bug_classes)
        print(f"{svd_name:<16} {n_bugs:>5} {len(bug_classes):>8}")
    print(f"\nReview CSVs under: {paths.results_dir}/<svd>/<svd>_review.csv")


if __name__ == "__main__":
    main()
