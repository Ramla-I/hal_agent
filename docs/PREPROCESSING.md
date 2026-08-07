# Preprocessing a Reference Manual (getting an RM generator-ready)

**Goal:** take a raw STM reference-manual PDF and produce everything the pipeline
needs so the generator (and the constraint chain) can run on it.

> **This is now automated by one command:**
> ```
> python scripts/run_stm_batch.py --devices {rm} --auto-register
> ```
> Run it on the **host** (it registers the device in the host-owned
> `config_devices.json` — the container can't — then launches s0 in Docker). s0's
> Step 1 does the chunking + ingest, writing to `chunked_datasheets/{mfr}/{rm}/chunks`
> (the location the generator + constraint step read; R1/R7 reconciled), with a
> readiness gate before generation. The rest of this doc is the **reference / manual
> path** for debugging or doing a step by hand.

The manual path below is a **multi-step process** with several sharp edges. It
records the exact steps *and* the roadblocks; roadblock status is noted inline.

---

## The key mental model: TWO independent consumers

An RM is "ready" only when **both** downstream consumers are satisfied — they use
**different artifacts in different locations**. Verifying one is not enough (this
has bitten us twice):

| Consumer | Needs | Location |
|---|---|---|
| **Generator retrieval** (openevolve → local vector DB) | registration + a ChromaDB vector store + a `vector_stores.json` local entry | `config_devices.json`, `databases/{rm}_md_chunks`, `devices/stm/{rm}/vector_stores.json` |
| **Constraint anchoring** (s0 Step 6 quote_anchor) | markdown chunks | `chunked_datasheets/stm/{rm}/chunks/md` |

> There are **two chunk directories** and they are NOT interchangeable:
> - `chunked_datasheets/stm/{rm}/chunks/md` — read by the **constraint** step.
> - `devices/stm/{rm}/chunks` — where s0 Step 1 chunks for the **generator** store
>   (pipeline.py's *default* output). See Roadblock R1.

---

## Prerequisites

- `devices/stm/{rm}/{rm}.pdf` — the datasheet PDF.
- `devices/stm/{rm}/svd/*.svd` — SVD ground truth (for the generator's register list).
- `devices/stm/rm_device_mapping.xml` — RM → SVD-device mapping.
- Docker image built (`scripts/docker_run.sh build`) — host Python lacks deps.

---

## Steps

### 1. Register the RM in `config_devices.json`  *(must be first)*

Ingestion looks the device up in `config.user_contexts`; an unregistered device
fails with `Device 'rmXXXX' not found in config.user_contexts`. Append:

```json
{ "device_name": "rm0530", "manufacturer": "STM", "peripheral_name": "",
  "driver_path": "", "run": 1, "file_id": "", "vs_id": "" }
```

`file_id`/`vs_id` are legacy OpenAI ids — **leave empty** for local retrieval.
**Do this on the host** (see Roadblock R6 — the container can't write this file).

### 2. Chunk the PDF → `chunked_datasheets/` (constraint chunks + generator source)

```bash
scripts/docker_run.sh run \
  context_retrieval/preprocessing/pipeline.py \
  devices/stm/{rm}/{rm}.pdf {rm} \
  --output-dir chunked_datasheets/stm/{rm}/chunks \
  --format markdown --embed-metadata --backend local
```

- `--output-dir` is **mandatory** — without it chunks land in `devices/...` where
  the constraint step never looks (Roadblock R1).
- `--embed-metadata` produces `chunks/md_enriched/` (metadata-augmented chunks) —
  this is what the vector store ingests.
- `--backend local` also builds the ChromaDB (Step 3) in the same run *if* the
  device is already registered. If you registered in Step 1, this one command
  covers Steps 2+3.

Produces: `chunks/md/` and `chunks/md_enriched/` (each holds `*.txt` chunk files —
Roadblock R9 — plus `chunks_index.csv` and `metadata.json`).

### 3. Build the local vector store (if not built in Step 2)

```bash
scripts/docker_run.sh run \
  context_retrieval/preprocessing/ingest_local_vector_db.py {rm} \
  --chunks-dir chunked_datasheets/stm/{rm}/chunks/md_enriched \
  --embedding-provider local
```

Produces: `databases/{rm}_md_chunks` (ChromaDB) **and** writes/updates
`devices/stm/{rm}/vector_stores.json` with a `local_md_chunks` entry set as the
default (Roadblock R4). CPU-only (FastEmbed) — no API cost.

### 4. Verify readiness (the whole-picture check)

All four must be true before the generator will use the RM correctly:

```bash
rm=rm0530
ls chunked_datasheets/stm/$rm/chunks/md/*.txt >/dev/null && echo "constraint chunks OK"
python3 -c "import json; print('registered', $rm in {d['device_name'] for d in json.load(open('config_devices.json'))['devices']})"  # true
ls -d databases/${rm}_md_chunks                       # ChromaDB exists
python3 -c "import json;d=json.load(open('devices/stm/$rm/vector_stores.json'));print('default',d['default'],'local_db',d['vector_stores']['local_md_chunks']['local_db_name'])"
```

Then the generator runs with openevolve retrieval:
`s0_run_full_analysis.py --devices {rm} --retrieval openevolve --skip-validator
--constraint-validation --constraint-chunks-root chunked_datasheets/stm` (Roadblock R5).

---

## Batch tooling (current)

`scripts/run_stm_batch.py --auto-register` is the one driver: per RM it registers
the device host-side, then launches s0, which folds preprocessing (chunk → ingest →
`vector_stores.json`) into **Step 1** before generating. There is no separate
batch-preprocess step to run anymore.

---

## Roadblocks (record for automation)

- **R1 — chunk output path.** `pipeline.py` defaults to `{pdf_dir}/chunks`
  (`devices/...`), which the constraint step and `config.chunk_index_path` never
  read. Must pass `--output-dir chunked_datasheets/stm/{rm}/chunks`.
  *Automation:* make `chunked_datasheets/` the default, or derive it.

- **R2 — large-PDF markdown conversion.** `pymupdf4llm.to_markdown` does per-page
  layout analysis (~1.2 s/page) in ONE silent whole-document call. STM has 9
  datasheets of 60–94 MB / 3000–7600 pages → 60–90 min each, and it *looks* hung
  (no output). **Fixed:** `p1_chunk_pdf_to_files.extract_text_markdown` now splits
  page ranges across processes above `parallel_threshold` (min(cpu,48) workers) —
  rm0399 (3556 p): 69 min → 3.4 min (~20×), output byte-identical. Plain-text
  extraction is 600× faster but loses table structure (register bit tables).

- **R3 — register-before-ingest ordering.** `ingest_local_vector_db.py` errors if
  the device isn't in `config.user_contexts`. Step 1 must precede Step 3.
  *Automation:* have ingest auto-register a minimal entry if missing.

- **R4 — vector_stores.json not created.** `ingest_local_vector_db.py` used to
  *skip* registration when `vector_stores.json` was absent (`return 0`) — leaving a
  built ChromaDB the generator never uses (silent fallback to keyword search,
  because `build_context_retrieval_params` resolves `local_db_name` from that
  file). **Fixed & verified:** it now creates the file and sets the local store as
  default (rm0351/rm0432: `vector_stores.json` written with `default=local_md_chunks`,
  `local_db_name={rm}_md_chunks` — the generator resolves LOCAL retrieval).

- **R5 — Step 4 validator crashes on openevolve.** The full structure validator's
  retrieval path doesn't resolve `ContextRetrievalMethod.OPENEVOLVE` and aborts the
  whole per-device run before Steps 5/6. Run with `--skip-validator` (s6 is the
  candidate validator that produces verdicts anyway).
  *Automation:* teach the validator retrieval to resolve openevolve, or make it
  non-fatal.

- **R6 — config ownership.** `config_devices.json` is host-owned (`ramla`); the
  Docker container runs as `nobody` and can't write it (mode 664). Registration
  must be done on the **host**, not inside a container script.

- **R7 — two chunk locations / two formats.** `md` vs `md_enriched`, and
  `devices/.../chunks` (generator, s0 Step 1) vs `chunked_datasheets/.../chunks`
  (constraint anchoring). Easy to build one and think the RM is "ready."

- **R8 — TaskStop ≠ container kill.** Stopping a background batch leaves its Docker
  container running (races on the same files, keeps spending API). Always
  `docker kill` the container as part of stopping a batch.

- **R9 — chunk files are `.txt`.** The `chunks/md/` dir holds `{rm}_pNNN_cNN.txt`
  files (not `.md`) plus `chunks_index.csv` + `metadata.json`. Don't glob `*.md`.

- **R10 — ChromaDB add() batch cap.** A single `collection.add()` is limited to
  ~5461 items; the big datasheets have 5.5k–7.6k chunks (rm0486: 7606) →
  `InternalError: Batch size … greater than max batch size`. **Fixed:**
  `vector_store.add_documents` now splits the add into ≤5000-item batches.

- **R11 — long-running containers don't reliably pick up mid-run code edits.** A
  container started *before* an edit kept failing on the R10 bug even for
  subprocesses spawned after the fix (stale bytecode / import caching over the
  bind mount), while a freshly-started container got it right. After any code fix
  during a batch: `docker kill` the container, clear `__pycache__`, and relaunch.
  Also: a failed ingest leaves a **partial `databases/{rm}_md_chunks`** dir, which
  a resume-by-db-exists skips — delete it before re-running.

---

## Automated (previously the TODO for a one-command preprocessor)

All four are now done by `scripts/run_stm_batch.py --auto-register` + s0:

1. ✅ Auto-register (R3/R6) — the host-side driver writes the `config_devices.json`
   entry if missing (serially, before launching the container).
2. ✅ Default chunk output to `chunked_datasheets/` (R1) — s0 Step 1 now writes there.
3. ✅ One driver: register → (s0) chunk → ingest (+vector_stores.json) → readiness
   gate → generate → reviews.
4. ✅ Reconcile the two chunk locations (R7) — s0 Step 1 writes to
   `chunked_datasheets/`, the same place the generator + constraint step read.
