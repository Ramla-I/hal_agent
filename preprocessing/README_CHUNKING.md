# PDF Chunking for Generator Analysis

This directory contains scripts to chunk PDFs into individual text files with trackable IDs for better analysis of generator retrieval.

## Workflow

### Step 1: Chunk the PDF

Extract text from PDF and split into manageable chunks with unique IDs.

**Option A: Plain Text (Default - Faster, but tables broken)**

```bash
python preprocessing/chunk_pdf_to_files.py \
    devices/stm/rm0041/rm0041.pdf \
    preprocessing/chunks/rm0041_text \
    rm0041 \
    --max-tokens 800 \
    --overlap-tokens 100
```

**Option B: Markdown (Slower, but better table preservation)**

```bash
python preprocessing/chunk_pdf_to_files.py \
    devices/stm/rm0041/rm0041.pdf \
    preprocessing/chunks/rm0041_md \
    rm0041 \
    --format markdown \
    --max-tokens 800 \
    --overlap-tokens 100
```

**Parameters:**
- `pdf_path`: Path to the PDF file
- `output_dir`: Directory to save chunk files
- `datasheet_name`: Short identifier (e.g., 'rm0041')
- `--max-tokens`: Maximum tokens per chunk (default: 800, matching OpenAI default)
- `--overlap-tokens`: Token overlap between consecutive chunks (default: 100)
- `--format`: Extraction format - `text` (default) or `markdown`

**Output:**
- Individual `.txt` files named `{datasheet}_p{page}_c{chunk}.txt`
  - Example: `rm0041_p005_c02.txt` (page 5, chunk 2)
- `{datasheet}_chunks_metadata.csv` with chunk information

### Step 2: Enrich Chunk Metadata (Optional but Recommended)

Generate rich metadata for each chunk to improve search accuracy:

```bash
python preprocessing/enrich_chunk_metadata.py \
    devices/stm/rm0041/chunks/md \
    --extension .txt
```

**What it does:**
- Analyzes each chunk for content type, peripheral, registers, keywords
- Extracts hierarchical context (chapter/section/subsection)
- Detects content features (tables, code, diagrams)
- Assesses importance based on content
- Saves metadata as JSON files

**Output:**
- Individual metadata JSON files in `<chunks_dir>/metadata/`
- `all_metadata.json` with combined metadata
- `metadata_summary.json` with statistics

**Statistics example:**
```
Total chunks: 1,034
Register tables: 470 (45%)
Critical importance: 283 (27%)
Chunks with tables: 614 (59%)
Unique peripherals: ~40
Unique registers: 442
```

### Step 3: Upload Chunks to Vector Store

**Option A: Basic Upload (No Metadata)**

```bash
python preprocessing/upload_chunks_to_vector_store.py \
    preprocessing/chunks/rm0041 \
    rm0041_chunked \
    rm0041
```

**Option B: Upload with Enriched Metadata (Recommended)**

```bash
python preprocessing/upload_enriched_chunks.py \
    devices/stm/rm0041/chunks/md \
    rm0041_md_enriched \
    rm0041 \
    --metadata-dir devices/stm/rm0041/chunks/md/metadata
```

**Parameters:**
- `chunks_dir`: Directory containing chunk files
- `vector_store_name`: Name for the vector store
- `datasheet_name`: Datasheet identifier (must match step 1)
- `--metadata-dir`: Directory with enriched metadata (for Option B)
- `--chunking-strategy`: How OpenAI should handle the chunks
  - `static` (default, recommended): Prevents re-chunking with max 1200 tokens
  - `auto`: OpenAI treats each file as-is
- `--max-chunk-tokens`: Max tokens for OpenAI re-chunking (100-4096)
- `--chunk-overlap-tokens`: Overlap for OpenAI re-chunking
- `--output`: Path to save upload summary CSV

**Metadata Attributes (Option B):**
When using enriched metadata, each chunk gets these attributes:
- `chunk_id`, `datasheet`, `page`
- `peripheral`, `content_type`, `importance`
- `primary_register`, `registers` (comma-separated)
- `has_tables`, `has_code`, `has_diagrams`
- `keywords` (comma-separated), `tokens`

**Output:**
- New vector store with individual chunk files
- `upload_summary_enriched.csv` tracking all uploaded files and metadata
- Vector store ID printed to console

### Step 4: Update Config

Add the new vector store ID to your config:

```python
# In config.py or your test script
vs_id = "vs_xxxxxxxxxxxxxxxxxxxxx"  # From upload output (basic)
# or
vs_id_md_enriched = "vs_xxxxxxxxxxxxxxxxxxxxx"  # From enriched upload
```

### Step 5: Analyze Retrieval

Use the chunked vector store with your generator to see exactly which chunks are retrieved:

```python
from context_retrieval.semantic_search import search_vector_store

results = search_vector_store(
    query="TIM2 prescaler register",
    vector_store_id=vs_id,
    num_results=16,
    include_file_names=True
)

# Results will include chunk IDs in filenames
# e.g., "rm0041_p127_c01.txt" tells you it's from page 127, chunk 1
```

