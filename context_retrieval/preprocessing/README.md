# Preprocessing Pipeline

This directory contains scripts for preprocessing datasheets into a vector store optimized for semantic search with contiguous chunk expansion.

## Quick Start

Use the unified pipeline script for a single-command workflow (recommended):

```bash
# Basic usage - chunk, enrich, upload, and update devices/.../vector_stores.json
python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041

# Higher quality retrieval (recommended for register-heavy docs): markdown extraction + embedded metadata
python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
    --format markdown --embed-metadata

# Local-only run (no upload) to inspect chunks/metadata
python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
    --skip-upload
```

## Workflow Options (Common Recipes)

### Option A: Fast setup (good baseline)

```bash
python preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> \
  --format text \
  --max-tokens 800 --overlap-tokens 100
```

### Option B: Best retrieval quality (recommended default)

```bash
python preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> \
  --format markdown \
  --max-tokens 1200 --overlap-tokens 0 \
  --embed-metadata
```

Notes:
- `--format markdown` improves table structure (slower).
- `--embed-metadata` prepends a structured comment header to each chunk so metadata becomes searchable.
- Chunk files are currently saved as `*.txt` even in markdown mode (content is markdown, extension is `.txt`).

## Chunking Details (IDs, Formats, Defaults)

### Chunk ID / filename format

Chunks are written as:

```
{datasheet}_p{page:03d}_c{chunk:02d}.txt
```

Examples:
- `rm0041_p001_c01.txt` (page 1, chunk 1)
- `rm0041_p127_c03.txt` (page 127, chunk 3)

### Text vs Markdown extraction

- **text** (`--format text`)
  - Fastest, smaller files
  - Tables usually become “one cell per line” (harder for the LLM to interpret)
- **markdown** (`--format markdown`)
  - Slower, but tables are often preserved in a parseable structure
  - Recommended for register maps / bitfield tables

### Recommended defaults

- **Register-heavy manuals**: `--format markdown --max-tokens 1200 --overlap-tokens 0 --embed-metadata`
- **Text-heavy docs**: `--format text --max-tokens 800 --overlap-tokens 100`

## Pipeline Steps

The pipeline performs these steps:

1. **Chunk PDF** (`p1_chunk_pdf_to_files.py`)
   - Extracts text or markdown from PDF
   - Splits into token-sized chunks with configurable overlap
   - Creates `{name}_p{page}_c{chunk}.txt` files

2. **Enrich Metadata** (`p2_enrich_chunk_metadata.py`)
   - Extracts section hierarchy from markdown headers
   - Identifies peripheral and register mentions
   - **Expands parameterized patterns** like:
     - `GPIOx_CRL (x=A..G)` → `GPIOA_CRL, GPIOB_CRL, ...`
     - `ADC_JOFRx (x=1..4)` → `ADC_JOFR1, ADC_JOFR2, ADC_JOFR3, ADC_JOFR4`
   - Classifies content type (register_table, overview, etc.)
   - Assesses importance scoring
   - Saves combined metadata.json and metadata_summary.json

3. **Augment Chunks** (optional, `p3_augment_chunks_with_metadata.py`)
   - Embeds metadata as headers in chunk content
   - Makes metadata searchable by semantic search
   - Creates augmented copy of chunks

4. **Upload to Vector Store** (`vector_store_uploader.py`, library — no standalone CLI)
   - Creates OpenAI vector store
   - Uploads chunks with attributes:
     - **basic** by default (from `chunks_index.csv`)
     - **enriched** when metadata.json is present
   - Saves `chunks_index.csv` with file_ids for retrieval expansion
   - Invoked automatically by `pipeline.py`; for one-off use call
     `create_vector_store_with_chunks(...)` or
     `create_vector_store_with_enriched_chunks(...)` from Python.

## Command Reference (pipeline.py)

`preprocessing/pipeline.py` is the supported “happy path” CLI. Most users should only need:

- `--format {text,markdown}`
- `--max-tokens`, `--overlap-tokens`
- `--embed-metadata`
- `--skip-upload`

Less common (advanced) options:
- **Paths**
  - `--output-dir`: where `chunks/` is created (default: alongside the PDF)
  - `--device-dir`: where `vector_stores.json` is updated (default: alongside the PDF)
- **Vector store naming**
  - `--store-name`: key used inside `devices/.../vector_stores.json`
  - `--vector-store-name`: display name for OpenAI vector store
- **OpenAI chunking strategy (server-side)**
  - `--chunking-strategy {static,auto}` (default: static)
  - `--openai-max-tokens` (default: 1200)
  - `--openai-overlap-tokens` (default: 0)

## Related Tools

- **Datasheet format analysis (optional)**: `datasheet_metadata_single_pass/query_datasheet.py`

```bash
# Structured questions (default)
python preprocessing/datasheet_metadata_single_pass/query_datasheet.py devices/stm/rm0041/rm0041.pdf

# Naive / open-ended analysis
python preprocessing/datasheet_metadata_single_pass/query_datasheet.py --mode naive devices/stm/rm0041/rm0041.pdf
```

## Using the Result in the Agent

There are two common ways to “wire in” the output:

1. **Use `devices/.../vector_stores.json`** (recommended): `pipeline.py` updates it automatically.

