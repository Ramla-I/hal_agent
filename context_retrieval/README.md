# Context Retrieval

This folder is the **runtime retrieval layer**. The pipeline asks it for the
slice of a datasheet relevant to a `(peripheral, register)` query, and gets
back ranked chunks formatted for the generator LLM. Four backends are
implemented; a single dispatcher picks the right one based on
`ContextRetrievalParameters.context_retrieval_method`.

For preprocessing (chunking a PDF + ingesting into a vector store), see
[`preprocessing/README.md`](preprocessing/README.md). For tuning retrieval
*settings* across backends, see [`optimization/retrieval/`](../optimization/retrieval/).
For evolving the retrieval *code itself*, see [`openevolve_retrieval/`](../openevolve_retrieval/).

## Architecture

Two entry points, both returning `(formatted_xml, embedding_ids)`:

```
                                            ┌──────────────────────────────┐
                                            │ ContextRetrievalParameters   │
                                            │   .context_retrieval_method  │
                                            └──────────────┬───────────────┘
                                                           │
        ┌──────────────────────────────────────────────────┴──────────────────┐
        │                                                                     │
        ▼                                                                     ▼
┌──────────────────┐                                              ┌──────────────────┐
│ retrieve_context │    needs device dir + manufacturer            │  search_context  │
│  (per-register   │    (uses keyword_infos.json or chunked        │   (semantic-only │
│   or per-periph) │     datasheet paths)                          │    query string) │
└────────┬─────────┘                                              └────────┬─────────┘
         │                                                                 │
         │      ┌────────────────────┬───────────────────┬────────────┐   │
         │      │                    │                   │            │   │
         ▼      ▼                    ▼                   ▼            ▼   ▼
    ┌─────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌────────────────┐
    │  keyword_   │   │   openevolve_   │   │  openai_file_   │   │ local_vector_  │
    │   search    │   │    search       │   │   search        │   │   search       │
    └─────────────┘   └─────────────────┘   └────────┬────────┘   └───────┬────────┘
                                                     │                    │
                                                     └────────┬───────────┘
                                                              │ (raw SearchResult list)
                                                              ▼
                                                  ┌──────────────────────┐
                                                  │   post_processing    │
                                                  │  • keyword boost     │
                                                  │  • score threshold   │
                                                  │  • trim to N         │
                                                  │  • chunk expansion   │
                                                  │  • neighbor expand   │
                                                  │  • XML formatting    │
                                                  │  • embedding_ids out │
                                                  └──────────────────────┘
```

`retrieve_context()` vs `search_context()` — when to use which:
- **`retrieve_context()`** when the caller has device context (device name,
  device_dir, manufacturer) and wants the layer to figure out which retrieval
  artifacts to load (keyword JSON, ChromaDB collection, evolved OE program).
  This is what `core/s1a_generator.py` calls.
- **`search_context()`** when the caller already has a query string and just
  wants semantic search against a known vector store. This is what the
  validator, coverage improver, and the `optimization/retrieval/` sweep use.

## Backends

| Method | When to use | Cost | Key files |
|---|---|---|---|
| `keyword_search` | Cheap baseline when the datasheet has a clean TOC or you already have per-register keyword pages cached. No semantic understanding. | Free | `keyword_search.py`, plus `keyword_infos.json` per device |
| `openai_file_search` | Highest-quality semantic search via OpenAI's vector store. Requires the datasheet to be uploaded (`preprocessing/pipeline.py` does this). | Per-query OpenAI tokens | `openai_file_search.py` |
| `local_vector_db` | Free local equivalent using ChromaDB + FastEmbed + optional FlashRank reranker. Supports `reg_*` metadata filtering. | Free, slower (~1s/query CPU) | `local_vector_search.py`, `vector_db/` package |
| `openevolve` | The evolved retrieval program from `openevolve_retrieval/`. Builds its own ephemeral ChromaDB at runtime; uses heuristic reranking + neighbor expansion. | Free | `openevolve_search.py`, `openevolve_retrieval/output_<device>/best/best_program.py` |
| `regex` | Stub for future regex-based retrieval. Currently returns `None`. | Free | (not implemented) |

Backend selection happens via `ContextRetrievalParameters.context_retrieval_method`
(an enum from `defs.py`). The default depends on the experiment — `optimization/retrieval/evaluate_retrieval.py`
is the canonical place to see what's currently in use.

## Layout