## Benefits of Chunking

1. **Trackable chunks**: Know exactly which pages/chunks are being retrieved
2. **Controlled chunk size**: Match or optimize chunk size for your use case
3. **Reproducible**: Same chunks every time vs. OpenAI's automatic chunking
4. **Analysis**: Compare different chunk sizes to find optimal settings
5. **Debugging**: Identify which chunks cause generator errors

## Benefits of Metadata Enrichment

When using `upload_enriched_chunks.py` with metadata:

1. **Better search ranking**: Chunks are ranked by relevance based on peripheral, content type, importance
2. **Filterable results**: Can filter by peripheral, register, content type, importance level
3. **No token overhead**: Metadata stored as attributes, doesn't consume chunk tokens
4. **Improved context**: LLM knows what type of content it's reading (table, description, example)
5. **Expected accuracy gain**: +4-12% based on testing with AFIO peripheral

**Metadata Fields:**
- **Identifiers**: chunk_id, page, datasheet
- **Content**: peripheral, content_type (register_table, overview, example, etc.)
- **Quality**: importance (critical, high, medium, low)
- **Registers**: primary_register, registers list, num_registers
- **Features**: has_tables, has_code, has_diagrams
- **Semantic**: keywords, section, token_count

## Chunk ID Format

```
{datasheet}_p{page:03d}_c{chunk:02d}.txt
```

Examples:
- `rm0041_p001_c01.txt` - Datasheet rm0041, page 1, chunk 1
- `rm0041_p127_c03.txt` - Datasheet rm0041, page 127, chunk 3

## Format Comparison: Text vs Markdown

### Plain Text Format (--format text)

**Pros:**
- ✅ Faster extraction (~2-3x faster than markdown)
- ✅ Smaller file sizes
- ✅ Bit descriptions preserved well

**Cons:**
- ❌ Tables completely broken (each cell on separate line)
- ❌ No table structure preserved
- ❌ Hard for LLM to parse register maps

**Example output (register table):**
```
Table 48. GPIO register map and reset values
Offset
Register
31
30
29
CNF
7
[1:0]
MODE
7
[1:0]
```

### Markdown Format (--format markdown)

**Pros:**
- ✅ Tables preserved with markdown syntax
- ✅ Better structure for LLM parsing
- ✅ Bit descriptions still readable
- ✅ Headers and formatting preserved

**Cons:**
- ❌ Slower extraction (~2-3x slower)
- ❌ Slightly larger file sizes
- ❌ May include more page metadata

**Example output (same register table):**
```markdown
**Table 48. GPIO register map and reset values**

|Offset|Register|31|30|29|28|27|26|25|24|...|
|---|---|---|---|---|---|---|---|---|---|---|
|0x00|GPIOx_CRL|CNF 7 [1:0]|MODE 7 [1:0]|CNF 6 [1:0]|MODE 6 [1:0]|...|
|Reset value|0|1|0|0|0|1|0|0|...|
```

### Recommendation

**For register-heavy datasheets (like rm0041):**
- Use **markdown format** - The table structure is critical for extracting register bit fields
- The extra processing time is worth it for better generator accuracy

**For text-heavy documents:**
- Use **text format** - Faster and simpler when tables aren't critical

## Recommended Settings

For generator analysis with rm0041:
- **Format**: `markdown` (better table preservation for register maps)
- **Chunk size**: 1200 tokens (prevents OpenAI re-chunking, tested in optimization)
- **Overlap**: 0 tokens (metadata provides context, overlap not needed)
- **Upload method**: `upload_enriched_chunks.py` (metadata attributes enabled)
- **Chunking strategy**: `static` with 1200 max tokens (prevents re-chunking)

**Complete workflow for best accuracy:**
```bash
# 1. Chunk with markdown
python preprocessing/chunk_pdf_to_files.py \
    devices/stm/rm0041/rm0041.pdf \
    devices/stm/rm0041/chunks/md \
    rm0041 \
    --format markdown \
    --max-tokens 1200

# 2. Enrich metadata
python preprocessing/enrich_chunk_metadata.py \
    devices/stm/rm0041/chunks/md \
    --extension .txt

# 3. Upload with metadata
python preprocessing/upload_enriched_chunks.py \
    devices/stm/rm0041/chunks/md \
    rm0041_md_enriched \
    rm0041 \
    --metadata-dir devices/stm/rm0041/chunks/md/metadata
```

For comparison testing:
- Create multiple vector stores with different chunk sizes (400, 800, 1200 tokens)
- Compare text vs markdown formats
- Compare with/without metadata enrichment
- Test which combination gives best generator accuracy

**Expected Results (based on AFIO testing):**
- Markdown chunks: 74.1% accuracy at 16 embeddings (vs 48.3% for text)
- Metadata enrichment: Expected +4-12% additional improvement
- Target: 78-85% accuracy with markdown + metadata + 16 embeddings