```python
from utils.vector_store_config import get_vector_stores

config = get_vector_stores("devices/<mfg>/<dev>")
vs_id = config.get_vs_id("<store-name>")
chunk_index_path = config.get_chunk_index_path("<store-name>")  # full path to chunks_index.csv
```

2. **Directly set `ContextRetrievalParameters.chunk_index_path`** (for experiments).

## Output Structure

**Chunks** (saved to `--output-dir`, defaults to `{pdf_dir}/chunks/`):
```
{output_dir}/
├── text/ or md/              # Chunk files
│   ├── {name}_p001_c01.txt
│   ├── {name}_p001_c02.txt
│   ├── ...
│   ├── chunks_index.csv      # Chunk index (basic metadata + file_ids after upload)
│   ├── metadata.json         # Enriched metadata for all chunks
│   └── metadata_summary.json # Summary statistics
├── text_augmented/ (optional)  # Chunks with embedded metadata
└── vector_store_info.json    # Vector store ID and config (legacy)
```

**Config** (saved to `--device-dir`, defaults to PDF's directory):
```
{device_dir}/
└── vector_stores.json        # Canonical vector store registry
```

> **Note:** `vector_stores.json` belongs in the device directory (e.g., `devices/stm/rm0041/`), NOT in `chunked_datasheets/`. If storing chunks separately, use `--output-dir` for chunks and let `--device-dir` default to the PDF location.

## Contiguous Chunk Expansion

The pipeline creates a `chunks_index.csv` that enables contiguous chunk expansion during retrieval. This feature:

1. After semantic search returns initial chunks
2. Looks up chunks from subsequent pages (page+1, page+2)
3. Appends them to provide complete context

Configure in `config.py`:
```python
CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
    ...
    chunk_expansion_enabled=True,
    pages_after=2,
    chunk_index_path="chunked_datasheets/stm/rm0041/chunks/text/chunks_index.csv",
)
```

## Individual Scripts

For more control, run scripts individually:

```bash
# Step 1: Chunk PDF
python preprocessing/p1_chunk_pdf_to_files.py \
    devices/stm/rm0041/rm0041.pdf \
    chunked_datasheets/stm/rm0041/chunks/text \
    rm0041 \
    --max-tokens 800 \
    --overlap-tokens 100

# Step 2: Enrich metadata (saves metadata.json in chunks_dir)
python preprocessing/p2_enrich_chunk_metadata.py \
    chunked_datasheets/stm/rm0041/chunks/text \
    --extension .txt

# Step 3: (Optional) Augment chunks
python preprocessing/p3_augment_chunks_with_metadata.py \
    chunked_datasheets/stm/rm0041/chunks/text \
    --output-dir chunked_datasheets/stm/rm0041/chunks/text_augmented

# Step 4: Upload — vector_store_uploader has NO standalone CLI.
# Either run the full pipeline.py (which calls it internally),
# or call the library function from Python:
python -c "
from context_retrieval.preprocessing.vector_store_uploader import (
    create_vector_store_with_enriched_chunks,
)
vs_id, infos = create_vector_store_with_enriched_chunks(
    chunks_dir='chunked_datasheets/stm/rm0041/chunks/text',
    vector_store_name='rm0041_enriched',
    datasheet_name='rm0041',
)
print(vs_id)
"
```
## Legacy / Notes
- `preprocessing/old/` contains legacy scripts that aren’t part of the current workflow and are intentionally not documented here.

## Register Name Expansion

The enrichment step automatically expands parameterized register patterns:

| Pattern | Example | Expansion |
|---------|---------|-----------|
| Numeric range | `ADC_JOFRx (x=1..4)` | ADC_JOFR1, ADC_JOFR2, ADC_JOFR3, ADC_JOFR4 |
| Alphabetic range | `GPIOx_CRL (x=A..G)` | GPIOA_CRL through GPIOG_CRL |
| Comma list | `fPCLKx (x=1,2)` | fPCLK1, fPCLK2 |
| Word range | `EXTI (x=0 to 3)` | EXTI0, EXTI1, EXTI2, EXTI3 |
| Parenthesized | `(BKP_DRx) (x=1..20)` | BKP_DR1 through BKP_DR20 |
| Contextual | `TIM1 register (TIMx_CR1)` | TIM1_CR1 |

## Tips

1. **Combine split tables**: Use LlamaParse with LLM option for better table handling across pages.

2. **Remove TOC for regex matching**: The table of contents can create false positives. Consider removing it if using regex-based matching.

3. **Markdown vs Text**: Use `--format markdown` for better table structure preservation (slower). Use `--format text` for faster processing.

4. **Token sizes**: Default 800 tokens with 100 overlap works well for most datasheets. Increase for documents with longer register descriptions.

## Troubleshooting

- **“No chunk files found”**
  - Ensure the `datasheet_name` argument matches the filenames in the chunk directory.
  - Remember: markdown mode still produces `*.txt` chunk files (content is markdown).
- **Upload fails / auth errors**
  - Ensure `OPENAI_API_KEY` is set in your environment.
- **Metadata file missing (metadata.json)**
  - Run enrichment (`p2_enrich_chunk_metadata.py`) or use the unified pipeline (it runs enrichment automatically).
