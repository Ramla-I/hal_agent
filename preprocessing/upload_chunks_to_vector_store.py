"""
Upload chunked text files to OpenAI vector store with metadata.

Usage:
    python upload_chunks_to_vector_store.py <chunks_dir> <vector_store_name> <datasheet_name> [options]

Examples:
    # Upload with auto chunking (recommended for pre-chunked files)
    python upload_chunks_to_vector_store.py chunks/rm0041 rm0041_chunked rm0041

    # Upload with static chunking strategy
    python upload_chunks_to_vector_store.py chunks/rm0041 rm0041_chunked rm0041 \
        --chunking-strategy static --max-chunk-tokens 1200 --chunk-overlap-tokens 200

Note:
    Since we've already pre-chunked the files, using --chunking-strategy=static with a large
    max-chunk-tokens (e.g., 1200) is recommended to prevent OpenAI from re-chunking our
    carefully created chunks. The 'auto' strategy uses 800 tokens with 400 overlap, which
    would re-chunk our files.
"""

import argparse
import os
import sys
import csv
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm


def load_chunk_metadata(chunks_dir: str, datasheet_name: str) -> dict[str, dict]:
    """
    Load chunk metadata from CSV.

    Returns:
        Dictionary mapping chunk_id to metadata
    """
    metadata_path = os.path.join(chunks_dir, f"{datasheet_name}_chunks_metadata.csv")

    if not os.path.exists(metadata_path):
        print(f"Warning: Metadata file not found: {metadata_path}")
        return {}

    metadata_by_id = {}
    with open(metadata_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            chunk_id = row['chunk_id']
            metadata_by_id[chunk_id] = row

    return metadata_by_id


def upload_file_to_openai(client: OpenAI, file_path: str) -> str:
    """
    Upload a single file to OpenAI.

    Returns:
        File ID
    """
    with open(file_path, "rb") as f:
        result = client.files.create(
            file=f,
            purpose="assistants"
        )
    return result.id


def create_vector_store_with_chunks(
    client: OpenAI,
    chunks_dir: str,
    vector_store_name: str,
    datasheet_name: str,
    chunking_strategy_type: str = "auto",
    max_chunk_size_tokens: int = None,
    chunk_overlap_tokens: int = None
) -> tuple[str, list[dict]]:
    """
    Create vector store and upload all chunk files with metadata.

    Args:
        client: OpenAI client
        chunks_dir: Directory containing chunk files
        vector_store_name: Name for the vector store
        datasheet_name: Name of the datasheet (for metadata file)
        chunking_strategy_type: "auto" or "static" (OpenAI's re-chunking strategy)
        max_chunk_size_tokens: Max tokens per chunk for OpenAI re-chunking (100-4096)
        chunk_overlap_tokens: Overlap tokens for OpenAI re-chunking

    Returns:
        Tuple of (vector_store_id, list of file info dicts)
    """
    # Load chunk metadata
    metadata_by_id = load_chunk_metadata(chunks_dir, datasheet_name)

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

    # Prepare chunking strategy for OpenAI
    # IMPORTANT: Use a chunk size LARGER than our pre-chunked files to prevent re-chunking
    # Our chunks are max 800 tokens, so we use a larger size to keep them intact
    chunking_strategy = {"type": chunking_strategy_type}
    if chunking_strategy_type == "static":
        if max_chunk_size_tokens:
            chunking_strategy["static"] = {
                "max_chunk_size_tokens": max_chunk_size_tokens,
                "chunk_overlap_tokens": chunk_overlap_tokens or 0  # No overlap needed (we already have it)
            }
        else:
            # Default: Use 1200 tokens (larger than our 800 max) to prevent splitting
            chunking_strategy["static"] = {
                "max_chunk_size_tokens": 1200,  # Larger than our 800-token chunks
                "chunk_overlap_tokens": 0  # No overlap (we already built it in)
            }
    else:
        # "auto" mode uses OpenAI defaults which might split our chunks
        # This strategy currently uses a max_chunk_size_tokens of 800 and chunk_overlap_tokens of 400
        # Recommend using "static" instead for pre-chunked files
        print("⚠️  WARNING: 'auto' mode may re-chunk your files with OpenAI's defaults (800 tokens, 400 overlap)")
        print("    Consider using --chunking-strategy static --max-chunk-tokens 1200 instead")

    print(f"Chunking strategy: {chunking_strategy}")

    # Upload files with metadata
    print(f"\nUploading {len(chunk_files)} files...")
    file_infos = []

    for chunk_file in tqdm(chunk_files, desc="Uploading chunks"):
        chunk_id = chunk_file.stem  # Filename without .txt extension

        # Upload file to OpenAI
        file_id = upload_file_to_openai(client, str(chunk_file))

        # Get metadata for this chunk
        chunk_metadata = metadata_by_id.get(chunk_id, {})

        # Prepare metadata attributes (OpenAI supports up to 16 key-value pairs)
        attributes = {
            'chunk_id': chunk_id,
            'datasheet': chunk_metadata.get('datasheet', datasheet_name),
            'page_number': chunk_metadata.get('page_number', ''),
            'chunk_index': chunk_metadata.get('chunk_index', ''),
            'token_count': chunk_metadata.get('token_count', ''),
        }

        # Add to vector store with chunking strategy
        # Note: Since we already chunked the files, we typically use "auto" or very small chunks
        # to prevent OpenAI from re-chunking our carefully created chunks
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
            **chunk_metadata
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
        description="Upload chunked files to OpenAI vector store"
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
        "--output",
        help="Path to save upload summary CSV (default: <chunks_dir>/upload_summary.csv)"
    )
    parser.add_argument(
        "--chunking-strategy",
        choices=["auto", "static"],
        default="static",
        help="OpenAI's chunking strategy: 'static' (recommended - prevents re-chunking) or 'auto' (uses 800 tokens, 400 overlap) (default: static)"
    )
    parser.add_argument(
        "--max-chunk-tokens",
        type=int,
        default=1200,
        help="Max tokens per chunk for OpenAI (100-4096). Set LARGER than your chunks to prevent splitting (default: 1200)"
    )
    parser.add_argument(
        "--chunk-overlap-tokens",
        type=int,
        default=0,
        help="Overlap tokens for OpenAI. Use 0 if you already have overlap in your chunks (default: 0)"
    )

    args = parser.parse_args()

    # Validate directory
    if not os.path.exists(args.chunks_dir):
        print(f"Error: Chunks directory not found: {args.chunks_dir}")
        sys.exit(1)

    # Validate chunking parameters
    if args.chunking_strategy == "static":
        if args.max_chunk_tokens and (args.max_chunk_tokens < 100 or args.max_chunk_tokens > 4096):
            print("Error: --max-chunk-tokens must be between 100 and 4096")
            sys.exit(1)
        if args.chunk_overlap_tokens and args.max_chunk_tokens:
            if args.chunk_overlap_tokens > args.max_chunk_tokens / 2:
                print("Error: --chunk-overlap-tokens cannot exceed max-chunk-tokens / 2")
                sys.exit(1)

    # Create OpenAI client
    client = OpenAI()

    # Upload chunks
    vector_store_id, file_infos = create_vector_store_with_chunks(
        client,
        args.chunks_dir,
        args.vector_store_name,
        args.datasheet_name,
        args.chunking_strategy,
        args.max_chunk_tokens,
        args.chunk_overlap_tokens
    )

    # Save summary
    output_path = args.output or os.path.join(args.chunks_dir, "upload_summary.csv")
    save_upload_summary(vector_store_id, file_infos, output_path)
    print(f"\nUpload summary saved to: {output_path}")

    # Save vector store ID to file
    vs_id_path = os.path.join(args.chunks_dir, "vector_store_id.txt")
    with open(vs_id_path, 'w') as f:
        f.write(f"vector_store_id: {vector_store_id}\n")
        f.write(f"datasheet: {args.datasheet_name}\n")
        f.write(f"vector_store_name: {args.vector_store_name}\n")
        f.write(f"total_files: {len(file_infos)}\n")
    print(f"Vector store ID saved to: {vs_id_path}")

    print(f"\n{'='*60}")
    print(f"Vector Store ID: {vector_store_id}")
    print(f"Total Files: {len(file_infos)}")
    print(f"{'='*60}")
    print(f"\nAdd this to your config:")
    print(f'  vs_id = "{vector_store_id}"')


if __name__ == "__main__":
    main()
