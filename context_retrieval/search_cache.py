"""
Simple in-memory cache for vector store search results.

Caches search results by (query, vs_id, num_results, re_rank, score_threshold) tuple.
"""

from functools import lru_cache
import hashlib
import json


def create_cache_key(query: str, vs_id: str, num_results: int, re_rank: bool, score_threshold: float) -> str:
    """Create a stable cache key for search parameters"""
    # Use hash for long queries to keep key size reasonable
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cache_dict = {
        "query_hash": query_hash,
        "vs_id": vs_id,
        "num_results": num_results,
        "re_rank": re_rank,
        "score_threshold": score_threshold
    }
    return json.dumps(cache_dict, sort_keys=True)


class SearchCache:
    """In-memory cache for vector store search results"""

    def __init__(self, max_size: int = 10000):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, query: str, vs_id: str, num_results: int, re_rank: bool, score_threshold: float):
        """Get cached result if exists"""
        key = create_cache_key(query, vs_id, num_results, re_rank, score_threshold)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, query: str, vs_id: str, num_results: int, re_rank: bool, score_threshold: float, result):
        """Cache a search result"""
        if len(self.cache) >= self.max_size:
            # Simple LRU: remove oldest entry
            self.cache.pop(next(iter(self.cache)))

        key = create_cache_key(query, vs_id, num_results, re_rank, score_threshold)
        self.cache[key] = result

    def clear(self):
        """Clear the cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self):
        """Return cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(self.cache)
        }


# Global cache instance
_search_cache = SearchCache()


def get_cache():
    """Get the global search cache instance"""
    return _search_cache
