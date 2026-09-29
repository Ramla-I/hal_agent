"""Shared embedding cache that persists across dynamically-loaded evolved modules
AND across processes (on disk).

The in-memory dict is stored here (a regular importable module) rather than in
initial_program.py, because each evolved variant is loaded as a fresh module via
importlib — its globals don't persist. This module is imported once and stays in
sys.modules.

On top of that, embeddings are persisted to an on-disk SQLite store keyed by the
chunk-text hash, so a fresh PROCESS (each s6 invocation, each generation run,
each re-run) does NOT re-embed the datasheet chunks. Re-embedding thousands of
chunks on CPU is the dominant cost of openevolve retrieval — ~1h for the largest
STM datasheets — and it was paid on every process. Content-keyed, so re-chunking
a datasheet naturally invalidates only the changed chunks. Override the store
path with $OE_EMBED_CACHE.
"""

import hashlib
import os
import sqlite3
import threading
from array import array
from typing import Dict, List

# text_hash -> embedding vector (in-process hot cache; unchanged behavior)
embedding_cache: Dict[str, List[float]] = {}

_DB_PATH = os.environ.get(
    "OE_EMBED_CACHE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "databases", "oe_embed_cache.sqlite"),
)
_lock = threading.Lock()
_conn = None
_conn_pid = None


def _db():
    """Per-process SQLite connection (reopened after a fork/forkserver spawn —
    a connection must never be shared across processes)."""
    global _conn, _conn_pid
    if _conn is None or _conn_pid != os.getpid():
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        c = sqlite3.connect(_DB_PATH, timeout=120, check_same_thread=False)
        c.execute("PRAGMA journal_mode=WAL")     # concurrent readers + one writer
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA busy_timeout=120000")  # wait out concurrent writers (P2, forkserver kids)
        c.execute("CREATE TABLE IF NOT EXISTS emb (h TEXT PRIMARY KEY, v BLOB)")
        _conn, _conn_pid = c, os.getpid()
    return _conn


def _disk_get(hashes: List[str]) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    if not hashes:
        return out
    c = _db()
    for i in range(0, len(hashes), 500):            # keep the IN(...) list bounded
        part = hashes[i:i + 500]
        rows = c.execute(
            "SELECT h, v FROM emb WHERE h IN (%s)" % ",".join("?" * len(part)), part)
        for h, v in rows:
            a = array("f")
            a.frombytes(v)
            out[h] = list(a)
    return out


def _disk_put(items: Dict[str, List[float]]) -> None:
    if not items:
        return
    c = _db()
    with _lock:
        c.executemany(
            "INSERT OR IGNORE INTO emb(h, v) VALUES(?, ?)",
            [(h, array("f", [float(x) for x in vec]).tobytes()) for h, vec in items.items()])
        c.commit()


def compute_embeddings_cached(texts: List[str], provider) -> List[List[float]]:
    """Embeddings with a two-level (in-memory + on-disk) cache; only genuinely
    unseen chunk texts are embedded, and the result is persisted for future
    processes."""
    hashes = [hashlib.md5(t.encode()).hexdigest() for t in texts]

    # 1. disk-load anything not already hot in memory (dedup hashes first).
    need = [h for h in dict.fromkeys(hashes) if h not in embedding_cache]
    if need:
        try:
            embedding_cache.update(_disk_get(need))
        except Exception:
            pass  # cache is an optimization; never let it break retrieval

    # 2. embed whatever is still missing (each unique text once), persist it.
    text_by_hash: Dict[str, str] = {}
    for t, h in zip(texts, hashes):
        if h not in embedding_cache and h not in text_by_hash:
            text_by_hash[h] = t
    if text_by_hash:
        miss_h = list(text_by_hash)
        new = provider.embed([text_by_hash[h] for h in miss_h])
        fresh: Dict[str, List[float]] = {}
        for h, emb in zip(miss_h, new):
            vec = list(emb)
            embedding_cache[h] = vec
            fresh[h] = vec
        try:
            _disk_put(fresh)
        except Exception:
            pass

    return [embedding_cache[h] for h in hashes]
