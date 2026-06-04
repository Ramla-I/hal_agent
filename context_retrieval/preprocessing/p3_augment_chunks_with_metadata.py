#!/usr/bin/env python3
"""
Augment chunk content with embedded metadata.

Instead of trying to pass metadata separately (which OpenAI doesn't fully support),
we embed the metadata directly into the chunk content as structured headers.
This makes the metadata:
1. Searchable by semantic search
2. Visible to the LLM during generation
3. No API limitations

Example output:
```
<!-- CHUNK METADATA
Chunk ID: rm0041_p187_c01
Page: 187
Section: 10.11 ADC Registers
Peripheral: ADC
Registers: ADC_DR, ADC_JDR1
Type: register_table
Importance: critical
Keywords: data, conversion, injected
-->

[original chunk content]
```
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.utils import setup_logger

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Configurable field presets for augmentation experiments
# ---------------------------------------------------------------------------
# All available metadata fields that can be embedded.
ALL_FIELDS = [
    "chunk_id",
    "page",
    "chapter",
    "section",
    "subsection",
    "peripheral",
    "registers",       # registers_mentioned
    "fields",          # fields_mentioned
    "chunk_type",
    "importance",
    "completeness",
    "has_tables",
    "has_code",
    "has_diagrams",
    "keywords",
    "description",
    "token_count",
]

# Named presets for quick experimentation.
PRESETS: dict[str, list[str]] = {
    # Current default (matches prior behavior).
    "default": ["chapter", "section", "subsection", "peripheral", "registers", "has_tables", "has_code", "has_diagrams", "keywords"],
    # Minimal context (low token overhead).
    "minimal": ["section", "peripheral", "registers"],
    # Registers-focused (for retrieval debugging).
    "registers_only": ["peripheral", "registers"],
    # Full metadata (max information).
    "full": ALL_FIELDS.copy(),
    # No metadata (passthrough for baseline comparisons).
    "none": [],
}


def load_all_metadata(metadata_dir: Path) -> Dict[str, Dict]:
    """
    Load the combined metadata.json file.

    Returns a dict mapping chunk_id -> metadata dict.
    """
    metadata_file = metadata_dir / "metadata.json"
    if not metadata_file.exists():
        return {}

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load metadata.json: {e}")
        return {}


def load_metadata(metadata_dir: Path, chunk_id: str, all_metadata: Optional[Dict[str, Dict]] = None) -> Optional[Dict]:
    """
    Load metadata for a specific chunk.

    Args:
        metadata_dir: Directory containing metadata.json
        chunk_id: The chunk ID to look up
        all_metadata: Optional pre-loaded metadata dict (for efficiency)
    """
    # Use pre-loaded metadata if available
    if all_metadata is not None:
        return all_metadata.get(chunk_id)

    # Fall back to loading the combined file
    combined = load_all_metadata(metadata_dir)
    return combined.get(chunk_id)


def generate_metadata_header(
    metadata: Dict,
    include_fields: list[str] | None = None,
) -> str:
    """
    Generate a metadata header to prepend to chunk content.

    This creates a structured comment block that:
    - Is human-readable
    - Is semantically meaningful for search
    - Provides context to the LLM

    Args:
        metadata: Metadata dictionary from enrichment step.
        include_fields: Which fields to include (default: PRESETS["default"]).
    """
    if not metadata:
        return ""

    fields = set(include_fields if include_fields is not None else PRESETS["default"])

    lines = ["<!-- CHUNK METADATA"]

    # --- Basic identifiers ---
    if "chunk_id" in fields and metadata.get("chunk_id"):
        lines.append(f"Chunk ID: {metadata['chunk_id']}")
    if "page" in fields and metadata.get("page"):
        lines.append(f"Page: {metadata['page']}")

    # --- Hierarchical context ---
    if "chapter" in fields and metadata.get("chapter"):
        lines.append(f"Chapter: {metadata['chapter']}")
    if "section" in fields and metadata.get("section"):
        lines.append(f"Section: {metadata['section']}")
    if "subsection" in fields and metadata.get("subsection"):
        lines.append(f"Subsection: {metadata['subsection']}")

    # --- Peripheral and registers ---
    if "peripheral" in fields and metadata.get("peripheral"):
        lines.append(f"Peripheral: {metadata['peripheral']}")
    if "registers" in fields:
        registers = metadata.get("registers_mentioned", [])
        if registers:
            reg_list = ", ".join(registers[:10])
            if len(registers) > 10:
                reg_list += f" (and {len(registers) - 10} more)"
            lines.append(f"Registers: {reg_list}")
    if "fields" in fields:
        fld = metadata.get("fields_mentioned", [])
        if fld:
            lines.append(f"Fields: {', '.join(fld[:10])}")

    # --- Content classification ---
    if "chunk_type" in fields and metadata.get("chunk_type"):
        lines.append(f"Content Type: {metadata['chunk_type']}")
    if "importance" in fields and metadata.get("importance"):
        lines.append(f"Importance: {metadata['importance']}")
    if "completeness" in fields and metadata.get("completeness"):
        lines.append(f"Completeness: {metadata['completeness']}")

    # --- Features ---
    if any(f in fields for f in ("has_tables", "has_code", "has_diagrams")):
        features = []
        if "has_tables" in fields and metadata.get("has_tables"):
            features.append("tables")
        if "has_code" in fields and metadata.get("has_code_examples"):
            features.append("code examples")
        if "has_diagrams" in fields and metadata.get("has_diagrams"):
            features.append("diagrams")
        if features:
            lines.append(f"Contains: {', '.join(features)}")

    # --- Semantic ---
    if "keywords" in fields:
        keywords = metadata.get("keywords", [])
        if keywords:
            lines.append(f"Keywords: {', '.join(keywords[:8])}")
    if "description" in fields and metadata.get("description"):
        lines.append(f"Description: {metadata['description']}")

    # --- Token count ---
    if "token_count" in fields and metadata.get("token_count"):
        lines.append(f"Tokens: {metadata['token_count']}")

    # Close comment
    lines.append("-->")
    lines.append("")  # Empty line separator

    # If only the opening/closing lines, return empty.
    if len(lines) <= 3:
        return ""

    return '\n'.join(lines)

def augment_chunk_content(
    chunk_content: str,
    metadata: Dict,
    include_fields: list[str] | None = None,
) -> str:
    """
    Augment chunk content with metadata header.

    Args:
        chunk_content: Original chunk text
        metadata: Metadata dictionary
        include_fields: Which fields to include (default: PRESETS["default"]).

    Returns:
        Augmented content with metadata header
    """
    header = generate_metadata_header(metadata, include_fields=include_fields)

    if not header:
        return chunk_content

    return header + chunk_content


def augment_chunk_directory(
    chunks_dir: Path,
    metadata_dir: Path,
    output_dir: Path,
    file_extension: str = '.txt',
    include_fields: list[str] | None = None,
) -> int:
    """
    Augment all chunks in a directory with metadata.

    Args:
        chunks_dir: Directory containing original chunks
        metadata_dir: Directory containing metadata.json
        output_dir: Directory to save augmented chunks
        file_extension: Extension of chunk files
        include_fields: Which metadata fields to include.

    Returns:
        Number of chunks processed
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_files = sorted(chunks_dir.glob(f'*{file_extension}'))
    logger.info(f"Found {len(chunk_files)} chunk files")

    # Load all metadata once for efficiency
    all_metadata = load_all_metadata(metadata_dir)
    if not all_metadata:
        logger.warning(f"No metadata.json found in {metadata_dir}")

    processed = 0

    for chunk_path in chunk_files:
        chunk_id = chunk_path.stem

        try:
            # Read original chunk
            with open(chunk_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Load metadata (using pre-loaded dict)
            metadata = load_metadata(metadata_dir, chunk_id, all_metadata=all_metadata)

            if metadata:
                augmented_content = augment_chunk_content(original_content, metadata, include_fields=include_fields)
            else:
                logger.warning(f"No metadata found for {chunk_id}, using original content")
                augmented_content = original_content

            # Save augmented chunk
            output_path = output_dir / chunk_path.name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(augmented_content)

            processed += 1

            if processed % 100 == 0:
                logger.info(f"Processed {processed}/{len(chunk_files)} chunks")

        except Exception as e:
            logger.error(f"Error processing {chunk_path.name}: {e}")
            continue

    logger.info(f"Successfully augmented {processed} chunks")
    logger.info(f"Output directory: {output_dir}")

    return processed

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Augment chunks with embedded metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Presets and fields
------------------
Use --list-fields to see all available fields and presets.

Examples:
  # Default augmentation
  python p3_augment_chunks_with_metadata.py chunks/ --output-dir out/

  # Minimal augmentation (less token overhead)
  python p3_augment_chunks_with_metadata.py chunks/ --output-dir out/ --preset minimal

  # Register-only augmentation for retrieval experiments
  python p3_augment_chunks_with_metadata.py chunks/ --output-dir out/ --preset registers_only

  # Full metadata for debugging/analysis
  python p3_augment_chunks_with_metadata.py chunks/ --output-dir out/ --preset full

  # Default preset but also include chunk_type
  python p3_augment_chunks_with_metadata.py chunks/ --output-dir out/ --include chunk_type

  # Default preset but exclude keywords
  python p3_augment_chunks_with_metadata.py chunks/ --output-dir out/ --exclude keywords
        """,
    )
    parser.add_argument('chunks_dir', type=str, help='Directory containing original chunks')
    parser.add_argument('--metadata-dir', type=str, help='Directory containing metadata.json (default: chunks_dir)')
    parser.add_argument('--output-dir', type=str, required=True, help='Output directory for augmented chunks')
    parser.add_argument('--extension', type=str, default='.txt', help='Chunk file extension')
    parser.add_argument(
        '--preset',
        choices=list(PRESETS.keys()),
        default='default',
        help='Named preset for which metadata fields to include (default: default)',
    )
    parser.add_argument(
        '--include',
        nargs='*',
        default=None,
        help='Additional fields to include (on top of preset)',
    )
    parser.add_argument(
        '--exclude',
        nargs='*',
        default=None,
        help='Fields to exclude from preset',
    )
    parser.add_argument(
        '--list-fields',
        action='store_true',
        help='List all available fields and presets, then exit',
    )

    args = parser.parse_args()

    # Handle --list-fields
    if args.list_fields:
        print("Available fields:")
        for f in ALL_FIELDS:
            print(f"  - {f}")
        print("\nPresets:")
        for name, fields in PRESETS.items():
            print(f"  {name}: {', '.join(fields) if fields else '(empty)'}")
        return 0

    chunks_dir = Path(args.chunks_dir)
    # Metadata is now stored directly in chunks_dir as metadata.json
    metadata_dir = Path(args.metadata_dir) if args.metadata_dir else chunks_dir
    output_dir = Path(args.output_dir)

    # Build final field list from preset +/- include/exclude.
    include_fields = list(PRESETS[args.preset])
    if args.include:
        for f in args.include:
            if f not in include_fields:
                include_fields.append(f)
    if args.exclude:
        include_fields = [f for f in include_fields if f not in args.exclude]

    if not chunks_dir.exists():
        logger.error(f"Chunks directory not found: {chunks_dir}")
        return 1

    metadata_file = metadata_dir / "metadata.json"
    if not metadata_file.exists():
        logger.error(f"Metadata file not found: {metadata_file}")
        logger.error("Please run p2_enrich_chunk_metadata.py first")
        return 1

    logger.info("Starting chunk augmentation with metadata")
    logger.info(f"Chunks directory: {chunks_dir}")
    logger.info(f"Metadata directory: {metadata_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"File extension: {args.extension}")
    logger.info(f"Preset: {args.preset}")
    logger.info(f"Include fields: {include_fields}")

    # Process chunks
    processed = augment_chunk_directory(
        chunks_dir,
        metadata_dir,
        output_dir,
        file_extension=args.extension,
        include_fields=include_fields,
    )

    print("\n" + "="*80)
    print("CHUNK AUGMENTATION COMPLETE")
    print("="*80)
    print(f"\nProcessed: {processed} chunks")
    print(f"Output directory: {output_dir}")
    print(f"Preset: {args.preset}, fields: {include_fields}")
    print("\nNext steps:")
    print("1. Review augmented chunks to verify metadata quality")
    print("2. Upload augmented chunks via preprocessing/pipeline.py (which calls vector_store_uploader)")
    print("="*80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
