#!/usr/bin/env python3
"""Deterministic quote anchoring for the Constraint Validator (plan §7.1).

Every extracted constraint carries its own cited evidence (``datasheet_text``).
This module verifies that evidence *deterministically* against the chunked
markdown conversion of the reference manual — no LLM, no semantic retrieval:

  1. ``exact``      — the normalized quote is a substring of a page (or an
                      adjacent-page join, for quotes spanning a page break).
  2. ``fuzzy``      — best difflib.SequenceMatcher ratio >= FUZZY_THRESHOLD
                      over candidate windows (pages shortlisted via a token
                      5-gram index).
  3. ``unanchored`` — neither; the constraint cannot be grounded.

For anchored rows the judge's future input ("context") is DERIVED from the
source: the match is located in the ORIGINAL (un-normalized) page text and
expanded to the enclosing paragraph plus one paragraph before and after
(capped at CONTEXT_CAP chars). Context is never generated.

Repeated boilerplate quotes are disambiguated by preferring the matched page
that mentions the row's own register name; ``ambiguous`` is flagged when >1
page matches and none / more than one mention it.

Determinism: same inputs produce a byte-identical JSONL (rows in CSV order,
sorted JSON keys, ASCII-escaped strings, fixed 4-decimal ratios).

CLI:
    python3 constraint_validator/quote_anchor.py \
        --csv verified_datasheet/constraints/stm.csv \
        --chunks /home/ramla/hal_agent-phase-1d/chunked_datasheets/stm \
        --out constraint_validator/out/anchors.jsonl [--rm rm0008]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from bisect import bisect_right
from collections import Counter, defaultdict
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Tunables (all deterministic)
# ---------------------------------------------------------------------------

FUZZY_THRESHOLD = 0.85     # SequenceMatcher ratio for the "fuzzy" tier
NGRAM = 5                  # token n-gram size for the fuzzy page shortlist
MAX_CANDIDATE_PAGES = 8    # pages shortlisted per fuzzy lookup
COMMON_TOKEN_DF = 50       # short-quote fallback: ignore tokens on > this many pages
CONTEXT_CAP = 2000         # max chars of derived context
MIN_CHUNK_OVERLAP = 20     # min suffix/prefix overlap to merge same-page chunks
OVERLAP_PROBE = 20         # probe length used to find the chunk overlap
                           # (must be <= MIN_CHUNK_OVERLAP so no genuine
                           # overlap is shorter than the probe)

CHUNK_FILE_RE = re.compile(r"^(?P<rm>rm\w+)_p(?P<page>\d+)_c(?P<chunk>\d+)\.txt$")

# ---------------------------------------------------------------------------
# Normalization
#
# Two implementations with identical semantics:
#   * normalize_text()          — vectorized (regex + str.translate); used to
#                                 normalize ~300 MB of page text quickly.
#   * normalize_with_offsets()  — char-by-char, additionally returns a map
#                                 norm-index -> original-index; used only on
#                                 the single matched page/pair so the context
#                                 can be extracted from the ORIGINAL text.
# Both share the same per-char predicate helpers so they cannot drift apart
# silently; a mismatch is additionally caught at context-extraction time and
# handled by re-locating the match.
# ---------------------------------------------------------------------------

# Raw single-char replacements applied before and after NFKC.
# '' means "delete". Markdown emphasis chars '*' and '`' are deleted; table
# pipes become whitespace so quotes drawn from table cells can still match.
_CHAR_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",   # curly single quotes
    "“": '"', "”": '"', "„": '"',                  # curly double quotes
    "‐": "-", "‑": "-", "‒": "-", "–": "-",   # hyphens/dashes
    "—": "-", "―": "-", "−": "-",                  # em dash, minus
    "­": "",                                                 # soft hyphen
    "​": "", "‌": "", "‍": "", "﻿": "",       # zero-width
    "*": "", "`": "",                                             # markdown emphasis/code
    "|": " ",                                                     # markdown table pipe
}

_ALNUM_RE = re.compile(r"[^\W_]", re.UNICODE)   # unicode alphanumeric (no '_')
_WS_RE = re.compile(r"\s", re.UNICODE)
_WS_RUN_RE = re.compile(r"\s+", re.UNICODE)
# leading run of blanks/hashes on a line (markdown heading markers)
_HASH_RUN_RE = re.compile(r"(?m)^[ \t#]+")
# '_' not flanked by alphanumerics on BOTH sides (markdown italics),
# i.e. intra-word underscores such as ADC_CR1 are preserved.
_UNDERSCORE_RE = re.compile(r"(?<![^\W_])_|_(?![^\W_])", re.UNICODE)

_PROC_CACHE: dict = {}


def _process_char(ch: str) -> str:
    """Map one raw char to its normalized string (may be '' or multi-char)."""
    cached = _PROC_CACHE.get(ch)
    if cached is not None:
        return cached
    mapped = _CHAR_MAP.get(ch, ch)
    out = []
    for base in mapped:
        seq = base if ord(base) < 128 else unicodedata.normalize("NFKC", base)
        for c in seq:
            c = _CHAR_MAP.get(c, c)
            if c:
                out.append(c.lower())
    result = "".join(out)
    _PROC_CACHE[ch] = result
    return result


def normalize_text(text: str) -> str:
    """Vectorized normalization (no offset map)."""
    s = _HASH_RUN_RE.sub(lambda m: m.group(0).replace("#", ""), text)
    s = _UNDERSCORE_RE.sub("", s)
    table = {ord(c): _process_char(c) for c in set(s)}
    s = s.translate(table)
    return _WS_RUN_RE.sub(" ", s).strip()


def normalize_with_offsets(text: str):
    """Char-by-char normalization returning (norm, offsets).

    offsets[i] is the index in ``text`` of the raw char that produced norm
    char i, allowing matches in normalized space to be mapped back to the
    original text.
    """
    out: list = []
    offs: list = []
    prev_space = True          # collapses leading whitespace too
    line_leading = True        # only blanks/'#' seen so far on this line
    n = len(text)
    for j, ch in enumerate(text):
        if ch == "#":
            if line_leading:
                continue       # markdown heading marker: drop, run continues
        elif ch == "\n":
            line_leading = True
        elif ch not in " \t":
            line_leading = False
        if ch == "_":
            left_ok = j > 0 and _ALNUM_RE.match(text[j - 1])
            right_ok = j + 1 < n and _ALNUM_RE.match(text[j + 1])
            if not (left_ok and right_ok):
                continue       # markdown italics: drop boundary underscore
        for c in _process_char(ch):
            if _WS_RE.match(c):
                if prev_space:
                    continue
                out.append(" ")
                offs.append(j)
                prev_space = True
            else:
                out.append(c)
                offs.append(j)
                prev_space = False
    while out and out[-1] == " ":
        out.pop()
        offs.pop()
    return "".join(out), offs


# ---------------------------------------------------------------------------
# Page assembly from chunk files
# ---------------------------------------------------------------------------

def _merge_overlap(a: str, b: str) -> str:
    """Concatenate chunk texts, deduplicating the chunker's overlap window.

    Consecutive same-page chunks share a few hundred chars (b starts with a
    suffix of a). Find the largest prefix of b that is a suffix of a via a
    probe search; require MIN_CHUNK_OVERLAP so a spurious 1-char match never
    silently drops text.
    """
    probe_len = min(OVERLAP_PROBE, len(a), len(b))
    if probe_len >= MIN_CHUNK_OVERLAP:
        tail = a[-probe_len:]
        best_k = 0
        idx = b.find(tail)
        while idx != -1:
            k = idx + probe_len
            if k >= MIN_CHUNK_OVERLAP and a.endswith(b[:k]):
                best_k = max(best_k, k)
            idx = b.find(tail, idx + 1)
        if best_k:
            return a + b[best_k:]
    return a + "\n" + b


def load_pages(md_dir: str, rm: str) -> dict:
    """Read chunk files for one RM and merge them into per-page texts."""
    by_page: dict = defaultdict(list)
    for fname in os.listdir(md_dir):
        m = CHUNK_FILE_RE.match(fname)
        if not m or m.group("rm") != rm:
            continue
        by_page[int(m.group("page"))].append(
            (int(m.group("chunk")), os.path.join(md_dir, fname))
        )
    pages: dict = {}
    for page, entries in by_page.items():
        merged = None
        for _, path in sorted(entries):
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            merged = text if merged is None else _merge_overlap(merged, text)
        pages[page] = merged
    return pages


# ---------------------------------------------------------------------------
# Context derivation (original text, paragraph-expanded)
# ---------------------------------------------------------------------------

_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n(?:[ \t]*\n)*")


def paragraph_context(orig: str, m_start: int, m_end: int, cap: int = CONTEXT_CAP) -> str:
    """Slice of ``orig``: the paragraph(s) containing [m_start, m_end) plus
    one paragraph before and one after, capped at ``cap`` chars around the
    match. Paragraph = blank-line-separated block."""
    bounds = []
    pos = 0
    for sep in _BLANK_LINE_RE.finditer(orig):
        if sep.start() > pos:
            bounds.append((pos, sep.start()))
        pos = sep.end()
    if pos < len(orig):
        bounds.append((pos, len(orig)))
    if not bounds:
        bounds = [(0, len(orig))]

    def para_index(off: int) -> int:
        for i, (s, e) in enumerate(bounds):
            if off < e:
                return i
        return len(bounds) - 1

    i0 = para_index(m_start)
    i1 = para_index(max(m_start, m_end - 1))
    lo = max(0, i0 - 1)
    hi = min(len(bounds) - 1, i1 + 1)
    cs, ce = bounds[lo][0], bounds[hi][1]
    if ce - cs > cap:
        span = m_end - m_start
        if span >= cap:
            cs2, ce2 = m_start, m_start + cap
        else:
            pad = (cap - span) // 2
            cs2 = max(cs, m_start - pad)
            ce2 = cs2 + cap
            if ce2 > ce:
                ce2 = ce
                cs2 = ce2 - cap
        cs, ce = max(cs, cs2), min(ce, ce2)
    return orig[cs:ce]


# ---------------------------------------------------------------------------
# Per-RM matcher
# ---------------------------------------------------------------------------

class RMMatcher:
    """Holds one reference manual's pages (original + normalized), the
    single/pair concatenations for exact search, and a lazily built token
    5-gram index for the fuzzy shortlist."""

    def __init__(self, rm: str, md_dir: str):
        self.rm = rm
        self.page_orig = load_pages(md_dir, rm)
        self.pages = sorted(self.page_orig)
        self.page_norm = {p: normalize_text(self.page_orig[p]) for p in self.pages}

        # Exact search over single pages: one big string with NUL separators
        # (NUL never occurs in text, so matches cannot cross pages).
        self.single_keys = [(p,) for p in self.pages if self.page_norm[p]]
        self._single_concat, self._single_starts = self._concat(
            [self.page_norm[k[0]] for k in self.single_keys]
        )

        # Adjacent-page joins, for quotes spanning a page break.
        self.pair_keys = []
        pair_texts = []
        for a, b in zip(self.pages, self.pages[1:]):
            na, nb = self.page_norm[a], self.page_norm[b]
            if na and nb:
                self.pair_keys.append((a, b))
                pair_texts.append(na + " " + nb)
        self._pair_concat, self._pair_starts = self._concat(pair_texts)

        self._gram_index = None
        self._token_index = None
        self.context_warnings = 0

    @staticmethod
    def _concat(texts):
        starts, parts, pos = [], [], 0
        for t in texts:
            starts.append(pos)
            parts.append(t)
            pos += len(t) + 1
        return "\x00".join(parts), starts

    # -- unit accessors ----------------------------------------------------

    def unit_norm(self, key) -> str:
        if len(key) == 1:
            return self.page_norm[key[0]]
        na, nb = self.page_norm[key[0]], self.page_norm[key[1]]
        return na + " " + nb if na and nb else (na or nb)

    def unit_orig(self, key) -> str:
        if len(key) == 1:
            return self.page_orig[key[0]]
        return self.page_orig[key[0]] + "\n" + self.page_orig[key[1]]

    # -- exact tier ----------------------------------------------------------

    @staticmethod
    def _find_hits(concat, starts, keys, needle):
        hits: dict = {}
        i = concat.find(needle)
        while i != -1:
            u = bisect_right(starts, i) - 1
            hits[keys[u]] = hits.get(keys[u], 0) + 1
            i = concat.find(needle, i + 1)
        return hits

    def exact_hits(self, nq: str):
        """Return (unit->count) for single pages, falling back to page pairs."""
        hits = self._find_hits(self._single_concat, self._single_starts,
                               self.single_keys, nq)
        if hits:
            return hits
        return self._find_hits(self._pair_concat, self._pair_starts,
                               self.pair_keys, nq)

    # -- register-mention heuristic -----------------------------------------

    def mention_score(self, key, peripheral: str, register: str) -> int:
        """2: page names the register fully (adc1_cr1 / adc_cr1 / adcx_cr1);
        1: bare register token; 0: no mention."""
        norm = self.unit_norm(key)
        per = normalize_text(peripheral)
        reg = normalize_text(register)
        if not reg:
            return 0
        base = per.rstrip("0123456789")
        full = {f"{per}_{reg}"}
        if base:
            full.add(f"{base}_{reg}")
            full.add(f"{base}x_{reg}")
        for pat in sorted(full):
            if pat and pat in norm:
                return 2
        bare = re.compile(r"(?<![a-z0-9_])" + re.escape(reg) + r"(?![a-z0-9_])")
        return 1 if bare.search(norm) else 0

    # -- fuzzy tier ----------------------------------------------------------

    def _build_indexes(self):
        gram_index: dict = defaultdict(list)
        token_index: dict = defaultdict(list)
        for p in self.pages:
            toks = self.page_norm[p].split(" ")
            seen = set()
            for i in range(len(toks) - NGRAM + 1):
                g = tuple(toks[i:i + NGRAM])
                if g not in seen:
                    seen.add(g)
                    gram_index[g].append(p)
            for t in set(toks):
                token_index[t].append(p)
        self._gram_index = gram_index
        self._token_index = token_index

    def _shortlist(self, nq: str):
        if self._gram_index is None:
            self._build_indexes()
        toks = nq.split(" ")
        scores: Counter = Counter()
        if len(toks) >= NGRAM:
            seen = set()
            for i in range(len(toks) - NGRAM + 1):
                g = tuple(toks[i:i + NGRAM])
                if g in seen:
                    continue
                seen.add(g)
                for p in self._gram_index.get(g, ()):
                    scores[p] += 1
        else:
            for t in set(toks):
                pages = self._token_index.get(t, ())
                if 0 < len(pages) <= COMMON_TOKEN_DF:
                    for p in pages:
                        scores[p] += 1
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return [p for p, _ in ranked[:MAX_CANDIDATE_PAGES]]

    def _scan_windows(self, sm, text, lengths, best, key, start_lo=None, start_hi=None):
        """Slide windows over ``text``; update best=(ratio, key, start, wlen)."""
        for wlen in lengths:
            if wlen <= 0:
                continue
            if len(text) <= wlen:
                starts = [0]
                wlen_eff = len(text)
            else:
                step = max(1, wlen // 5)
                lo = 0 if start_lo is None else max(0, start_lo)
                hi = (len(text) - wlen) if start_hi is None else min(len(text) - wlen, start_hi)
                starts = list(range(lo, hi + 1, step))
                wlen_eff = wlen
            for s in starts:
                sm.set_seq1(text[s:s + wlen_eff])
                if sm.real_quick_ratio() <= best[0] or sm.quick_ratio() <= best[0]:
                    continue
                r = sm.ratio()
                if r > best[0]:
                    best = (r, key, s, wlen_eff)
        return best

    def fuzzy_best(self, nq: str):
        """Best fuzzy window across shortlisted pages (+ boundary joins).

        Returns (ratio, key, norm_start, norm_len); key is None if no
        candidate pages exist."""
        shortlist = self._shortlist(nq)
        if not shortlist:
            return 0.0, None, 0, 0
        L = len(nq)
        lengths = [L, L + max(2, L // 5)]  # allow small insertions in the source
        sm = SequenceMatcher(autojunk=False)
        sm.set_seq2(nq)
        best = (0.0, None, 0, 0)
        page_set = set(self.pages)
        scanned = set()
        for p in shortlist:
            keys = [(p,)]
            if p + 1 in page_set:
                keys.append((p, p + 1))
            if p - 1 in page_set:
                keys.append((p - 1, p))
            for key in keys:
                if key in scanned:
                    continue
                scanned.add(key)
                text = self.unit_norm(key)
                if len(key) == 1:
                    best = self._scan_windows(sm, text, lengths, best, key)
                else:
                    # pure-single-page windows are covered above; only scan
                    # windows overlapping the page boundary
                    boundary = len(self.page_norm[key[0]])
                    best = self._scan_windows(
                        sm, text, lengths, best, key,
                        start_lo=boundary - (L + max(2, L // 5)),
                        start_hi=boundary,
                    )
        if best[1] is not None:
            # fine pass (step 1) around the coarse best
            r, key, s, wlen = best
            step = max(1, wlen // 5)
            text = self.unit_norm(key)
            best = self._scan_windows(
                sm, text, [wlen], best, key,
                start_lo=s - step, start_hi=s + step,
            )
        return best

    # -- context -------------------------------------------------------------

    def derive_context(self, key, norm_start: int, norm_len: int):
        """Extract original-text context for a match located in normalized
        space, by re-normalizing the unit with an offset map."""
        orig = self.unit_orig(key)
        norm2, offs = normalize_with_offsets(orig)
        unit_norm = self.unit_norm(key)
        if norm2 != unit_norm:
            # the two normalizers disagreed (should not happen) — re-locate
            self.context_warnings += 1
            sub = unit_norm[norm_start:norm_start + norm_len]
            pos = norm2.find(sub)
            if pos == -1:
                return None
            norm_start = pos
            norm_len = len(sub)
        if not offs or norm_len <= 0:
            return None
        end_idx = min(norm_start + norm_len, len(offs)) - 1
        if end_idx < 0 or norm_start >= len(offs):
            return None
        o_start = offs[norm_start]
        o_end = offs[end_idx] + 1
        return paragraph_context(orig, o_start, o_end)


# ---------------------------------------------------------------------------
# Row anchoring
# ---------------------------------------------------------------------------

def _ratio_fmt(r: float) -> float:
    return float(f"{r:.4f}")


def anchor_row(matcher: RMMatcher, row: dict) -> dict:
    quote = row.get("datasheet_text", "") or ""
    nq = normalize_text(quote)
    rec = {
        "id": row.get("id", ""),
        "reference_manual": matcher.rm,
        "quote_len": len(quote),
        "ambiguous": False,
        "occurrences": 0,
        "pages": [],
    }
    if not nq:
        rec.update(tier="unanchored", ratio=0.0)
        return rec

    hits = matcher.exact_hits(nq)
    if hits:
        units = sorted(hits)
        rec["occurrences"] = sum(hits.values())
        rec["pages"] = sorted({p for u in units for p in u})
        rec["ratio"] = 1.0
        rec["tier"] = "exact"
        if len(units) > 1:
            per = row.get("peripheral", "") or ""
            reg = row.get("register", "") or ""
            scores = {u: matcher.mention_score(u, per, reg) for u in units}
            mentioning = [u for u in units if scores[u] > 0]
            rec["ambiguous"] = len(mentioning) != 1
            chosen = sorted(units, key=lambda u: (-scores[u], u))[0]
        else:
            chosen = units[0]
        pos = matcher.unit_norm(chosen).find(nq)
        ctx = matcher.derive_context(chosen, pos, len(nq))
        if ctx is not None:
            rec["context"] = ctx
        return rec

    ratio, key, s, wlen = matcher.fuzzy_best(nq)
    rec["ratio"] = _ratio_fmt(ratio)
    if key is not None:
        rec["pages"] = list(key)
    if key is not None and ratio >= FUZZY_THRESHOLD:
        rec["tier"] = "fuzzy"
        ctx = matcher.derive_context(key, s, wlen)
        if ctx is not None:
            rec["context"] = ctx
    else:
        rec["tier"] = "unanchored"
    return rec


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(csv_path: str, chunks_root: str, out_path: str, rm_filter=None,
        quiet: bool = False) -> dict:
    """Anchor every CSV row against its RM's chunked markdown.

    Writes a JSONL (one object per attempted row, CSV order, deterministic
    bytes) and returns a summary dict."""
    t0 = time.monotonic()
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rm_filter:
        rows = [r for r in rows if r.get("reference_manual") == rm_filter]

    by_rm: dict = defaultdict(list)
    for i, row in enumerate(rows):
        by_rm[row.get("reference_manual", "")].append(i)

    rms_with_chunks, rms_without_chunks = [], []
    results: dict = {}
    per_rm: dict = {}
    context_warnings = 0
    for rm in sorted(by_rm):
        md_dir = os.path.join(chunks_root, rm, "chunks", "md")
        if not os.path.isdir(md_dir):
            rms_without_chunks.append(rm)
            continue
        rms_with_chunks.append(rm)
        matcher = RMMatcher(rm, md_dir)
        counts = Counter()
        ambiguous = 0
        for i in by_rm[rm]:
            rec = anchor_row(matcher, rows[i])
            results[i] = rec
            counts[rec["tier"]] += 1
            ambiguous += bool(rec["ambiguous"])
        context_warnings += matcher.context_warnings
        per_rm[rm] = {
            "rows": len(by_rm[rm]),
            "exact": counts["exact"],
            "fuzzy": counts["fuzzy"],
            "unanchored": counts["unanchored"],
            "ambiguous": ambiguous,
        }
        del matcher

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tiers = Counter()
    ambiguous_total = 0
    attempted = 0
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for i in sorted(results):
            rec = results[i]
            tiers[rec["tier"]] += 1
            ambiguous_total += bool(rec["ambiguous"])
            attempted += 1
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")

    summary = {
        "csv_rows": len(rows),
        "attempted": attempted,
        "skipped_no_chunks": len(rows) - attempted,
        "rms_with_chunks": rms_with_chunks,
        "rms_without_chunks": rms_without_chunks,
        "tiers": dict(tiers),
        "ambiguous": ambiguous_total,
        "per_rm": per_rm,
        "context_warnings": context_warnings,
        "elapsed_s": round(time.monotonic() - t0, 1),
        "out_path": out_path,
    }
    if not quiet:
        _print_summary(summary)
    return summary


def _print_summary(s: dict) -> None:
    total = s["attempted"] or 1
    print(f"rows in CSV:        {s['csv_rows']}")
    print(f"rows attempted:     {s['attempted']}"
          f"  (skipped, RM without chunks: {s['skipped_no_chunks']})")
    print(f"RMs with chunks:    {len(s['rms_with_chunks'])}"
          f"   without: {len(s['rms_without_chunks'])}"
          + (f" {s['rms_without_chunks']}" if s["rms_without_chunks"] else ""))
    for tier in ("exact", "fuzzy", "unanchored"):
        n = s["tiers"].get(tier, 0)
        print(f"  {tier:<11} {n:>5}  ({100.0 * n / total:.1f}%)")
    print(f"ambiguous (multi-page exact, unresolved): {s['ambiguous']}")
    if s["context_warnings"]:
        print(f"context re-locations (normalizer disagreement): {s['context_warnings']}")
    print(f"elapsed: {s['elapsed_s']}s -> {s['out_path']}")
    print()
    print(f"{'rm':<8} {'rows':>5} {'exact':>6} {'fuzzy':>6} {'unanch':>6} {'ambig':>6}")
    for rm in sorted(s["per_rm"]):
        r = s["per_rm"][rm]
        print(f"{rm:<8} {r['rows']:>5} {r['exact']:>6} {r['fuzzy']:>6}"
              f" {r['unanchored']:>6} {r['ambiguous']:>6}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", default="verified_datasheet/constraints/stm.csv",
                    help="verified-constraints CSV")
    ap.add_argument("--chunks",
                    default="/home/ramla/hal_agent-phase-1d/chunked_datasheets/stm",
                    help="root of chunked markdown ({rm}/chunks/md/*.txt)")
    ap.add_argument("--out", default="constraint_validator/out/anchors.jsonl",
                    help="output JSONL path")
    ap.add_argument("--rm", default=None,
                    help="restrict to one reference manual (e.g. rm0008)")
    args = ap.parse_args(argv)
    run(args.csv, args.chunks, args.out, rm_filter=args.rm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
