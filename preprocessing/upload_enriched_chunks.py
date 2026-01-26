"""
Upload chunked files to OpenAI vector store with enriched metadata attributes.

This script extends the base upload functionality to use rich metadata generated
by scripts/enrich_chunk_metadata.py.

Usage:
    python upload_enriched_chunks.py <chunks_dir> <vector_store_name> <datasheet_name> [options]

Example:
    python upload_enriched_chunks.py \
        devices/stm/rm0041/chunks/md \
        rm0041_md_enriched \
        rm0041 \
        --metadata-dir devices/stm/rm0041/chunks/md/metadata
"""

import argparse
import os
import sys
import csv
import json
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm


def load_enriched_metadata(metadata_dir: str, chunk_id: str) -> dict:
    """
    Load enriched metadata for a specific chunk.

    Args:
        metadata_dir: Directory containing metadata JSON files
        chunk_id: Chunk identifier (e.g., 'rm0041_p187_c01')

    Returns:
        Dictionary with metadata, or empty dict if not found
    """
    metadata_file = os.path.join(metadata_dir, f"{chunk_id}_metadata.json")

    if not os.path.exists(metadata_file):
        return {}

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load metadata for {chunk_id}: {e}")
        return {}


def prepare_attributes_from_metadata(metadata: dict, chunk_id: str, datasheet_name: str) -> dict:
    """
    Convert enriched metadata to OpenAI attributes format.

    OpenAI supports up to 16 key-value pairs, all values must be strings.
    We select the most valuable metadata fields.

    Args:
        metadata: Full metadata dictionary
        chunk_id: Chunk identifier
        datasheet_name: Datasheet name

    Returns:
        Dictionary of attributes for OpenAI
    """
    attributes = {
        'chunk_id': chunk_id,
        'datasheet': datasheet_name,
    }

    if not metadata:
        return attributes

    # Page information
    if 'page' in metadata:
        attributes['page'] = str(metadata['page'])

    # Hierarchical context (truncate if too long)
    if metadata.get('section'):
        attributes['section'] = str(metadata['section'])[:100]

    # Peripheral and content type
    if metadata.get('peripheral'):
        attributes['peripheral'] = str(metadata['peripheral'])

    attributes['content_type'] = str(metadata.get('chunk_type', 'general'))
    attributes['importance'] = str(metadata.get('importance', 'medium'))

    # Register information
    registers = metadata.get('registers_mentioned', [])
    if registers:
        attributes['num_registers'] = str(len(registers))
        # Store first register for quick filtering
        attributes['primary_register'] = str(registers[0])
        # Store up to 5 registers as comma-separated (within char limits)
        reg_list = ','.join(registers[:5])
        if len(reg_list) <= 100:
            attributes['registers'] = reg_list

    # Content features as boolean flags
    if metadata.get('has_tables'):
        attributes['has_tables'] = 'true'
    if metadata.get('has_code_examples'):
        attributes['has_code'] = 'true'
    if metadata.get('has_diagrams'):
        attributes['has_diagrams'] = 'true'

    # Keywords (first 3-5, comma-separated)
    keywords = metadata.get('keywords', [])
    if keywords:
        kw_str = ','.join(keywords[:5])
        if len(kw_str) <= 100:
            attributes['keywords'] = kw_str

    # Token count
    if 'token_count' in metadata:
        attributes['tokens'] = str(metadata['token_count'])

    return attributes


def upload_file_to_openai(client: OpenAI, file_path: str) -> str:
    """Upload a single file to OpenAI."""
    with open(file_path, "rb") as f:
        result = client.files.create(
            file=f,
            purpose="assistants"
        )
    return result.id


def create_vector_store_with_enriched_chunks(
    client: OpenAI,
    chunks_dir: str,
    metadata_dir: str,
    vector_store_name: str,
    datasheet_name: str,
    chunking_strategy_type: str = "static",
    max_chunk_size_tokens: int = 1200,
    chunk_overlap_tokens: int = 0
) -> tuple[str, list[dict]]:
    """
    Create vector store and upload all chunk files with enriched metadata.

    Args:
        client: OpenAI client
        chunks_dir: Directory containing chunk files
        metadata_dir: Directory containing enriched metadata JSON files
        vector_store_name: Name for the vector store
        datasheet_name: Name of the datasheet
        chunking_strategy_type: "auto" or "static"
        max_chunk_size_tokens: Max tokens per chunk for OpenAI
        chunk_overlap_tokens: Overlap tokens for OpenAI

    Returns:
        Tuple of (vector_store_id, list of file info dicts)
    """
    # Find all chunk files
    chunk_files = sorted(Path(chunks_dir).glob(f"{datasheet_name}_p*_c*.txt"))

    if not chunk_files:
        print(f"Error: No chunk files found in {chunks_dir}")
        sys.exit(1)

    print(f"Found {len(chunk_files)} chunk files")

    # Create vector store
    print(f"\nCreating vector store: {vector_store_name}")
    vector_store = client.vector_stores.create(name=vector_store_name)
    print(f"Vector store ID: {vector_store.id}")

    # Prepare chunking strategy
    chunking_strategy = {"type": chunking_strategy_type}
    if chunking_strategy_type == "static":
        chunking_strategy["static"] = {
            "max_chunk_size_tokens": max_chunk_size_tokens,
            "chunk_overlap_tokens": chunk_overlap_tokens
        }

    print(f"Chunking strategy: {chunking_strategy}")

    # Upload files with enriched metadata
    print(f"\nUploading {len(chunk_files)} files with enriched metadata...")
    file_infos = []

    for chunk_file in tqdm(chunk_files, desc="Uploading chunks"):
        chunk_id = chunk_file.stem

        # Upload file to OpenAI
        file_id = upload_file_to_openai(client, str(chunk_file))

        # Load enriched metadata
        metadata = load_enriched_metadata(metadata_dir, chunk_id)

        # Convert to attributes
        attributes = prepare_attributes_from_metadata(metadata, chunk_id, datasheet_name)

        # Add to vector store with metadata attributes
        result = client.vector_stores.files.create(
            vector_store_id=vector_store.id,
            file_id=file_id,
            chunking_strategy=chunking_strategy,
            attributes=attributes
        )

        file_infos.append({
            'chunk_id': chunk_id,
            'file_id': file_id,
            'file_path': str(chunk_file),
            'status': result.status,
            'peripheral': metadata.get('peripheral', ''),
            'content_type': metadata.get('chunk_type', ''),
            'importance': metadata.get('importance', ''),
            'num_registers': len(metadata.get('registers_mentioned', [])),
            'page': metadata.get('page', ''),
        })

    print(f"\n✓ Uploaded {len(file_infos)} files to vector store {vector_store.id}")

    return vector_store.id, file_infos


