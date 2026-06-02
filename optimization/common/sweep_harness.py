"""
Shared sweep-harness helpers used by retrieval and generator optimization scripts.

These functions used to live as private helpers inside `optimization/retrieval/run_sweep.py`
but are imported by `optimization/generator/optimize_generator.py` and by the smoke tests,
so they belong in a shared module.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Project root on sys.path so `config`, `utils.*`, etc. import cleanly when this module
# is loaded standalone (e.g. by a test that imports only `optimization.common.*`).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import config

from optimization.common.compare_generator_with_verified import (
    compare_outputs,
    load_generator_output,
    load_verified_datasheet,
)
from utils.generator_facts import extract_facts_from_generator_output


def get_user_context(device_name: str):
    """Return the user_contexts entry for `device_name`, or None."""
    return next((ctx for ctx in config.user_contexts if ctx.device_name == device_name), None)


def get_verified_csv_path(device_dir: str, svd: str, peripheral: Optional[str] = None) -> Optional[str]:
    """
    Find the verified datasheet CSV for a device.

    Looks for files matching patterns:
    - verified_datasheet/{mfr}/{device}/{device}_{svd}_full.csv
    - verified_datasheet/{mfr}/{device}/{device}_{svd}_{peripheral}.csv
    """
    parts = device_dir.rstrip("/").split("/")
    if len(parts) < 2:
        return None
    device_name = parts[-1]
    mfr = parts[-2]

    verified_base = f"verified_datasheet/{mfr}/{device_name}"

    if peripheral:
        peripheral_csv = os.path.join(verified_base, f"{device_name}_{svd}_{peripheral}.csv")
        if os.path.exists(peripheral_csv):
            return peripheral_csv

    full_csv = os.path.join(verified_base, f"{device_name}_{svd}_full.csv")
    if os.path.exists(full_csv):
        return full_csv

    return None


def get_verified_registers(verified_csv: str, peripheral: str) -> List[str]:
    """Extract register names for a peripheral from the verified CSV."""
    verified_facts = load_verified_datasheet(verified_csv, peripheral_filter=peripheral)
    return sorted({r for (p, r, f, k) in verified_facts.keys()})


def run_comparison(
    output_dir: str,
    verified_csv: str,
    peripheral_filter: Optional[str] = None,
) -> Dict:
    """
    Compare generator output against verified datasheet and return accuracy metrics.

    Returns a dict with:
      - registers_found, total_registers
      - correct, wrong, missing, total_facts, found_accuracy   (found-register metrics)
      - correct_all, wrong_all, missing_all, total_facts_all, complete_accuracy  (all registers)
      - coverage (fraction of verified facts under found registers)
      - register_results: per-register breakdown
      - fact_errors: per-fact wrong/missing rows
      - accuracy: legacy alias for found_accuracy
    """
    verified_facts = load_verified_datasheet(verified_csv, peripheral_filter=peripheral_filter)

    register_pairs = sorted({(p, r) for (p, r, f, k) in verified_facts.keys()})

    all_generator_facts: Dict = {}
    registers_found = set()
    for peripheral, register in register_pairs:
        output_json = load_generator_output(output_dir, peripheral, register)
        if output_json:
            registers_found.add((peripheral, register))
            facts = extract_facts_from_generator_output(output_json, peripheral, register)
            all_generator_facts.update(facts)

    correct, wrong, missing = compare_outputs(verified_facts, all_generator_facts, registers_found)
    correct_all, wrong_all, missing_all = compare_outputs(
        verified_facts, all_generator_facts, set(register_pairs),
    )

    register_results: List[Dict] = []
    fact_errors: List[Dict] = []

    for peripheral, register in register_pairs:
        verified_reg_facts = {
            k: v for k, v in verified_facts.items()
            if k[0] == peripheral and k[1] == register
        }
        total_verified_reg_facts = len(verified_reg_facts)
        found = (peripheral, register) in registers_found

        if found:
            c_r, w_r, m_r = compare_outputs(
                verified_reg_facts,
                all_generator_facts,
                {(peripheral, register)},
            )
            correct_r = len(c_r)
            wrong_r = len(w_r)
            missing_r = len(m_r)

            for w_item in w_r:
                fact = w_item["fact"]
                fact_errors.append({
                    "error_type": "wrong",
                    "peripheral": fact[0],
                    "register": fact[1],
                    "field_name": fact[2],
                    "key": fact[3],
                    "correct_value": w_item["correct"],
                    "generated_value": w_item["generated"],
                })
            for m_item in m_r:
                fact = m_item["fact"]
                fact_errors.append({
                    "error_type": "missing",
                    "peripheral": fact[0],
                    "register": fact[1],
                    "field_name": fact[2],
                    "key": fact[3],
                    "correct_value": m_item["correct_value"],
                    "generated_value": "",
                })
        else:
            correct_r = 0
            wrong_r = 0
            missing_r = total_verified_reg_facts
            for fact_key, correct_value in verified_reg_facts.items():
                fact_errors.append({
                    "error_type": "missing",
                    "peripheral": fact_key[0],
                    "register": fact_key[1],
                    "field_name": fact_key[2],
                    "key": fact_key[3],
                    "correct_value": correct_value,
                    "generated_value": "",
                })

        total_r = correct_r + wrong_r + missing_r
        acc_r = (correct_r / total_r * 100) if total_r > 0 else 0

        register_results.append({
            "peripheral": peripheral,
            "register": register,
            "register_found": found,
            "correct": correct_r,
            "wrong": wrong_r,
            "missing": missing_r,
            "total_facts": total_r,
            "accuracy": acc_r,
        })

    found_total = len(correct) + len(wrong) + len(missing)
    found_accuracy = (len(correct) / found_total * 100) if found_total > 0 else 0

    complete_total = len(correct_all) + len(wrong_all) + len(missing_all)
    complete_accuracy = (len(correct_all) / complete_total * 100) if complete_total > 0 else 0

    coverage = (found_total / complete_total * 100) if complete_total > 0 else 0

    return {
        "registers_found": len(registers_found),
        "total_registers": len(register_pairs),
        "correct": len(correct),
        "wrong": len(wrong),
        "missing": len(missing),
        "total_facts": found_total,
        "found_accuracy": found_accuracy,
        "correct_all": len(correct_all),
        "wrong_all": len(wrong_all),
        "missing_all": len(missing_all),
        "total_facts_all": complete_total,
        "complete_accuracy": complete_accuracy,
        "coverage": coverage,
        "accuracy": found_accuracy,
        "register_results": register_results,
        "fact_errors": fact_errors,
    }