```
context_retrieval/
├── README.md                       # this file
├── retrieve_context.py             # main dispatcher (per-register + per-peripheral, all backends)
├── search.py                       # thin dispatcher for the two semantic backends (no device context needed)
│
├── keyword_search.py               # keyword backend: per-register page lookup via keyword_infos.json
├── openai_file_search.py           # OpenAI file_search backend
├── local_vector_search.py          # local ChromaDB + FastEmbed backend
├── openevolve_search.py            # adapter for the evolved retrieval program
│
├── chunk_index.py                  # ChunkIndex: page-to-chunks map + table metadata, used for expansion
├── post_processing.py              # shared SearchResult, post_process() pipeline, format_results()
├── test_search.py                  # standalone CLI for trying different configs end-to-end
│
├── vector_db/                      # self-contained local ChromaDB package
│   ├── __init__.py
│   ├── config.py                   # env-driven config (DATABASES_DIR, embedding provider, etc.)
│   ├── embeddings.py               # FastEmbed + OpenAI embedding providers
│   ├── reranker.py                 # FlashRank wrapper
│   └── vector_store.py             # VectorStore class — wraps a ChromaDB collection
│
└── preprocessing/                  # offline pipeline: PDF → chunks → vector store
    ├── README.md                   # detailed preprocessing docs
    ├── pipeline.py                 # supported one-shot CLI
    ├── p1_chunk_pdf_to_files.py    # PDF → chunk files
    ├── p2_enrich_chunk_metadata.py # extract section/peripheral/register metadata
    ├── p3_augment_chunks_with_metadata.py  # (optional) embed metadata into chunk text
    ├── vector_store_uploader.py    # library: upload chunks → OpenAI vector store
    ├── ingest_local_vector_db.py   # CLI: ingest chunks → local ChromaDB
    └── old/                        # legacy raw-PDF upload, kept only for optimization_coverage_improver/
```

## How retrieval actually runs

The pipeline goes from a `(peripheral, register)` query to formatted context
in roughly four phases:

1. **Dispatch** — `retrieve_context.py` (or `search.py`) inspects
   `ContextRetrievalParameters.context_retrieval_method` and forwards the call
   to one of the backend modules.

2. **Backend search** — each backend produces raw results:
   - keyword → list of pages → PDF page extraction → datasheet text string
   - openai_file_search → `client.vector_stores.search(...)` → ranked chunks
   - local_vector_search → tiered filter on ChromaDB (`reg_*` metadata first,
     `$contains` fallback, unfiltered fallback) → optional FlashRank rerank
   - openevolve → loads `best_program.py` via importlib, runs its evolved
     `search_and_format()`, returns `[Page N]` blocks

3. **Normalize** — backend-specific output is converted to a uniform list of
   `SearchResult` (defined in `post_processing.py`). The dataclass fields are
   `text`, `score`, `page_number`, `chunk_id`, `source`, `has_tables`,
   `metadata`, `rank`, `keyword_boost`, `is_expansion`.

4. **Post-process** — `post_processing.post_process()` runs a shared pipeline:
   keyword boost → score threshold → trim to `number_embeddings` → chunk
   expansion (page-level + neighbor) → table removal → XML format → extract
   `embedding_ids`. Each step is controlled by a field in
   `ContextRetrievalParameters`.

The keyword backend skips most of post-processing (it's not semantic). The
OpenEvolve backend does its own post-processing inside the evolved program
and returns formatted text directly; the adapter parses `[Page N]` blocks to
recover chunk IDs for `embedding_ids.jsonl`.

## Trying things out

`test_search.py` is a standalone CLI that exercises the four modes
(`search`, `retrieve`, `post-process`, `unit`) without involving the
generator. Useful for debugging a single config.

```bash
source .venv/bin/activate

# Unit test on synthetic data (no DB required)
python context_retrieval/test_search.py --mode unit

# End-to-end local-DB semantic search for one register
python context_retrieval/test_search.py --mode search --method local_vector_db

# Same but OpenAI file_search
python context_retrieval/test_search.py --mode search --method openai_file_search

# Keyword search via retrieve_context()
python context_retrieval/test_search.py --mode retrieve --method keyword_search

# Compare post-processing parameter sweeps on real data
python context_retrieval/test_search.py --mode post-process
```

For an end-to-end retrieval-quality measurement across a whole sweep, use
`optimization/retrieval/smoke_test.py` instead — that one exercises the full
pipeline including the generator.

## Adding a new backend

1. Add a new value to `ContextRetrievalMethod` in `defs.py`.
2. Write a backend module that exposes either:
   - A `search_<name>(...)` function returning `(formatted_text, embedding_ids)`
     for `retrieve_context.py`-style usage, OR
   - A `search_<name>_raw(...)` function returning a raw result list +
     `normalize_<name>_results(...)` to `SearchResult` for `search.py`-style
     usage (which then feeds into the shared `post_process()`).
3. Add a dispatch branch in `retrieve_context.py:retrieve_context()` (and
   `retrieve_context_for_peripheral()` if the backend supports batched queries).
4. If your backend emits `embedding_ids.jsonl` in a format that matches the
   labels DB's `source` paths, `optimization/retrieval/metrics_retrieval.py`
   will score it automatically. Otherwise, expect the
   "Backend support" caveats in that README.

## Preprocessing

See [`preprocessing/README.md`](preprocessing/README.md) for the offline
chunk-and-ingest pipeline. Short version:

```bash
# Chunk + enrich + upload to OpenAI vector store + register in vector_stores.json
python context_retrieval/preprocessing/pipeline.py \
    devices/stm/rm0041/rm0041.pdf rm0041 \
    --format markdown --embed-metadata

# Same, but ingest into a local ChromaDB instead
python context_retrieval/preprocessing/pipeline.py \
    devices/stm/rm0041/rm0041.pdf rm0041 \
    --format markdown --embed-metadata --backend local
```
