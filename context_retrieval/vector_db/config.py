"""Configuration for the local vector database package."""

import os
from pathlib import Path

# Base paths - default databases directory is in hal_agent/databases/
# Can be overridden by setting DATABASES_DIR before importing other modules
_DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "databases"
DATABASES_DIR = Path(os.getenv("VECTOR_DB_DATABASES_DIR", str(_DEFAULT_DB_DIR)))

# Embedding configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Chunking configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# Search configuration
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))


def get_db_path(db_name: str) -> Path:
    """Get the path for a specific database."""
    return DATABASES_DIR / db_name


def ensure_databases_dir():
    """Ensure the databases directory exists."""
    DATABASES_DIR.mkdir(parents=True, exist_ok=True)
