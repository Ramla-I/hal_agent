#!/usr/bin/env python3
"""Corroboration analysis: is each HAL enforcement hit already handled?

When the unmodified HAL crate fails at a constrained call site, two stories
hide behind the same compile error:

  corroborated -- the HAL already performs the datasheet-prescribed check
                  nearby (e.g. busy-waits on the flag before writing). The
                  gate did not catch a bug; it corroborates the constraint
                  and marks a mechanical witnessed-call migration site.
  unchecked    -- the HAL performs the operation with NO nearby check: a
                  candidate latent bug (and a potential upstream report).

This tool classifies every enforcement hit three ways and reports where the
methods disagree (those rows go to a human):

  1. deterministic scan -- does the enclosing function reference the
     precondition fields before the flagged line?
  2. LLM judge (the calibrated gpt-oss validator, closed-book: constraint +
     quote + enclosing function only),
  3. (human review of the shortlist happens outside this tool.)

Usage:
    python applications/pac_codegen/experiments/corroboration.py [--only f4|f1]
                                                                 [--no-judge]

Outputs JSONL under experiments/out/ (git-ignored) and prints per-target
tables; docs/hal_corroboration.md is the committed report.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent   # applications/pac_codegen
REPO = APP_DIR.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(APP_DIR))

import get_pac  # noqa: E402
from core import constraint_validator as cv_judge  # noqa: E402

OUT_DIR = APP_DIR / "experiments" / "out"

TARGETS = {
    "f4": {
        "crate": "stm32f4", "version": "0.16.0", "device": "stm32f405",
        "peripheral": "i2c1",
        "fixture": APP_DIR / "constraint_test" / "stm32f405_i2c1.json",
        "hal": ("stm32f4xx-hal", "=0.23.0", ["stm32f405"]),
        "concrete_token": "i2c1::cr1",
    },
    "f1": {
        "crate": "stm32f1", "version": "0.16.0", "device": "stm32f103",
        "peripheral": "i2c1",
        "fixture": APP_DIR / "experiments" / "fixtures" / "rm0008_i2c1_cr1.json",
        "hal": ("stm32f1xx-hal", "=0.11.0", ["stm32f103", "medium"]),
        "concrete_token": "i2c1::cr1",
    },
}

JUDGE_SYSTEM = """You review embedded Rust driver code against a hardware
datasheet constraint. You receive the constraint (operation, preconditions,
the datasheet's verbatim sentence) and ONE driver function whose flagged line
performs the constrained operation. Judge ONLY from the given code.

Question: does this function already establish or verify the constraint's
preconditions before the flagged line (e.g. polling/checking the named flags,
or a loop that waits for them to clear)? A check AFTER the flagged line, or
of unrelated flags, does not count.

Respond with a single JSON object, keys exactly:
{"verdict": "corroborated" | "unchecked" | "unclear",
 "evidence": "<the code line that performs the check, or empty>",
 "reason": "<one sentence>"}"""


def snapshot(pac_dir: Path, device: str, tmp: Path):
    shutil.copy2(pac_dir / "src" / "generic.rs", tmp / "generic.rs")
    shutil.copytree(pac_dir / "src" / device, tmp / device)


def restore(pac_dir: Path, device: str, tmp: Path):
    import os
    shutil.copy2(tmp / "generic.rs", pac_dir / "src" / "generic.rs")
    shutil.rmtree(pac_dir / "src" / device)
    shutil.copytree(tmp / device, pac_dir / "src" / device)
    # Defeat cargo's diagnostic replay: old mtimes read as "fresh".
    os.utime(pac_dir / "src" / "generic.rs")
    for f in (pac_dir / "src" / device).rglob("*"):
        if f.is_file():
            import os as _os
            _os.utime(f)


def make_workspace(ws: Path, hal: tuple, pac_crate: str, pac_dir: Path):
    name, version, features = hal
    (ws / "src").mkdir(parents=True, exist_ok=True)
    (ws / "src" / "lib.rs").write_text(
        "#![no_std]\npub use {} as hal;\n".format(name.replace("-", "_")))
    feats = ", ".join(f'"{f}"' for f in features)
    (ws / "Cargo.toml").write_text(
        f'[package]\nname = "corroboration-probe"\nversion = "0.1.0"\n'
        f'edition = "2021"\n\n[dependencies]\n'
        f'{name} = {{ version = "{version}", features = [{feats}] }}\n\n'
        f"[patch.crates-io]\n{pac_crate} = {{ path = \"{pac_dir}\" }}\n")


def enforcement_hits(ws: Path, hal_name: str, concrete_token: str) -> list[dict]:
    """cargo-check the workspace; return deduped concrete enforcement hits
    with their HAL source file (absolute) and line."""
    run = subprocess.run(["cargo", "check", "--message-format=json"],
                         cwd=str(ws), capture_output=True, text=True)
    hits = {}
    for line in run.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        msg = d.get("message", "")
        if "constrained by its datasheet" not in msg or concrete_token not in msg:
            continue
        spans = []

        def walk(ss):
            for s in ss:
                fn = s.get("file_name", "")
                if hal_name in fn:
                    spans.append((fn, s.get("line_start")))
                exp = s.get("expansion")
                if exp and exp.get("span"):
                    walk([exp["span"]])

        walk(d.get("spans", []))
        for ch in d.get("children", []):
            walk(ch.get("spans", []))
        if spans:
            fn, ln = sorted(spans)[0]
            hits.setdefault((fn, ln), {
                "file": fn, "line": ln,
                "operation": ("modify" if "modify-constrained" in msg
                              else "write"),
            })
    return [hits[k] for k in sorted(hits)]


FN_RE = re.compile(r"^\s*(pub(\([^)]*\))?\s+)?(unsafe\s+)?fn\s+\w+")


def enclosing_function(path: str, line: int, max_lines: int = 140):
    """Return (start_line, snippet) of the function containing `line`, the
    flagged line marked. Brace counting is approximate but fine for triage."""
    lines = Path(path).read_text().splitlines()
    start = None
    for i in range(min(line, len(lines)) - 1, -1, -1):
        if FN_RE.match(lines[i]):
            start = i
            break
    if start is None:
        start = max(0, line - 20)
    depth = 0
    end = start
    opened = False
    for j in range(start, min(len(lines), start + 400)):
        depth += lines[j].count("{") - lines[j].count("}")
        if "{" in lines[j]:
            opened = True
        end = j
        if opened and depth <= 0:
            break
    body = lines[start:end + 1][:max_lines]
    out = []
    for k, text in enumerate(body, start=start + 1):
        marker = "   // <-- FLAGGED (constrained operation)" if k == line else ""
        out.append(f"{text}{marker}")
    return start + 1, "\n".join(out)


def deterministic_scan(snippet: str, flagged_line_rel: int,
                       fields: list[str]) -> dict:
    """Does the function reference any precondition field accessor before the
    flagged line?"""
    lines = snippet.splitlines()
    pat = re.compile("|".join(rf"\.{f}\s*\(" for f in fields))
    before = [i for i, t in enumerate(lines[:flagged_line_rel]) if pat.search(t)]
    anywhere = [i for i, t in enumerate(lines) if pat.search(t)]
    return {
        "fields": fields,
        "check_before_flag": bool(before),
        "check_anywhere": bool(anywhere),
        "verdict": "corroborated" if before else "unchecked",
    }


def judge_hit(client, constraint: dict, snippet: str, operation: str) -> dict:
    user = (
        f"CONSTRAINT (operation: {operation})\n"
        f"preconditions: {json.dumps(constraint['preconditions'])}\n"
        f"datasheet says: \"{constraint['datasheet_text']}\"\n\n"
        f"DRIVER FUNCTION (the flagged line is marked):\n```rust\n{snippet}\n```"
    )
    messages = [{"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user}]
    for attempt in range(2):
        text, _ptok, _ctok = cv_judge._call_with_backoff(
            client, cv_judge.MODEL, messages)
        obj = cv_judge.extract_json_block(text)
        if isinstance(obj, dict) and obj.get("verdict") in (
                "corroborated", "unchecked", "unclear"):
            obj["parse_recovered"] = attempt > 0
            return obj
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content":
                         "Respond with ONLY the JSON object."})
    return {"verdict": "unclear", "evidence": "",
            "reason": "judge output unparseable", "parse_recovered": True}


def run_target(name: str, cfg: dict, use_judge: bool) -> list[dict]:
    print(f"\n=== {name}: {cfg['hal'][0]} {cfg['hal'][1]} vs injected "
          f"{cfg['crate']} ===")
    pac_dir = get_pac.provision(crate=cfg["crate"], version=cfg["version"])
    fixture = json.loads(cfg["fixture"].read_text())
    constraint = fixture["access_constraints_v2"][0]
    fields = sorted({p["field"].lower()
                     for p in constraint["preconditions"]})

    records = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        snapshot(pac_dir, cfg["device"], tmp)
        try:
            inject = subprocess.run(
                [sys.executable, str(APP_DIR / "rust_codegen.py"),
                 str(cfg["fixture"]), "--peripheral", cfg["peripheral"],
                 "--inject-pac", str(pac_dir), "--device", cfg["device"]],
                capture_output=True, text=True)
            if inject.returncode != 0:
                raise RuntimeError("injection failed:\n" + inject.stderr)
            ws = tmp / "ws"
            make_workspace(ws, cfg["hal"], cfg["crate"], pac_dir)
            hits = enforcement_hits(ws, f"{cfg['hal'][0]}-", cfg["concrete_token"])
            print(f"  enforcement hits: {len(hits)}")

            client = cv_judge.make_client() if use_judge else None
            for h in hits:
                start, snippet = enclosing_function(h["file"], h["line"])
                det = deterministic_scan(snippet, h["line"] - start, fields)
                rec = {
                    "target": name,
                    "file": h["file"].split(f"{cfg['hal'][0]}-")[-1],
                    "line": h["line"], "operation": h["operation"],
                    "deterministic": det,
                }
                if client:
                    rec["judge"] = judge_hit(client, constraint, snippet,
                                             h["operation"])
                    rec["agreement"] = (rec["judge"]["verdict"]
                                        == det["verdict"])
                records.append(rec)
        finally:
            restore(pac_dir, cfg["device"], tmp)
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=sorted(TARGETS))
    ap.add_argument("--no-judge", action="store_true",
                    help="deterministic scan only (no API calls)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_records = []
    for name, cfg in TARGETS.items():
        if args.only and name != args.only:
            continue
        recs = run_target(name, cfg, use_judge=not args.no_judge)
        all_records.extend(recs)
        out = OUT_DIR / f"corroboration_{name}.jsonl"
        out.write_text("".join(
            json.dumps(r, sort_keys=True) + "\n" for r in recs))
        print(f"  -> {out}")

    print(f"\n{'target':4} {'file:line':38} {'op':6} {'scan':13} "
          f"{'judge':13} agree")
    for r in all_records:
        j = r.get("judge", {}).get("verdict", "-")
        a = {True: "yes", False: "NO"}.get(r.get("agreement"), "-")
        print(f"{r['target']:4} {r['file'] + ':' + str(r['line']):38} "
              f"{r['operation']:6} {r['deterministic']['verdict']:13} "
              f"{j:13} {a}")


if __name__ == "__main__":
    main()
