"""
Shared OpenAI vector store upload utilities for chunked datasheets.

This module consolidates the logic that previously lived in:
- `preprocessing/p4_upload_chunks.py` (CLI)

It provides two public helpers that keep the existing naming stable:
- `create_vector_store_with_chunks(...)`
- `create_vector_store_with_enriched_chunks(...)`
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Optional


def _upload_file_to_openai(client, file_path: str) -> str:
    """Upload a single file to OpenAI and return the file ID."""
    with open(file_path, "rb") as f:
        result = client.files.create(file=f, purpose="assistants")
    return result.id


def _load_chunk_metadata_csv(chunks_dir: str, datasheet_name: str = None) -> dict[str, dict]:
    """
    Load chunk metadata from `chunks_index.csv` if present.

    Returns a dict mapping chunk_id -> metadata row (strings).

    Note: datasheet_name is kept for backward compatibility but no longer used.
    """
    metadata_path = os.path.join(chunks_dir, "chunks_index.csv")
    if not os.path.exists(metadata_path):
        return {}

    metadata_by_id: dict[str, dict] = {}
    with open(metadata_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chunk_id = row.get("chunk_id")
            if chunk_id:
                metadata_by_id[chunk_id] = row
    return metadata_by_id


def _load_all_enriched_metadata(metadata_dir: str) -> dict[str, dict]:
    """
    Load the combined metadata.json file.

    Returns a dict mapping chunk_id -> metadata dict.
    """
    metadata_file = os.path.join(metadata_dir, "metadata.json")
    if not os.path.exists(metadata_file):
        return {}
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _prepare_attributes_basic(
    chunk_id: str,
    datasheet_name: str,
    chunk_metadata_row: Optional[dict] = None,
) -> dict:
    """
    Prepare a small set of attributes for OpenAI.

    OpenAI supports up to 16 key-value pairs; all values must be strings.
    """
    row = chunk_metadata_row or {}
    attributes = {
        "chunk_id": chunk_id,
        "datasheet": str(row.get("datasheet", datasheet_name) or datasheet_name),
    }

    # Keep these keys aligned with prior scripts where possible.
    if row.get("page_number") is not None:
        attributes["page_number"] = str(row.get("page_number", ""))
    if row.get("chunk_index") is not None:
        attributes["chunk_index"] = str(row.get("chunk_index", ""))
    if row.get("token_count") is not None:
        attributes["token_count"] = str(row.get("token_count", ""))

    return attributes


def _prepare_attributes_enriched(metadata: dict, chunk_id: str, datasheet_name: str) -> dict:
    """
    Convert enriched metadata JSON to OpenAI attributes format.

    OpenAI supports up to 16 key-value pairs; all values must be strings.
    """
    attributes = {"chunk_id": chunk_id, "datasheet": datasheet_name}
    if not metadata:
        return attributes

    if "page" in metadata:
        attributes["page"] = str(metadata["page"])

    if metadata.get("section"):
        attributes["section"] = str(metadata["section"])[:100]

    if metadata.get("peripheral"):
        attributes["peripheral"] = str(metadata["peripheral"])

    attributes["content_type"] = str(metadata.get("chunk_type", "general"))
    attributes["importance"] = str(metadata.get("importance", "medium"))

    registers = metadata.get("registers_mentioned", []) or []
    if registers:
        attributes["num_registers"] = str(len(registers))
        attributes["primary_register"] = str(registers[0])
        reg_list = ",".join(str(r) for r in registers[:5])
        if len(reg_list) <= 100:
            attributes["registers"] = reg_list

    if metadata.get("has_tables"):
        attributes["has_tables"] = "true"
    if metadata.get("has_code_examples"):
        attributes["has_code"] = "true"
    if metadata.get("has_diagrams"):
        attributes["has_diagrams"] = "true"

    keywords = metadata.get("keywords", []) or []
    if keywords:
        kw_str = ",".join(str(k) for k in keywords[:5])
        if len(kw_str) <= 100:
            attributes["keywords"] = kw_str

    if "token_count" in metadata:
        attributes["tokens"] = str(metadata["token_count"])

    return attributes


def _create_vector_store_with_chunk_files(
    client,
    chunk_files: list[Path],
    *,
    vector_store_name: str,
    chunking_strategy_type: str,
    max_chunk_size_tokens: int,
    chunk_overlap_tokens: int,
) -> tuple[str, dict]:
    """Create vector store and return (vector_store_id, chunking_strategy_dict)."""
    vector_store = client.vector_stores.create(name=vector_store_name)

    chunking_strategy: dict = {"type": chunking_strategy_type}
    if chunking_strategy_type == "static":
        chunking_strategy["static"] = {
            "max_chunk_size_tokens": max_chunk_size_tokens,
            "chunk_overlap_tokens": chunk_overlap_tokens,
        }

    return vector_store.id, chunking_strategy


def _discover_chunk_files(
    chunks_dir: str,
    datasheet_name: str,
    *,
    file_extension: str,
) -> list[Path]:
    chunks_path = Path(chunks_dir)
    return sorted(chunks_path.glob(f"{datasheet_name}_p*_c*{file_extension}"))


def create_vector_store_with_chunks(
    client,
    chunks_dir: str,
    vector_store_name: str,
    datasheet_name: str,
    chunking_strategy_type: str = "static",
    max_chunk_size_tokens: int = 1200,
    chunk_overlap_tokens: int = 0,
    *,
    file_extension: str = ".txt",
) -> tuple[str, list[dict]]:
    """
    Create a vector store and upload pre-chunked files with basic attributes.
    """
    chunk_files = _discover_chunk_files(chunks_dir, datasheet_name, file_extension=file_extension)
    if not chunk_files:
        raise FileNotFoundError(f"No chunk files found in {chunks_dir} for datasheet '{datasheet_name}'")

    metadata_by_id = _load_chunk_metadata_csv(chunks_dir, datasheet_name)

    vector_store_id, chunking_strategy = _create_vector_store_with_chunk_files(
        client,
        chunk_files,
        vector_store_name=vector_store_name,
        chunking_strategy_type=chunking_strategy_type,
        max_chunk_size_tokens=max_chunk_size_tokens,
        chunk_overlap_tokens=chunk_overlap_tokens,
    )

    file_infos: list[dict] = []
    for chunk_file in chunk_files:
        chunk_id = chunk_file.stem
        file_id = _upload_file_to_openai(client, str(chunk_file))

        attributes = _prepare_attributes_basic(
            chunk_id=chunk_id,
            datasheet_name=datasheet_name,
            chunk_metadata_row=metadata_by_id.get(chunk_id),
        )

        result = client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
            chunking_strategy=chunking_strategy,
            attributes=attributes,
        )

        file_infos.append(
            {
                "chunk_id": chunk_id,
                "file_id": file_id,
                "file_path": str(chunk_file),
                "status": getattr(result, "status", ""),
                **(metadata_by_id.get(chunk_id) or {}),
            }
        )

    return vector_store_id, file_infos


def create_vector_store_with_enriched_chunks(
    client,
    chunks_dir: str,
    metadata_dir: str,
    vector_store_name: str,
    datasheet_name: str,
    chunking_strategy_type: str = "static",
    max_chunk_size_tokens: int = 1200,
    chunk_overlap_tokens: int = 0,
    *,
    file_extension: str = ".txt",
) -> tuple[str, list[dict]]:
    """
    Create a vector store and upload pre-chunked files with enriched attributes.
    """
    chunk_files = _discover_chunk_files(chunks_dir, datasheet_name, file_extension=file_extension)
    if not chunk_files:
        raise FileNotFoundError(f"No chunk files found in {chunks_dir} for datasheet '{datasheet_name}'")

    # Load all enriched metadata once (from combined metadata.json)
    all_metadata = _load_all_enriched_metadata(metadata_dir)

    vector_store_id, chunking_strategy = _create_vector_store_with_chunk_files(
        client,
        chunk_files,
        vector_store_name=vector_store_name,
        chunking_strategy_type=chunking_strategy_type,
        max_chunk_size_tokens=max_chunk_size_tokens,
        chunk_overlap_tokens=chunk_overlap_tokens,
    )

    file_infos: list[dict] = []
    for chunk_file in chunk_files:
        chunk_id = chunk_file.stem
        file_id = _upload_file_to_openai(client, str(chunk_file))

        metadata = all_metadata.get(chunk_id, {})
        attributes = _prepare_attributes_enriched(metadata, chunk_id, datasheet_name)

        result = client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
            chunking_strategy=chunking_strategy,
            attributes=attributes,
        )

        file_infos.append(
            {
                "chunk_id": chunk_id,
                "file_id": file_id,
                "file_path": str(chunk_file),
                "status": getattr(result, "status", ""),
                "peripheral": metadata.get("peripheral", ""),
                "content_type": metadata.get("chunk_type", ""),
                "importance": metadata.get("importance", ""),
                "num_registers": len(metadata.get("registers_mentioned", []) or []),
                "page": metadata.get("page", ""),
            }
        )

    return vector_store_id, file_infos


def save_upload_summary(vector_store_id: str, file_infos: list[dict], output_path: str) -> None:
    """Save upload summary to CSV."""
    # Keep vector_store_id in the CSV via each row if caller wants (legacy scripts don't).
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        if not file_infos:
            return
        writer = csv.DictWriter(f, fieldnames=file_infos[0].keys())
        writer.writeheader()
        writer.writerows(file_infos)

