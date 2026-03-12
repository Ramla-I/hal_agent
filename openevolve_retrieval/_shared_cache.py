"""Shared embedding cache that persists across dynamically-loaded evolved modules.

The cache is stored here (a regular importable module) rather than in
initial_program.py, because each evolved variant is loaded as a fresh module
via importlib — its globals don't persist. This module is imported once and
stays in sys.modules.
"""

import hashlib
from typing import Dict, List

# text_hash -> embedding vector
embedding_cache: Dict[str, List[float]] = {}


def compute_embeddings_cached(
    texts: List[str], provider
) -> List[List[float]]:
    """Compute embeddings with caching. Only embeds texts not seen before."""
    hashes = [hashlib.md5(t.encode()).hexdigest() for t in texts]
    uncached_indices = [i for i, h in enumerate(hashes) if h not in embedding_cache]

    if uncached_indices:
        uncached_texts = [texts[i] for i in uncached_indices]
        new_embeddings = provider.embed(uncached_texts)
        for idx, emb in zip(uncached_indices, new_embeddings):
            embedding_cache[hashes[idx]] = emb

    return [embedding_cache[h] for h in hashes]
