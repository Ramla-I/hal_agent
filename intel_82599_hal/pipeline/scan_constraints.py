#!/usr/bin/env python3
"""Constraint-recall scan: find datasheet ordering/state/sequence cues in the
75 target registers' detail sections and check which registers show a cue but
carry no extracted constraint — the candidate misses to adjudicate by hand.

Cue lexicon targets access/ordering language, deliberately broad (favouring
false positives, which hand-adjudication filters) — NOT the DO-NOT-EMIT
classes (w1c, read-to-clear, access width, privilege, plain reset).
"""
import json, os, re, sys
sys.path.insert(0, ".")
from enumerate_targets import parse_detail_headings, DATASHEET_MD

CUES = [
    r"must be set", r"must be cleared", r"must be (?:written|programmed)",
    r"should (?:be set|be cleared|only be|not be)", r"should be written",
    r"before (?:enabling|accessing|writing|setting|clearing|the)",
    r"after (?:a reset|reset|enabling|disabling|setting|clearing|the)",
    r"only (?:be )?(?:written|set|accessed|modified|changed|valid) (?:when|while|if|after)",
    r"only when", r"only while", r"only if", r"while .{0,30}(?:disabled|enabled|is set|is cleared|= 0b|=0b)",
    r"prior to", r"poll", r"wait (?:for|until)", r"until .{0,20}(?:is set|reads|= 1b)",
    r"self[- ]?clearing", r"semaphore", r"synchroniz", r"in parallel",
    r"must not (?:be )?(?:change|set|cleared|written)", r"do not (?:write|set|change)",
    r"must (?:first|be the same|equal|match)", r"sequence", r"step \d",
    r"restart", r"this register must be initialized", r"grant",
    r"owned by (?:software|firmware)", r"disable .{0,30}before", r"enabled before",
]
CUE_RE = re.compile("|".join(f"(?:{c})" for c in CUES), re.I)

# DO-NOT-EMIT suppressors: a cue sentence that is ONLY one of these is not a constraint
BENIGN = re.compile(r"reads? as 0|written to 0x0 for future|ignored on write|"
                    r"accessed as a 32-bit|privileged|reserved\b", re.I)


def reg_sections(regs_upper):
    lines = open(DATASHEET_MD).readlines()
    heads = parse_detail_headings()
    head_lines = sorted({h["line"] for h in heads.values()})
    out = {}
    for reg in regs_upper:
        h = heads.get(reg.lower()) or heads.get(reg.lower() + "n")
        if not h:
            out[reg] = None
            continue
        start = h["line"]
        nxt = [l for l in head_lines if l > start]
        end = nxt[0] if nxt else len(lines) + 1
        out[reg] = "".join(lines[start - 1:end - 1])
    return out


def cue_sentences(text):
    hits = []
    for raw in re.split(r"(?<=[.!])\s+|\n", text):
        s = raw.strip()
        if len(s) < 12 or s.startswith(("#", "|---")):
            continue
        if CUE_RE.search(s) and not (BENIGN.search(s) and len(CUE_RE.findall(s)) == 0):
            # drop pure table-separator / heading noise
            core = re.sub(r"^\|.*?\|", "", s)
            hits.append(s[:200])
    return hits


def main():
    regs = [r["abbrev_base"].upper()
            for r in json.load(open("targets/registers_join.json"))["registers"]]
    cons = json.load(open("constraints/r006_constraints.json"))
    # registers that are a target OR referenced by any accepted constraint
    covered = set()
    for a in cons["accepted"]:
        c = a["constraint"]
        covered.add(a["register"].upper())
        covered.add(str(c.get("target_register", "")).upper())
        for key in ("preconditions", "postconditions", "fields", "involved", "steps"):
            for o in (c.get(key) or []):
                if isinstance(o, dict) and o.get("register"):
                    covered.add(o["register"].upper())
    covered.discard("")

    secs = reg_sections(regs)
    flagged = {}
    for reg in regs:
        if secs[reg] is None:
            continue
        hits = cue_sentences(secs[reg])
        if hits and reg not in covered:
            flagged[reg] = hits
    print(f"registers with an extracted constraint (target or ref): {len(covered)}")
    print(f"registers with cue language BUT no constraint: {len(flagged)}\n")
    for reg, hits in flagged.items():
        print(f"### {reg}")
        for h in hits[:6]:
            print("   -", re.sub(r"\s+", " ", h))
        print()
    json.dump({"covered": sorted(covered), "candidate_misses": flagged},
              open("constraint_recall_scan.json", "w"), indent=2)


if __name__ == "__main__":
    main()
