#!/usr/bin/env python3
"""Parse `cargo build` stderr into the witness-gate firing list.

A whole-register gate fires as E0277 ("`<SPEC>` is write/modify/read-constrained
by its datasheet") at the offending call site; a field-level advisory fires as
E0061 (the patched field accessor now takes a witness arg). Prints one line per
firing: KIND  REG op  file:line. Usage: parse_firings.py <cargo-stderr-file>
"""
import re
import sys

text = open(sys.argv[1]).read().splitlines()
fires, i = [], 0
while i < len(text):
    l = text[i]
    m = re.match(r'error\[E0277\]: `(\w+)` is (write|modify|read)-constrained', l)
    if m:
        reg, op = m.group(1), m.group(2)
        loc = next((re.search(r'--> (\S+:\d+)', text[j]).group(1)
                    for j in range(i + 1, min(i + 6, len(text)))
                    if re.search(r'--> \S+:\d+', text[j])), "?")
        fires.append(("E0277", f"{reg} {op}", loc))
    elif re.match(r'error\[E0061\]:', l):
        loc = next((re.search(r'--> (\S+:\d+)', text[j]).group(1)
                    for j in range(i + 1, min(i + 8, len(text)))
                    if re.search(r'--> \S+:\d+', text[j])), "?")
        fires.append(("E0061-field", "", loc))
    i += 1

n277 = sum(1 for k, *_ in fires if k == "E0277")
n061 = sum(1 for k, *_ in fires if k == "E0061-field")
print(f"firings: {n277} whole-register (E0277), {n061} field-advisory (E0061)")
for k, what, loc in fires:
    print(f"  {k:12} {what:24} {loc}")
