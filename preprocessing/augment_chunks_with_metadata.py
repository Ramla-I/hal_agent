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

def load_metadata(metadata_dir: Path, chunk_id: str) -> Optional[Dict]:
    """Load metadata for a specific chunk."""
    metadata_file = metadata_dir / f"{chunk_id}_metadata.json"

    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load metadata for {chunk_id}: {e}")
        return None

def generate_metadata_header(metadata: Dict) -> str:
    """
    Generate a metadata header to prepend to chunk content.

    This creates a structured comment block that:
    - Is human-readable
    - Is semantically meaningful for search
    - Provides context to the LLM
    """
    if not metadata:
        return ""

    lines = ["<!-- CHUNK METADATA"]

    # Basic identifiers
    lines.append(f"Chunk ID: {metadata.get('chunk_id', 'unknown')}")
    lines.append(f"Page: {metadata.get('page', 'unknown')}")

    # Hierarchical context
    if metadata.get('chapter'):
        lines.append(f"Chapter: {metadata['chapter']}")
    if metadata.get('section'):
        lines.append(f"Section: {metadata['section']}")
    if metadata.get('subsection'):
        lines.append(f"Subsection: {metadata['subsection']}")

    # Peripheral and registers
    if metadata.get('peripheral'):
        lines.append(f"Peripheral: {metadata['peripheral']}")

    registers = metadata.get('registers_mentioned', [])
    if registers:
        # Limit to first 10 registers to avoid too long headers
        reg_list = ', '.join(registers[:10])
        if len(registers) > 10:
            reg_list += f" (and {len(registers) - 10} more)"
        lines.append(f"Registers: {reg_list}")

    # Content classification
    lines.append(f"Content Type: {metadata.get('chunk_type', 'general')}")
    lines.append(f"Importance: {metadata.get('importance', 'medium')}")

    # Features
    features = []
    if metadata.get('has_tables'):
        features.append('tables')
    if metadata.get('has_code_examples'):
        features.append('code examples')
    if metadata.get('has_diagrams'):
        features.append('diagrams')

    if features:
        lines.append(f"Contains: {', '.join(features)}")

    # Keywords
    keywords = metadata.get('keywords', [])
    if keywords:
        kw_list = ', '.join(keywords[:8])  # First 8 keywords
        lines.append(f"Keywords: {kw_list}")

    # Close comment
    lines.append("-->")
    lines.append("")  # Empty line separator

    return '\n'.join(lines)

def augment_chunk_content(chunk_content: str, metadata: Dict) -> str:
    """
    Augment chunk content with metadata header.

    Args:
        chunk_content: Original chunk text
        metadata: Metadata dictionary

    Returns:
        Augmented content with metadata header
    """
    header = generate_metadata_header(metadata)

    if not header:
        return chunk_content

    return header + chunk_content

def augment_chunk_directory(
    chunks_dir: Path,
    metadata_dir: Path,
    output_dir: Path,
    file_extension: str = '.txt'
) -> int:
    """
    Augment all chunks in a directory with metadata.

    Args:
        chunks_dir: Directory containing original chunks
        metadata_dir: Directory containing metadata JSON files
        output_dir: Directory to save augmented chunks
        file_extension: Extension of chunk files

    Returns:
        Number of chunks processed
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_files = sorted(chunks_dir.glob(f'*{file_extension}'))
    logger.info(f"Found {len(chunk_files)} chunk files")

    processed = 0

    for chunk_path in chunk_files:
        chunk_id = chunk_path.stem

        try:
            # Read original chunk
            with open(chunk_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Load metadata
            metadata = load_metadata(metadata_dir, chunk_id)

            if metadata:
                # Augment content
                augmented_content = augment_chunk_content(original_content, metadata)
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

    parser = argparse.ArgumentParser(description='Augment chunks with embedded metadata')
    parser.add_argument('chunks_dir', type=str, help='Directory containing original chunks')
    parser.add_argument('--metadata-dir', type=str, help='Directory containing metadata (default: chunks_dir/metadata)')
    parser.add_argument('--output-dir', type=str, required=True, help='Output directory for augmented chunks')
    parser.add_argument('--extension', type=str, default='.txt', help='Chunk file extension')

    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    metadata_dir = Path(args.metadata_dir) if args.metadata_dir else chunks_dir / 'metadata'
    output_dir = Path(args.output_dir)

    if not chunks_dir.exists():
        logger.error(f"Chunks directory not found: {chunks_dir}")
        return 1

    if not metadata_dir.exists():
        logger.error(f"Metadata directory not found: {metadata_dir}")
        logger.error("Please run enrich_chunk_metadata.py first")
        return 1

    logger.info("Starting chunk augmentation with metadata")
    logger.info(f"Chunks directory: {chunks_dir}")
    logger.info(f"Metadata directory: {metadata_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"File extension: {args.extension}")

    # Process chunks
    processed = augment_chunk_directory(
        chunks_dir,
        metadata_dir,
        output_dir,
        file_extension=args.extension
    )

    print("\n" + "="*80)
    print("CHUNK AUGMENTATION COMPLETE")
    print("="*80)
    print(f"\nProcessed: {processed} chunks")
    print(f"Output directory: {output_dir}")
    print("\nNext steps:")
    print("1. Review augmented chunks to verify metadata quality")
    print("2. Upload augmented chunks to vector store using scripts/upload_to_vector_store.py")
    print("="*80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
