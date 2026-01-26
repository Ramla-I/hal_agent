# Preprocessing Pipeline

This directory contains scripts for preprocessing datasheets into a vector store optimized for semantic search with contiguous chunk expansion.

## Quick Start

Use the unified pipeline script for a single-command workflow:

```bash
# Basic usage - chunk, enrich, and upload
python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041

# With markdown format and embedded metadata
python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
    --format markdown --embed-metadata

# Test without uploading
python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
    --skip-upload
```

## Pipeline Steps

The pipeline performs these steps:

1. **Chunk PDF** (`chunk_pdf_to_files.py`)
   - Extracts text or markdown from PDF
   - Splits into token-sized chunks with configurable overlap
   - Creates `{name}_p{page}_c{chunk}.txt` files

2. **Enrich Metadata** (`enrich_chunk_metadata.py`)
   - Extracts section hierarchy from markdown headers
   - Identifies peripheral and register mentions
   - **Expands parameterized patterns** like:
     - `GPIOx_CRL (x=A..G)` → `GPIOA_CRL, GPIOB_CRL, ...`
     - `ADC_JOFRx (x=1..4)` → `ADC_JOFR1, ADC_JOFR2, ADC_JOFR3, ADC_JOFR4`
   - Classifies content type (register_table, overview, etc.)
   - Assesses importance scoring
   - Creates JSON metadata per chunk

3. **Augment Chunks** (optional, `augment_chunks_with_metadata.py`)
   - Embeds metadata as headers in chunk content
   - Makes metadata searchable by semantic search
   - Creates augmented copy of chunks

4. **Upload to Vector Store** (`upload_enriched_chunks.py`)
   - Creates OpenAI vector store
   - Uploads chunks with metadata attributes
   - Saves `upload_summary.csv` for retrieval expansion

## Output Structure

```
{output_dir}/
├── text/ or md/              # Chunk files
│   ├── {name}_p001_c01.txt
│   ├── {name}_p001_c02.txt
│   ├── ...
│   ├── metadata/             # Enriched metadata JSON
│   │   ├── {chunk_id}_metadata.json
│   │   ├── all_metadata.json
│   │   └── metadata_summary.json
│   ├── upload_summary.csv    # Chunk index for retrieval
│   └── {name}_chunks_metadata.csv
├── text_augmented/ (optional)  # Chunks with embedded metadata
└── vector_store_info.json    # Vector store ID and config
```

## Contiguous Chunk Expansion

The pipeline creates an `upload_summary.csv` that enables contiguous chunk expansion during retrieval. This feature:

1. After semantic search returns initial chunks
2. Looks up chunks from subsequent pages (page+1, page+2)
3. Appends them to provide complete context

Configure in `config.py`:
```python
CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
    ...
    chunk_expansion_enabled=True,
    pages_after=2,
    chunk_index_path="devices/stm/rm0041/chunks/text/upload_summary.csv",
)
```

## Individual Scripts

For more control, run scripts individually:

```bash
# Step 1: Chunk PDF
python preprocessing/chunk_pdf_to_files.py \
    devices/stm/rm0041/rm0041.pdf \
    devices/stm/rm0041/chunks/text \
    rm0041 \
    --max-tokens 800 \
    --overlap-tokens 100

# Step 2: Enrich metadata
python preprocessing/enrich_chunk_metadata.py \
    devices/stm/rm0041/chunks/text \
    --extension .txt

# Step 3: (Optional) Augment chunks
python preprocessing/augment_chunks_with_metadata.py \
    devices/stm/rm0041/chunks/text \
    --output-dir devices/stm/rm0041/chunks/text_augmented

# Step 4: Upload
python preprocessing/upload_enriched_chunks.py \
    devices/stm/rm0041/chunks/text \
    rm0041_enriched \
    rm0041
```

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
