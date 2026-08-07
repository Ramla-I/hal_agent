# Context retrieval

How the pipeline finds the right slice of a datasheet to feed the LLM. Every LLM
stage that needs datasheet text — the **generator** (per register), the **validator**
(per register batch), and the **constraint** anchoring — goes through the same
retrieval interface: `context_retrieval/retrieve_context.py::retrieve_context(...)`
(single register) and `retrieve_context_for_peripheral(...)` (batched).

## Retrieval methods

`ContextRetrievalMethod` (`defs.py`) selects the backend; `s0 --retrieval` overrides it.

| Method | What it does | Reads |
|---|---|---|
| `openevolve` | **The one the STM pipeline uses.** An evolutionary-optimized retrieval *program* (`openevolve_retrieval/output_{rm}/best/best_program.py`, or a vendor default) builds its own in-memory vector DB and ranks chunks. | plain `chunks/md/*.txt` + `chunks/md/chunks_index.csv` |
| `local_vector_db` | Persistent local ChromaDB with metadata filtering. | `databases/{rm}_md_chunks` (built from `md_enriched` + `metadata.json`) |
| `openai_file_search` | OpenAI vector store (hosted). | a `vs_id` |
| `keyword_search` | Section/keyword match over the markdown. | the markdown |
| `regex` | Regex over the markdown. | the markdown |

The run flow (`run_stm_batch → s0`) uses **`openevolve`**. `retrieve_context.py` is the
dispatcher; the openevolve branch calls `context_retrieval/openevolve_search.py`.

## Data flow (preprocessing → retrieval)

Preprocessing (`s0` Step 1 / `context_retrieval/preprocessing/pipeline.py`) runs
**chunk → enrich → augment → ingest**, writing everything under
`chunked_datasheets/{mfr}/{rm}/chunks/`:

| Artifact | Created by | Used by |
|---|---|---|
| `md/*.txt` | **chunk** (`p1_chunk_pdf_to_files.py`) — split the markdown into token-bounded chunks | **openevolve** (the actual retrieval text) |
| `md/chunks_index.csv` | **chunk** — one row per chunk | **openevolve** `load_raw_chunks` + local-DB ingest (see below) |
| `md/metadata.json` | **enrich** (`p2_enrich_chunk_metadata.py`) — per-chunk metadata | augment + local-DB metadata filtering |
| `md_enriched/*.txt` | **augment** (`p3_...`) — metadata embedded into chunk text | local-DB ingest only |
| `databases/{rm}_md_chunks/` | **ingest** (`ingest_local_vector_db.py`) from `md_enriched` | `local_vector_db` retrieval |
| `databases/oe_embed_cache.sqlite` | openevolve embedding step (shared) | every openevolve build (see below) |

**Key point:** in the openevolve flow, only `md/*.txt` and `md/chunks_index.csv` are
actually used. `md_enriched/`, `metadata.json`, and `databases/{rm}_md_chunks` are still
built by default (enrichment is on: `--embed-metadata` defaults `True`) but only feed
the `local_vector_db` path. So they're extra preprocessing work in an openevolve run.

## OpenEvolve internals

- **The store is an in-memory `chromadb.EphemeralClient`** (`best_program.py::build_ephemeral_store`), *not* persisted like `databases/{rm}_md_chunks`. It's built on the first retrieval call in a process.
- **Per-process cache.** `openevolve_search.py::_db_cache` caches the built collection keyed by `(program_path, chunks_index_csv)`. Same device → same keys → reused for every subsequent register in that process; a **different process rebuilds from scratch**. This is why the candidate validator (s6) now runs **in-process inside s0** (Step 5b) — it reuses the collection the generator already built instead of paying a fresh 60-min build on the giants.
- **Loading + page attribution.** `load_raw_chunks(chunks_dir, chunks_index_csv)` walks `chunks_index.csv`, resolves each chunk by `chunks_dir/{chunk_id}.txt` (falling back to the row's `file_path`), and carries `page_number` through — so a retrieved chunk can cite its datasheet page.

## `chunks_index.csv`

One row per chunk: `chunk_id, file_path, datasheet, page_number, chunk_index,
total_chunks_on_page, global_chunk_index, token_count, char_count`. It's the manifest
openevolve uses to enumerate/load chunks and attach page numbers, and the local-DB
ingest reads it for `page_number` metadata. It is **the one preprocessing artifact
openevolve depends on** (besides the `md` text itself).

- **`file_path` may be absolute `/app/...`** — `/app` is the repo's mount point inside
  Docker (`docker_run.sh -v $REPO_ROOT:/app -w /app`), **not a placeholder**. RMs chunked
  with a relative `--output-dir` (via `preprocess_stm_batch`) record relative paths;
  RMs chunked by s0's `preprocess_device` (whose `base_output_dir` uses `_REPO_ROOT`,
  = `/app` in-container) record absolute `/app/...`. Harmless in the normal flow because
  loading prefers `chunks_dir/{chunk_id}.txt`; but `/app/...` won't resolve if the CSV is
  read on the **host**.

## Metadata & keywords (enrichment)

`metadata.json` is produced **deterministically** (no LLM by default) by
`p2_enrich_chunk_metadata.py::enrich_single_chunk`, one entry per chunk, with fields:
`page, chunk_number, chapter/section/subsection, peripheral, registers_mentioned,
fields_mentioned, chunk_type, has_tables/code/diagrams, keywords, topics, description,
importance, completeness`. Section/peripheral/registers come from regex over the
markdown headers and register-name patterns.

- **`keywords`** = `extract_keywords`: tokenize → drop stopwords and <3-char words →
  return the **top-10 most frequent** tokens. A plain bag-of-words frequency ("simple
  for now"). Only consumed by the local-DB path.

## `oe_embed_cache.sqlite` (shared embedding cache)

- **One file for the whole corpus**: `databases/oe_embed_cache.sqlite` (not per-RM;
  `_shared_cache.py`, path env-overridable via `_DB_PATH`).
- **Key = `md5(chunk text)` → embedding blob** (`emb(h TEXT PRIMARY KEY, v BLOB)`).
  Content-keyed and device-agnostic, so identical chunk text (shared datasheet
  boilerplate) is embedded **once and reused across every RM and every process** —
  it's what makes repeated openevolve builds cheap.
- **Caveat:** the key is the **text only** — no embedding model/provider in it. If you
  switch embedders, the cache returns vectors from the *old* model for the same text.
  Clear it (`rm databases/oe_embed_cache.sqlite`, it rebuilds) or repoint `_DB_PATH`.

## Readiness (what a run needs)

For the openevolve flow, the essentials are `chunks/md/*.txt` + `chunks/md/chunks_index.csv`
(and, because preprocessing builds it, the local DB). `s0`'s post-Step-1 readiness gate
(`assert_ready`) checks the chunks + `databases/{rm}_md_chunks` before generation, so a
missing/failed preprocess fails fast instead of silently degrading to keyword search.
