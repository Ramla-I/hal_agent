#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
from typing import Iterable, List, Tuple


HEADERS = [
    "iteration",
    "retrieval_method",
    "peripheral_coverage",
    "register_coverage",
    "field_coverage",
    "total_invariants",
    "validator_true_percent",
    "validator_false_percent",
]


def resolve_repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resolve_subfolder_paths(subfolders: Iterable[str]) -> List[str]:
    base_root = os.path.join(resolve_repo_root(), "coverage_improver_optimization")
    resolved = []
    for name in subfolders:
        if os.path.isabs(name):
            resolved.append(name)
        else:
            resolved.append(os.path.join(base_root, name))
    return resolved


def iter_iteration_dirs(base_path: str) -> List[Tuple[str, str]]:
    if not os.path.isdir(base_path):
        return []
    entries = []
    for entry in os.listdir(base_path):
        full_path = os.path.join(base_path, entry)
        if os.path.isdir(full_path):
            entries.append((entry, full_path))
    entries.sort(key=lambda item: int(item[0]) if item[0].isdigit() else item[0])
    return entries


def read_coverage_info(iteration_path: str) -> Tuple[float, float, float]:
    coverage_path = os.path.join(iteration_path, "coverage_improver", "coverage_info.json")
    with open(coverage_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return (
        payload["peripheral_coverage"],
        payload["register_coverage"],
        payload["field_coverage"],
    )


def format_float(value: float) -> str:
    return f"{value:.2f}"


def read_validator_counts(iteration_path: str) -> Tuple[int, int, int]:
    classification_path = os.path.join(iteration_path, "validator", "classification.csv")
    total = 0
    true_count = 0
    false_count = 0
    with open(classification_path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if "agent_judgement" not in reader.fieldnames:
            raise KeyError(
                f"Missing 'agent_judgement' column in {classification_path}"
            )
        for row in reader:
            total += 1
            judgement = (row.get("agent_judgement") or "").strip().lower()
            if judgement == "true":
                true_count += 1
            elif judgement == "false":
                false_count += 1
    return total, true_count, false_count


def read_retrieval_method(base_path: str, iteration_name: str) -> str:
    if not iteration_name.isdigit():
        return ""
    previous_iteration = str(int(iteration_name) - 1)
    if int(iteration_name) <= 0:
        return ""
    output_path = os.path.join(
        base_path,
        previous_iteration,
        "coverage_improver",
        "coverage_improver_output.json",
    )
    if not os.path.isfile(output_path):
        return ""
    with open(output_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return (
        payload.get("context_retrieval_parameters", {})
        .get("context_retrieval_method", "")
    )


def compile_rows(base_path: str) -> List[List[str]]:
    rows = []
    for iteration_name, iteration_path in iter_iteration_dirs(base_path):
        coverage_path = os.path.join(
            iteration_path, "coverage_improver", "coverage_info.json"
        )
        classification_path = os.path.join(
            iteration_path, "validator", "classification.csv"
        )
        if not os.path.isfile(coverage_path) or not os.path.isfile(classification_path):
            continue
        retrieval_method = read_retrieval_method(base_path, iteration_name)
        peripheral, register, field = read_coverage_info(iteration_path)
        total, true_count, false_count = read_validator_counts(iteration_path)
        if total:
            true_percent = (true_count / total) * 100
            false_percent = (false_count / total) * 100
        else:
            true_percent = 0.0
            false_percent = 0.0
        rows.append(
            [
                iteration_name,
                retrieval_method,
                format_float(peripheral),
                format_float(register),
                format_float(field),
                str(total),
                format_float(true_percent),
                format_float(false_percent),
            ]
        )
    return rows


def write_csv(path: str, rows: List[List[str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile coverage and validator summary tables for each iteration."
        )
    )
    parser.add_argument(
        "subfolders",
        nargs="+",
        help=(
            "Subfolder(s) under coverage_improver_optimization, e.g. "
            "'rm0041/gpt-oss-120b'"
        ),
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional output CSV path. Only valid when a single subfolder is given."
        ),
    )
    args = parser.parse_args()

    subfolder_paths = resolve_subfolder_paths(args.subfolders)
    if args.output and len(subfolder_paths) != 1:
        print("--output can only be used with one subfolder.", file=sys.stderr)
        return 2

    for base_path in subfolder_paths:
        rows = compile_rows(base_path)
        if args.output:
            output_path = args.output
        else:
            output_path = os.path.join(base_path, "coverage_summary.csv")
        write_csv(output_path, rows)
        print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