def save_upload_summary(
    vector_store_id: str,
    file_infos: list[dict],
    output_path: str
):
    """Save upload summary to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        if file_infos:
            writer = csv.DictWriter(f, fieldnames=file_infos[0].keys())
            writer.writeheader()
            writer.writerows(file_infos)


def main():
    parser = argparse.ArgumentParser(
        description="Upload chunks with enriched metadata to OpenAI vector store"
    )
    parser.add_argument(
        "chunks_dir",
        help="Directory containing chunk files"
    )
    parser.add_argument(
        "vector_store_name",
        help="Name for the vector store"
    )
    parser.add_argument(
        "datasheet_name",
        help="Name of the datasheet (e.g., 'rm0041')"
    )
    parser.add_argument(
        "--metadata-dir",
        help="Directory containing enriched metadata JSON files (default: <chunks_dir>/metadata)"
    )
    parser.add_argument(
        "--output",
        help="Path to save upload summary CSV (default: <chunks_dir>/upload_summary_enriched.csv)"
    )
    parser.add_argument(
        "--chunking-strategy",
        choices=["auto", "static"],
        default="static",
        help="OpenAI's chunking strategy (default: static)"
    )
    parser.add_argument(
        "--max-chunk-tokens",
        type=int,
        default=1200,
        help="Max tokens per chunk for OpenAI (default: 1200)"
    )
    parser.add_argument(
        "--chunk-overlap-tokens",
        type=int,
        default=0,
        help="Overlap tokens for OpenAI (default: 0)"
    )

    args = parser.parse_args()

    # Validate directories
    if not os.path.exists(args.chunks_dir):
        print(f"Error: Chunks directory not found: {args.chunks_dir}")
        sys.exit(1)

    metadata_dir = args.metadata_dir or os.path.join(args.chunks_dir, "metadata")
    if not os.path.exists(metadata_dir):
        print(f"Error: Metadata directory not found: {metadata_dir}")
        print("Please run scripts/enrich_chunk_metadata.py first")
        sys.exit(1)

    # Check for all_metadata.json to ensure metadata was generated
    all_metadata_file = os.path.join(metadata_dir, "all_metadata.json")
    if not os.path.exists(all_metadata_file):
        print(f"Error: all_metadata.json not found in {metadata_dir}")
        print("Please run scripts/enrich_chunk_metadata.py first")
        sys.exit(1)

    # Create OpenAI client
    client = OpenAI()

    # Upload chunks with enriched metadata
    vector_store_id, file_infos = create_vector_store_with_enriched_chunks(
        client,
        args.chunks_dir,
        metadata_dir,
        args.vector_store_name,
        args.datasheet_name,
        args.chunking_strategy,
        args.max_chunk_tokens,
        args.chunk_overlap_tokens
    )

    # Save summary
    output_path = args.output or os.path.join(args.chunks_dir, "upload_summary_enriched.csv")
    save_upload_summary(vector_store_id, file_infos, output_path)
    print(f"\nUpload summary saved to: {output_path}")

    # Save vector store ID to file
    vs_id_path = os.path.join(args.chunks_dir, "vector_store_id_enriched.txt")
    with open(vs_id_path, 'w') as f:
        f.write(f"vector_store_id: {vector_store_id}\n")
        f.write(f"datasheet: {args.datasheet_name}\n")
        f.write(f"vector_store_name: {args.vector_store_name}\n")
        f.write(f"total_files: {len(file_infos)}\n")
        f.write(f"metadata_enabled: true\n")
    print(f"Vector store ID saved to: {vs_id_path}")

    print(f"\n{'='*60}")
    print(f"Vector Store ID: {vector_store_id}")
    print(f"Total Files: {len(file_infos)}")
    print(f"Metadata: Enriched attributes enabled")
    print(f"{'='*60}")
    print(f"\nAdd this to your config:")
    print(f'  vs_id_md_enriched = "{vector_store_id}"')


if __name__ == "__main__":
    main()
