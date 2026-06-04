"""
Chunk Index for local lookup and contiguous chunk expansion.

This module provides a ChunkIndex class that loads chunk metadata from chunks_index.csv
and enables efficient lookup of chunks by page number. This supports contiguous chunk
expansion where semantic search results are expanded with chunks from subsequent pages.

OpenAI vector store search does NOT support metadata filtering, so we use this local
index to perform page-based lookups after semantic search returns initial results.

Table-aware expansion:
The ChunkIndex can also load metadata.json (from the enrichment step) to determine
which pages contain tables. This enables the table_pages_only filter for contiguous
chunk expansion.
"""

import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from utils.utils import setup_logger

logger = setup_logger(__name__)


class ChunkIndex:
    """
    Index for mapping pages to chunks and reading chunk content locally.

    Loads chunk metadata from chunks_index.csv which contains:
    - chunk_id: e.g., 'rm0041_p187_c01'
    - file_id: OpenAI file ID
    - file_path: local path to chunk file
    - page_number: page number (1-indexed)
    - chunk_index: chunk index on that page (1-indexed)
    - token_count: number of tokens in chunk
    """

    def __init__(self, upload_summary_csv: str, load_metadata: bool = True):
        """
        Initialize the chunk index from a chunks_index.csv file.

        Args:
            upload_summary_csv: Path to the chunks_index.csv file (legacy name kept for compatibility)
            load_metadata: Whether to load metadata.json for table information (default: True)
        """
        self.csv_path = upload_summary_csv
        self.page_to_chunks: Dict[int, List[dict]] = defaultdict(list)
        self.chunk_id_to_info: Dict[str, dict] = {}
        self._base_dir: Optional[str] = None

        # Table-aware expansion data
        self._chunk_has_tables: Dict[str, bool] = {}  # chunk_id -> has_tables
        self._pages_with_tables: Set[int] = set()  # pages that have at least one chunk with tables

        self._load_from_csv(upload_summary_csv)

        if load_metadata:
            self._load_metadata()

    def _load_from_csv(self, csv_path: str):
        """Load chunk index from CSV file."""
        if not os.path.exists(csv_path):
            logger.error(f"Chunk index CSV not found: {csv_path}")
            raise FileNotFoundError(f"Chunk index CSV not found: {csv_path}")

        # Store base directory for resolving relative paths
        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(csv_path)))

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                chunk_info = {
                    'chunk_id': row.get('chunk_id', ''),
                    'file_id': row.get('file_id', ''),
                    'file_path': row.get('file_path', ''),
                    'page_number': int(row.get('page_number', 0)),
                    'chunk_index': int(row.get('chunk_index', 0)),
                    'total_chunks_on_page': int(row.get('total_chunks_on_page', 0)),
                    'token_count': int(row.get('token_count', 0)),
                    'datasheet': row.get('datasheet', ''),
                }

                page = chunk_info['page_number']
                chunk_id = chunk_info['chunk_id']

                self.page_to_chunks[page].append(chunk_info)
                self.chunk_id_to_info[chunk_id] = chunk_info

        # Sort chunks within each page by chunk_index
        for page in self.page_to_chunks:
            self.page_to_chunks[page].sort(key=lambda x: x['chunk_index'])

        logger.info(f"Loaded chunk index: {len(self.chunk_id_to_info)} chunks across {len(self.page_to_chunks)} pages")

    def _load_metadata(self):
        """
        Load metadata.json to get table information per chunk.

        The metadata.json file is expected to be in the same directory as the chunks_index.csv.
        It contains a dict mapping chunk_id -> metadata, where metadata includes 'has_tables'.
        """
        csv_dir = os.path.dirname(self.csv_path)
        metadata_path = os.path.join(csv_dir, "metadata.json")

        if not os.path.exists(metadata_path):
            logger.debug(f"No metadata.json found at {metadata_path} - table filtering disabled")
            return

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)

            for chunk_id, metadata in all_metadata.items():
                has_tables = metadata.get('has_tables', False)
                self._chunk_has_tables[chunk_id] = has_tables

                # If this chunk has tables, mark its page as having tables
                if has_tables:
                    chunk_info = self.chunk_id_to_info.get(chunk_id)
                    if chunk_info:
                        page = chunk_info.get('page_number', 0)
                        if page > 0:
                            self._pages_with_tables.add(page)

            logger.info(f"Loaded table metadata: {len(self._pages_with_tables)} pages with tables")

        except Exception as e:
            logger.warning(f"Error loading metadata.json: {e} - table filtering disabled")

    def get_chunks_for_pages(self, pages: List[int]) -> List[dict]:
        """
        Get all chunks for given page numbers, sorted by page then chunk_index.

        Args:
            pages: List of page numbers (1-indexed)

        Returns:
            List of chunk info dictionaries, sorted by (page, chunk_index)
        """
        chunks = []
        for page in sorted(pages):
            if page in self.page_to_chunks:
                chunks.extend(self.page_to_chunks[page])
        return chunks

    def get_contiguous_pages(self, page: int, pages_after: int = 2, table_pages_only: bool = False) -> List[int]:
        """
        Return page numbers for contiguous pages after a given page.

        Args:
            page: Starting page number (1-indexed)
            pages_after: Number of pages to include after the starting page
            table_pages_only: If True, only include pages that contain tables

        Returns:
            List of page numbers [page+1, page+2, ...] up to pages_after,
            optionally filtered to only pages with tables.
        """
        max_page = max(self.page_to_chunks.keys()) if self.page_to_chunks else 0
        contiguous = [p for p in range(page + 1, page + 1 + pages_after) if p <= max_page]

        if table_pages_only:
            contiguous = [p for p in contiguous if self.page_has_tables(p)]

        return contiguous

    def page_has_tables(self, page: int) -> bool:
        """
        Check if a page has at least one chunk containing tables.

        Args:
            page: Page number (1-indexed)

        Returns:
            True if the page has tables, False otherwise
        """
        return page in self._pages_with_tables

    def chunk_has_tables(self, chunk_id: str) -> bool:
        """
        Check if a specific chunk contains tables.

        Args:
            chunk_id: The chunk ID to check

        Returns:
            True if the chunk has tables, False otherwise
        """
        return self._chunk_has_tables.get(chunk_id, False)

    @property
    def has_table_metadata(self) -> bool:
        """Check if table metadata was loaded successfully."""
        return len(self._chunk_has_tables) > 0

    def get_chunk_by_id(self, chunk_id: str) -> Optional[dict]:
        """Get chunk info by chunk_id."""
        return self.chunk_id_to_info.get(chunk_id)

    def read_chunk_content(self, chunk_info: dict) -> str:
        """
        Read chunk content from local file_path.

        Args:
            chunk_info: Chunk info dictionary with 'file_path' key

        Returns:
            Content of the chunk file as string
        """
        file_path = chunk_info.get('file_path', '')

        if not file_path:
            logger.warning(f"No file_path for chunk: {chunk_info.get('chunk_id', 'unknown')}")
            return ''

        # Handle relative paths - try both absolute and relative to project root
        if not os.path.isabs(file_path):
            # Try relative to the CSV file's parent directory
            full_path = os.path.join(self._base_dir, file_path) if self._base_dir else file_path
            if not os.path.exists(full_path):
                # Try relative to current working directory
                full_path = file_path
        else:
            full_path = file_path

        if not os.path.exists(full_path):
            logger.warning(f"Chunk file not found: {full_path}")
            return ''

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading chunk file {full_path}: {e}")
            return ''

    @property
    def total_chunks(self) -> int:
        """Total number of chunks in the index."""
        return len(self.chunk_id_to_info)

    @property
    def total_pages(self) -> int:
        """Total number of pages with chunks."""
        return len(self.page_to_chunks)

    def __repr__(self):
        return f"ChunkIndex({self.total_chunks} chunks, {self.total_pages} pages)"


