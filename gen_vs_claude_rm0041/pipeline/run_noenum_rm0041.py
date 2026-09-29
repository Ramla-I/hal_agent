#!/usr/bin/env python3
"""COMPLETE RERUN (apples-to-apples with the Claude baseline):
evolved rm0041 retrieval + gpt-oss-120b generator over the FULL device, but with
`enumerated_values` DROPPED from the prompt (the Claude baseline was told to omit
enums too) + retry/backoff + a higher completion-token cap so large registers no
longer truncate mid-JSON.

Isolation: writes ONLY into this folder (register_info/, metrics.json, analysis/).
The prior with-enums output is preserved as *_with_enums. Reads everything else RO.

Run:  GROQ_API_KEY=... python oneoff_evolved_rm0041/run_noenum_rm0041.py
"""
import os, sys, re, json, time, importlib.util, subprocess
from pathlib import Path


def query_name(register: str) -> str:
    """Reconcile the SVD/verified register name to the datasheet's HEADING before
    building the retrieval query (fix (b)). The SVD (and verified CSV) split some
    registers by mode -- e.g. TIM `CCMR1_Input` / `CCMR1_Output` -- but the manual
    titles that section just `CCMR1` (both modes described together). Querying with
    the `_input`/`_output` suffix returns the wrong chunk (the table of contents).
    We normalize ONLY the query; the output file + scoring keep the full name, since
    the verified datasheet uses `ccmr1_input`/`ccmr1_output`."""
    return re.sub(r"_(input|output)$", "", register, flags=re.I)

REPO = "/home/ramla/hal_agent-phase-1d"
# The evolved retriever is vendored next to this script (sha256 in README), so the
# experiment is self-contained. Source: hal_agent-retrieval v6_rm0041_seed42_labelfix.
HERE = os.path.dirname(os.path.abspath(__file__))
EVOLVED = os.path.join(HERE, "retriever", "best_program.py")
DEVICE_DIR = f"{REPO}/devices/stm/rm0041"
CHUNKS_DIR = f"{REPO}/chunked_datasheets/stm/rm0041/chunks/md"
CHUNKS_INDEX = f"{CHUNKS_DIR}/chunks_index.csv"
VERIFIED = f"{REPO}/verified_datasheet/stm/rm0041_stm32f100.csv"
COMPARE = f"{REPO}/optimization/common/compare_generator_with_verified.py"

OUT = Path(f"{REPO}/oneoff_evolved_rm0041")
REGDIR = OUT / "register_info"
METRICS = OUT / "metrics.json"

MODEL = "openai/gpt-oss-120b"
RATE_IN = 0.15 / 1e6
RATE_CACHED_IN = 0.075 / 1e6
RATE_OUT = 0.60 / 1e6
MAX_TOKENS = 8000        # up from default; big enum-free registers still fit comfortably
MAX_RETRIES = 5
BASE_BACKOFF = 2.0

# the enumerated_values schema block to strip from the system prompt (drops enums)
ENUM_SCHEMA_BLOCK = (
    "        - `enumerated_values`: A list of enumerated values that could be empty if there are no enumerated values. Each object in the list has the following fields:\n"
    "            - `value`: The value of the enumerated value. A string.\n"
    "            - `name`: The name of the enumerated value. A string.\n"
)

if REGDIR.exists() and any(REGDIR.iterdir()):
    sys.exit(f"refusing to overwrite existing {REGDIR} (move it aside first)")
REGDIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(HERE, "retriever"))   # so best_program.py finds _shared_cache
from prompts.register_info_stm import (
    create_register_info_stm_system_prompt, create_register_info_stm_user_prompt)
from utils.parse_output import get_reasoning_from_response, get_json_block_from_response
from agent_tools.tools import all_svd_file_paths
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from openai import OpenAI

spec = importlib.util.spec_from_file_location("evolved_rm0041", EVOLVED)
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

svds = all_svd_file_paths(DEVICE_DIR)
reg_list = [(p, r) for p in get_peripheral_names(svds)
            for r in get_register_names_for_peripheral(svds, p)]
print(f"full device: {len(reg_list)} registers to extract (enums DROPPED)")

