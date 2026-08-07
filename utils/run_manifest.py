"""Per-run manifest: a structured record of each pipeline run.

Each device run writes ``run_manifest.json`` into its output directory (no central
file → no write races across parallel runs). ``scripts/list_runs.py`` scans them.

Tracked: which datasheet/SVDs, generator model(s), retrieval, output folder,
whether the run is valid (completed with output) and whether it was used
downstream, and whether the analyzer/validator ran.
"""
from __future__ import annotations

import glob
import json
import os
from typing import List, Optional

from pydantic import BaseModel

MANIFEST_NAME = "run_manifest.json"


class RunManifest(BaseModel):
    timestamp: str
    device_name: str
    manufacturer: str
    datasheet: str = ""              # PDF path
    svd_files: List[str] = []
    run_number: int = 0
    output_dir: str = ""             # relative to repo root
    results_dir: str = ""
    retrieval_method: str = ""
    generator_models: List[str] = []
    generator_batched: bool = False
    coverage_improver_iterations: int = 0
    analyzer_used: bool = False
    validator_used: bool = False
    validator_true: int = 0
    validator_false: int = 0
    registers_generated: int = 0
    svd_files_compared: int = 0
    bug_candidates: int = 0          # analyzer-kept candidate rows (status blank)
    auto_fp: int = 0                 # deterministic false-positives
    truncated: bool = False
    success: bool = False
    error: str = ""
    valid: bool = False              # success AND produced generator output
    used: bool = False               # set when this run's output is consumed/submitted


def save_run_manifest(manifest: RunManifest, output_dir: str) -> str:
    """Write the manifest into ``{output_dir}/info/run_manifest.json`` — grouped with
    the run's other metadata (summary.txt, usage.csv, reasoning) in info/, not loose
    at the run root. ``find_run_manifests`` globs recursively, so it still finds it."""
    info_dir = os.path.join(output_dir, "info")
    os.makedirs(info_dir, exist_ok=True)
    path = os.path.join(info_dir, MANIFEST_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))
    return path


def load_run_manifest(path: str) -> RunManifest:
    with open(path, "r", encoding="utf-8") as f:
        return RunManifest.model_validate_json(f.read())


def find_run_manifests(repo_root: str, output_base: str = "agent_output") -> List[RunManifest]:
    """Load every run manifest under the output tree, sorted by timestamp."""
    pattern = os.path.join(repo_root, output_base, "**", MANIFEST_NAME)
    manifests = []
    for path in glob.glob(pattern, recursive=True):
        try:
            manifests.append(load_run_manifest(path))
        except Exception:
            continue
    return sorted(manifests, key=lambda m: (m.timestamp, m.device_name, m.run_number))


def mark_used(repo_root: str, device_name: str, run_number: int, used: bool = True,
              output_base: str = "agent_output") -> Optional[str]:
    """Set the ``used`` flag on a run's manifest. Returns the path, or None if absent."""
    for path in glob.glob(os.path.join(repo_root, output_base, "**", MANIFEST_NAME), recursive=True):
        try:
            m = load_run_manifest(path)
        except Exception:
            continue
        if m.device_name == device_name and m.run_number == run_number:
            m.used = used
            with open(path, "w", encoding="utf-8") as f:
                f.write(m.model_dump_json(indent=2))
            return path
    return None


def runs_table(manifests: List[RunManifest]) -> str:
    """Render manifests as a fixed-width table."""
    header = (f"{'device':<10} {'run':>3} {'valid':>5} {'used':>4} {'analyzer':>8} "
              f"{'regs':>5} {'bugs':>5} {'fp':>4} {'gen models':<28} {'retrieval':<13} {'timestamp':<20}")
    lines = [header, "-" * len(header)]
    for m in manifests:
        lines.append(
            f"{m.device_name:<10} {m.run_number:>3} "
            f"{('yes' if m.valid else 'no'):>5} {('yes' if m.used else '-'):>4} "
            f"{('yes' if m.analyzer_used else 'no'):>8} "
            f"{m.registers_generated:>5} {m.bug_candidates:>5} {m.auto_fp:>4} "
            f"{','.join(m.generator_models)[:28]:<28} {m.retrieval_method:<13} {m.timestamp[:19]:<20}"
        )
    return "\n".join(lines)