# Global cache for chunk indices
_chunk_index_cache: Dict[str, ChunkIndex] = {}


def get_chunk_index(upload_summary_csv: str) -> ChunkIndex:
    """
    Get a cached ChunkIndex for the given CSV file.

    This function caches ChunkIndex instances to avoid reloading
    the same CSV file multiple times.

    Args:
        upload_summary_csv: Path to the chunks_index.csv file (legacy name kept for compatibility)

    Returns:
        ChunkIndex instance (cached if previously loaded)
    """
    csv_path = os.path.abspath(upload_summary_csv)

    if csv_path not in _chunk_index_cache:
        _chunk_index_cache[csv_path] = ChunkIndex(csv_path)

    return _chunk_index_cache[csv_path]


if __name__ == "__main__":
    # Test the chunk index
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chunk_index.py <chunks_index.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    index = ChunkIndex(csv_path)

    print(f"\nChunk Index Summary:")
    print(f"  Total chunks: {index.total_chunks}")
    print(f"  Total pages: {index.total_pages}")

    # Show chunks on a sample page
    if index.total_pages > 0:
        sample_page = list(index.page_to_chunks.keys())[0]
        chunks = index.get_chunks_for_pages([sample_page])
        print(f"\nChunks on page {sample_page}:")
        for chunk in chunks:
            print(f"  - {chunk['chunk_id']} ({chunk['token_count']} tokens)")

        # Show contiguous pages
        contiguous = index.get_contiguous_pages(sample_page, pages_after=2)
        print(f"\nContiguous pages after {sample_page}: {contiguous}")

        # Read sample content
        if chunks:
            content = index.read_chunk_content(chunks[0])
            print(f"\nSample content preview (first 200 chars):")
            print(f"  {content[:200]}...")