# build the enum-free system prompt once and verify the strip actually happened
sys_prompt = create_register_info_stm_system_prompt(function_calls_description=None, examples=None)
if ENUM_SCHEMA_BLOCK not in sys_prompt:
    sys.exit("ERROR: enum schema block not found in system prompt — the prompt changed; "
             "update ENUM_SCHEMA_BLOCK before running (else enums would NOT be dropped).")
sys_prompt = sys_prompt.replace(ENUM_SCHEMA_BLOCK, "")
assert "enumerated_values" not in sys_prompt, "enum still referenced after strip"


def strip_enums(data):
    """Belt-and-suspenders: remove any enumerated_values the model emits anyway."""
    for f in data.get("subfields", []) or []:
        f.pop("enumerated_values", None)
    return data


t0 = time.time()
col, proc = ev.setup_database(CHUNKS_DIR, CHUNKS_INDEX)
setup_s = time.time() - t0

tot_in = tot_cached = tot_out = written = empty = still_fail = no_json = trunc = 0
tgen = time.time()
name_fixed = 0
for i, (p, r) in enumerate(reg_list, 1):
    qr = query_name(r)
    if qr != r:
        name_fixed += 1
    ctx = ev.run_retrieval(p, qr, col, proc)   # retrieve with datasheet-heading name
    if not ctx:
        empty += 1; continue
    data = None; last = ""
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL, timeout=90, max_completion_tokens=MAX_TOKENS,
                messages=[{"role": "system", "content": sys_prompt},
                          {"role": "user", "content": create_register_info_stm_user_prompt(r, p, ctx)}])
            u = resp.usage
            cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
            tot_in += u.prompt_tokens; tot_out += u.completion_tokens; tot_cached += cached
            if resp.choices[0].finish_reason == "length":
                trunc += 1  # count truncations even at the higher cap
            _, rest = get_reasoning_from_response(resp.choices[0].message.content or "")
            js = get_json_block_from_response(rest)
            data = json.loads(js) if js else None
            if not isinstance(data, dict):   # model sometimes returns a bare list -> invalid
                data = None
            break  # got a real API response (parseable or not); no point retrying
        except Exception as e:
            last = type(e).__name__
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_BACKOFF * (2 ** attempt))
    if data is None:
        if last:
            still_fail += 1
        else:
            no_json += 1
        continue
    (REGDIR / f"{p}_{r}").write_text(json.dumps(strip_enums(data)))
    written += 1
    if i % 50 == 0:
        print(f"  {i}/{len(reg_list)}  written={written} no_json={no_json} trunc={trunc} fail={still_fail}")
gen_s = time.time() - tgen

metrics = {
    "model": MODEL, "evolved_program": EVOLVED,
    "variant": "enums_dropped + query_name_reconciled",
    "query_names_reconciled": name_fixed,
    "max_completion_tokens": MAX_TOKENS, "max_retries": MAX_RETRIES,
    "registers_attempted": len(reg_list), "registers_written": written,
    "empty_retrieval": empty, "no_json": no_json, "still_failing": still_fail,
    "truncated_finish_length": trunc,
    "prompt_tokens": tot_in, "cached_input_tokens": tot_cached, "completion_tokens": tot_out,
    "cost_usd_est": round((tot_in - tot_cached) * RATE_IN + tot_cached * RATE_CACHED_IN
                          + tot_out * RATE_OUT, 4),
    "embeddings": "FastEmbed local ($0)",
    "setup_seconds": round(setup_s, 1), "generate_seconds": round(gen_s, 1),
}
METRICS.write_text(json.dumps(metrics, indent=2))
print("\n=== metrics (enums dropped) ==="); print(json.dumps(metrics, indent=2))

print("\n=== accuracy vs verified datasheet ===")
subprocess.run([sys.executable, COMPARE, "-v", VERIFIED, str(REGDIR)],
               cwd=str(OUT), env={**os.environ, "PYTHONPATH": REPO})
r = (OUT / "analysis/generator_comparison.csv")
if r.exists():
    print("\nsummary row:\n" + r.read_text().strip().splitlines()[-1])
