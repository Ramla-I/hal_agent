#!/usr/bin/env python3
"""Extraction eval for the grammar-v2 generator prompt (roadmap step F).

Runs the CONSTRAINTS-ONLY system prompt -- which shares
ACCESS_CONSTRAINTS_V2_SCHEMA / ACCESS_CONSTRAINTS_V2_GUIDANCE verbatim with
the shipping generator prompts (prompts/register_info_stm.py) -- over a fixed,
committed register sample (eval_expectations_v2.json) and scores whether the
model populates the new v2 fields correctly. This is the plan's "do not land
prompt changes blind" gate (section 6).

DESIGN: the eval isolates PROMPT quality from RETRIEVAL quality. Context per
register is assembled deterministically from the chunked markdown -- pages
mentioning the register (constraint_validator.quote_anchor.RMMatcher's
mention heuristic), the register's own section first, capped at ~8k chars --
with none of the pipeline's retrieval infrastructure. A scoring miss is
therefore a prompt/model failure, never a retrieval miss.

Per register it scores:
  - parse: the response yields a JSON object whose access_constraints_v2
    entries validate against defs.ConstraintV2 (one repair retry);
  - kinds: required_kinds all emitted ("full"; "extra" when genuine-looking
    additional kinds appear beyond allowed_kinds; "partial" when only an
    allowed alternative was emitted; "fail" otherwise);
  - established_by: expected value per named condition (suffix-insensitive
    register matching);
  - zero-emission compliance for the negative cases;
  - quote anchoring: every emitted datasheet_text located in the manual
    (exact/fuzzy, RMMatcher machinery).

It then writes each register's output as a run-dir-style JSON (the native-v2
wire format: access_constraints [] + access_constraints_v2 + schema_version 2)
and runs applications/pac_codegen/collect_constraints.py over it per RM
(native-v2 path, with that RM's alphabetically-first SVD when available),
reporting the manifest counts.

Outputs land under optimization/test_outputs/extraction_eval_v2/<run-name>/
(git-ignored): raw model responses, assembled contexts, run_dirs/, collected/,
results.json. The committed report is docs/extraction_eval_v2.md.

Usage:
    .venv/bin/python optimization/generator/extraction_eval_v2.py \
        [--run-name 2026-07-17] [--cases rm0008_i2c1_cr1,...] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from pydantic import TypeAdapter  # noqa: E402

from defs import ConstraintV2  # noqa: E402
from prompts.register_info_stm import (  # noqa: E402
    create_register_constraints_v2_system_prompt,
    create_register_info_stm_user_prompt,
)
from constraint_validator.judge import (  # noqa: E402
    MODEL,
    _call_with_backoff,
    extract_json_block,
    make_client,
)
from constraint_validator.quote_anchor import (  # noqa: E402
    FUZZY_THRESHOLD,
    RMMatcher,
    normalize_text,
)
from applications.pac_codegen.collect_constraints import (  # noqa: E402
    collect_constraints,
)

CONSTRAINT_V2_ADAPTER = TypeAdapter(ConstraintV2)

DEFAULT_CHUNKS = "/home/ramla/hal_agent-phase-1d/chunked_datasheets/stm"
DEFAULT_SVD_ROOT = "/home/ramla/hal_agent-phase-1d/devices/stm"
DEFAULT_EXPECTATIONS = Path(__file__).parent / "eval_expectations_v2.json"
DEFAULT_OUT_ROOT = _REPO_ROOT / "optimization" / "test_outputs" / "extraction_eval_v2"

# ~8-12k chars (~3k tokens): the register's section plus 2-4 related pages.
# Started at ~8k per the plan; raised after the dry run showed the RTC_WPR
# unlock-procedure page falling just outside the budget for rm0383/rtc_dr
# (documented in docs/extraction_eval_v2.md).
CONTEXT_CAP = 12000

REPAIR_PROMPT = (
    "Your previous reply did not contain a single valid JSON object with an "
    '"access_constraints_v2" list. Respond again with ONLY the JSON object: '
    '{"register_name": ..., "schema_version": 2, '
    '"access_constraints_v2": [...]}'
)


# ---------------------------------------------------------------------------
# Context assembly (deterministic; no pipeline retrieval)
# ---------------------------------------------------------------------------


def _is_front_matter(matcher: RMMatcher, page: int) -> bool:
    """Contents/index/revision-history pages mention every register (and even
    quote section headers verbatim); exclude them."""
    head = matcher.page_orig[page][:120]
    return any(marker in head for marker in
               ("Contents", "Index", "List of tables", "List of figures",
                "Revision history", "Glossary"))


def assemble_context(matcher: RMMatcher, peripheral: str, register: str,
                     cap: int = CONTEXT_CAP) -> tuple[str, list[int]]:
    """Pages mentioning the register, the register's own section first.

    Ranking: full-name mentions (i2c1_cr1 / i2c_cr1 / i2cx_cr1) beat bare
    register tokens; the SECTION page -- the one carrying the STM register
    section header, "... register (REG_NAME)" -- leads, followed by its
    continuation page, then the remaining mentioning pages in page order,
    until the character cap.
    """
    full, bare = [], []
    for p in matcher.pages:
        if _is_front_matter(matcher, p):
            continue
        score = matcher.mention_score((p,), peripheral, register)
        if score == 2:
            full.append(p)
        elif score == 1:
            bare.append(p)
    candidates = full if full else bare
    if not candidates:
        return "", []

    # The register-description section header spells the name in parentheses:
    # "Control/status register (RCC_CSR)". Cross-references in other chapters
    # use the same parenthesized form, so require the register-layout marker
    # "reset value" on the page and break ties by the EARLIEST header position
    # (a section header sits at the top of its page; a cross-reference sits
    # mid-prose); then relax tier by tier.
    per = normalize_text(peripheral)
    reg = normalize_text(register)
    base = per.rstrip("0123456789")
    header_pats = {f"({per}_{reg})", f"({base}_{reg})", f"({base}x_{reg})"}

    def _pat_pos(norm: str):
        positions = [norm.find(pat) for pat in header_pats]
        positions = [pos for pos in positions if pos != -1]
        return min(positions) if positions else None

    def _tier(pred):
        matches = [(pos, p) for p in candidates
                   if (pos := pred(matcher.page_norm[p])) is not None]
        return min(matches)[1] if matches else None

    section = _tier(lambda n: _pat_pos(n) if "reset value" in n else None)
    if section is None:
        section = _tier(_pat_pos)
    if section is None:
        section = _tier(lambda n: 0 if "reset value" in n else None)
    if section is None:
        section = candidates[0]

    # Section first; its continuation pages (page+1 always, further pages
    # while they still mention the register -- long sections span several
    # pages); then the other mentioning pages in page order; last, the page
    # BEFORE the section (often the "XXX registers" intro carrying
    # section-wide notes such as access-width rules).
    ordered = [section]
    nxt = section + 1
    while nxt in matcher.page_orig and not _is_front_matter(matcher, nxt):
        ordered.append(nxt)
        nxt += 1
        if nxt not in candidates:
            break
    ordered.extend(p for p in candidates if p not in ordered)
    prev = section - 1
    if prev in matcher.page_orig and prev not in ordered \
            and not _is_front_matter(matcher, prev):
        ordered.append(prev)

    parts, used, total = [], [], 0
    for p in ordered:
        text = matcher.page_orig[p]
        piece = f"--- page {p} ---\n{text}\n"
        if used and total + len(piece) > cap:
            break
        parts.append(piece)
        used.append(p)
        total += len(piece)
        if total >= cap:
            break
    return "".join(parts)[: cap + 200], used


# ---------------------------------------------------------------------------
# Model call (Groq gpt-oss-120b; free-form JSON + one repair retry --
# NO json_schema mode, per the tiered schema-enforcement decision)
# ---------------------------------------------------------------------------


def run_case_model(client, system_prompt: str, case: dict, context: str,
                   model: str = MODEL) -> dict:
    user = create_register_info_stm_user_prompt(
        case["register_name"], case["peripheral_name"], context)
    base = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]
    ptok = ctok = calls = 0
    raw_responses = []
    messages = base
    obj = None
    for attempt in (0, 1):
        content, pt, ct = _call_with_backoff(client, model, messages)
        calls += 1
        ptok += pt
        ctok += ct
        raw_responses.append(content)
        obj = extract_json_block(content)
        if isinstance(obj, dict) and isinstance(
                obj.get("access_constraints_v2"), list):
            break
        obj = None
        messages = base + [
            {"role": "assistant", "content": content},
            {"role": "user", "content": REPAIR_PROMPT},
        ]
    return {
        "object": obj,
        "raw_responses": raw_responses,
        "usage": {"prompt_tokens": ptok, "completion_tokens": ctok,
                  "calls": calls},
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _reg_suffix(name: str) -> str:
    """Peripheral-prefix-insensitive register comparison key: the part after
    the first underscore when present (SPI_SR / SPI1_SR -> 'sr')."""
    n = (name or "").strip().lower()
    return n.split("_", 1)[1] if "_" in n else n


def _iter_conditions(constraint):
    if constraint.kind == "state_gate":
        yield from constraint.preconditions
        yield from constraint.postconditions
    elif constraint.kind == "clock_gate":
        yield constraint.clock


def score_established_by(expected: dict, constraints: list) -> dict:
    """expected: {"REG.FIELD" | "REG": "hardware"|"software"} -> per-key
    status "correct" / "wrong" / "missing"."""
    out = {}
    for key, want in expected.items():
        reg, _, field = key.partition(".")
        found = None
        for c in constraints:
            for cond in _iter_conditions(c):
                if _reg_suffix(cond.register) != _reg_suffix(reg):
                    continue
                if field:
                    if cond.whole_register or cond.field.lower() != field.lower():
                        continue
                elif not cond.whole_register:
                    continue
                found = cond
                break
            if found:
                break
        if found is None:
            out[key] = "missing"
        elif found.established_by == want:
            out[key] = "correct"
        else:
            out[key] = f"wrong ({found.established_by})"
    return out


def score_kinds(case: dict, emitted_kinds: set) -> str:
    required = set(case["required_kinds"])
    allowed = required | set(case["allowed_kinds"])
    if case["expect_zero"]:
        return "full" if not emitted_kinds else "fail"
    if not emitted_kinds:
        return "fail"
    if required <= emitted_kinds:
        return "full" if emitted_kinds <= allowed else "extra"
    if emitted_kinds & allowed:
        return "partial"
    return "fail"


def anchor_tier(matcher: RMMatcher, quote: str) -> str:
    nq = normalize_text(quote or "")
    if not nq:
        return "unanchored"
    if matcher.exact_hits(nq):
        return "exact"
    ratio, key, _, _ = matcher.fuzzy_best(nq)
    if key is not None and ratio >= FUZZY_THRESHOLD:
        return "fuzzy"
    return "unanchored"


def score_case(case: dict, model_result: dict, matcher: RMMatcher) -> dict:
    obj = model_result["object"]
    raw_constraints = (obj or {}).get("access_constraints_v2") or []
    valid, invalid = [], []
    for entry in raw_constraints:
        try:
            valid.append(CONSTRAINT_V2_ADAPTER.validate_python(entry))
        except Exception as e:  # pydantic ValidationError
            invalid.append(str(e).splitlines()[0][:160])

    emitted_kinds = {c.kind for c in valid}
    anchors = {"exact": 0, "fuzzy": 0, "unanchored": 0}
    for c in valid:
        anchors[anchor_tier(matcher, c.datasheet_text)] += 1

    parse_ok = obj is not None and not invalid
    return {
        "id": case["id"],
        "parse_ok": parse_ok,
        "emitted": len(raw_constraints),
        "valid": len(valid),
        "invalid": len(invalid),
        "invalid_errors": invalid,
        "kinds_emitted": sorted(emitted_kinds),
        "kind_match": score_kinds(case, emitted_kinds),
        "established_by": score_established_by(
            case["expected_established_by"], valid),
        "expect_zero": case["expect_zero"],
        "zero_ok": (len(raw_constraints) == 0) if case["expect_zero"] else None,
        "anchors": anchors,
        "wire_format_ok": bool(obj) and obj.get("schema_version") == 2
        and "access_constraints" not in obj,
        "usage": model_result["usage"],
    }


# ---------------------------------------------------------------------------
# Run-dir writing + collection (native-v2 path, end to end)
# ---------------------------------------------------------------------------


def write_run_dir_file(run_dir: Path, case: dict, model_result: dict) -> Path:
    """Run-dir-style native-v2 RegisterInfo JSON: ALL raw emitted constraints
    (including malformed ones -- collection's per-constraint recovery must
    handle them), layout fields stubbed (this eval extracts constraints only).
    """
    obj = model_result["object"] or {}
    data = {
        "datasheet_register_abbreviation": case["register_name"],
        "address_offset": "",
        "reset_value": "",
        "size": 32,
        "subfields": [],
        "access_constraints_v2": obj.get("access_constraints_v2") or [],
        "schema_version": 2,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / case["file"]
    out.write_text(json.dumps(data, indent=2))
    return out


def first_svd(svd_root: Path, rm: str):
    svd_dir = svd_root / rm / "svd"
    if not svd_dir.is_dir():
        return None
    svds = sorted(svd_dir.glob("*.svd"))
    return str(svds[0]) if svds else None


def run_collection(out_root: Path, rms: list[str], svd_root: Path) -> dict:
    summaries = {}
    for rm in sorted(rms):
        run_dir = out_root / "run_dirs" / rm
        collected = out_root / "collected" / rm
        svd = first_svd(svd_root, rm)
        collect_constraints(str(run_dir), output_dir=str(collected),
                            svd_dir=svd, include_empty=True)
        manifest = json.loads((collected / "manifest.json").read_text())
        summaries[rm] = {
            "svd": svd,
            "summary": manifest["summary"],
            "registers": [
                {k: r[k] for k in ("file", "constraint_source",
                                   "num_source_constraints",
                                   "num_constraints_v2", "lint_flags")}
                for r in manifest["registers"]
            ],
        }
    return summaries


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def aggregate(scores: list[dict]) -> dict:
    positives = [s for s in scores if not s["expect_zero"]]
    negatives = [s for s in scores if s["expect_zero"]]
    eb_statuses = [v for s in scores for v in s["established_by"].values()]
    total_valid = sum(s["valid"] for s in scores)
    anchored = sum(s["anchors"]["exact"] + s["anchors"]["fuzzy"] for s in scores)
    return {
        "cases": len(scores),
        "parse_rate": sum(s["parse_ok"] for s in scores) / len(scores),
        "constraints_emitted": sum(s["emitted"] for s in scores),
        "constraints_valid": total_valid,
        "kind_full": sum(s["kind_match"] == "full" for s in positives),
        "kind_extra": sum(s["kind_match"] == "extra" for s in positives),
        "kind_partial": sum(s["kind_match"] == "partial" for s in positives),
        "kind_fail": sum(s["kind_match"] == "fail" for s in positives),
        "kind_accuracy": (sum(s["kind_match"] in ("full", "extra")
                              for s in positives) / len(positives))
        if positives else None,
        "established_by_expected": len(eb_statuses),
        "established_by_correct": sum(v == "correct" for v in eb_statuses),
        "established_by_accuracy": (sum(v == "correct" for v in eb_statuses)
                                    / len(eb_statuses)) if eb_statuses else None,
        "negative_compliance": (sum(bool(s["zero_ok"]) for s in negatives)
                                / len(negatives)) if negatives else None,
        "quote_anchor_rate": (anchored / total_valid) if total_valid else None,
        "wire_format_ok": sum(bool(s["wire_format_ok"]) for s in scores),
        "prompt_tokens": sum(s["usage"]["prompt_tokens"] for s in scores),
        "completion_tokens": sum(s["usage"]["completion_tokens"] for s in scores),
        "calls": sum(s["usage"]["calls"] for s in scores),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--expectations", default=str(DEFAULT_EXPECTATIONS))
    ap.add_argument("--chunks", default=DEFAULT_CHUNKS)
    ap.add_argument("--svd-root", default=DEFAULT_SVD_ROOT)
    ap.add_argument("--out-root", default=None,
                    help="output directory (default: "
                         "optimization/test_outputs/extraction_eval_v2/<run-name>)")
    ap.add_argument("--run-name", default=time.strftime("%Y-%m-%d"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--cases", default=None,
                    help="comma-separated case ids (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble and save contexts only; no API calls")
    args = ap.parse_args(argv)

    spec = json.loads(Path(args.expectations).read_text())
    cases = spec["cases"]
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    out_root = Path(args.out_root) if args.out_root else (
        DEFAULT_OUT_ROOT / args.run_name)
    (out_root / "raw").mkdir(parents=True, exist_ok=True)
    (out_root / "contexts").mkdir(parents=True, exist_ok=True)

    system_prompt = create_register_constraints_v2_system_prompt()
    (out_root / "system_prompt.txt").write_text(system_prompt)

    matchers: dict[str, RMMatcher] = {}
    client = None if args.dry_run else make_client()

    t0 = time.monotonic()
    scores = []
    for case in cases:
        rm = case["rm"]
        if rm not in matchers:
            matchers[rm] = RMMatcher(rm, str(Path(args.chunks) / rm / "chunks" / "md"))
        matcher = matchers[rm]
        context, pages = assemble_context(matcher, case["peripheral"],
                                          case["register"])
        (out_root / "contexts" / f"{case['id']}.md").write_text(
            f"pages: {pages}\n\n{context}")
        print(f"[{case['id']}] context pages {pages} ({len(context)} chars)",
              file=sys.stderr)
        if args.dry_run:
            continue

        model_result = run_case_model(client, system_prompt, case, context,
                                      model=args.model)
        (out_root / "raw" / f"{case['id']}.txt").write_text(
            "\n\n=== RETRY ===\n\n".join(model_result["raw_responses"]))
        write_run_dir_file(out_root / "run_dirs" / rm, case, model_result)
        score = score_case(case, model_result, matcher)
        scores.append(score)
        print(f"[{case['id']}] kinds={score['kinds_emitted']} "
              f"match={score['kind_match']} eb={score['established_by']} "
              f"anchors={score['anchors']}", file=sys.stderr)

    if args.dry_run:
        print(f"dry run complete -> {out_root}/contexts", file=sys.stderr)
        return 0

    collection = run_collection(out_root, sorted({c["rm"] for c in cases}),
                                Path(args.svd_root))

    elapsed = round(time.monotonic() - t0, 1)
    results = {
        "run_name": args.run_name,
        "model": args.model,
        "elapsed_s": elapsed,
        "aggregate": aggregate(scores),
        "scores": scores,
        "collection": collection,
    }
    (out_root / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results["aggregate"], indent=2))
    print(f"-> {out_root}/results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
