"""
Local vector database package using ChromaDB.

Self-contained copy of vector_db modules adapted for hal_agent.
Eliminates the sibling directory dependency and config.py namespace collision.
"""

from context_retrieval.vector_db.vector_store import VectorStore, create_database, database_exists, list_databases, delete_database
from context_retrieval.vector_db.text_processor import TextProcessor
from context_retrieval.vector_db.reranker import get_reranker
from context_retrieval.vector_db import config
