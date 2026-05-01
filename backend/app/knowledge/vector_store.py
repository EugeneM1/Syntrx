"""
Thin wrapper around ChromaDB.

ChromaDB is heavy and we don't want to fail the whole API if it's
missing in dev. The wrapper degrades gracefully: if Chroma can't be
imported or its persist dir is empty, `is_available()` returns False
and the LookupAgent uses the curated catalog as evidence.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class VectorStore:
    _default: "VectorStore | None" = None

    def __init__(self, persist_dir: str | None = None) -> None:
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        self._client: Any | None = None
        self._collection: Any | None = None
        self._init_attempted = False

    # --- public ----------------------------------------------------------

    def is_available(self) -> bool:
        self._lazy_init()
        return self._collection is not None and self._collection_count() > 0

    def query(self, rsid: str, gene: str, top_k: int = 5) -> list[dict]:
        if not self.is_available():
            return []
        try:
            results = self._collection.query(
                query_texts=[f"{rsid} {gene}"],
                n_results=top_k,
            )
        except Exception:
            return []
        out: list[dict] = []
        for doc, meta, dist in zip(
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0],
            strict=False,
        ):
            out.append({
                "text": doc,
                "source": (meta or {}).get("source", "unknown"),
                "score": 1.0 - float(dist),
            })
        return out

    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        self._lazy_init()
        if self._collection is None:
            return
        self._collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    # --- internals -------------------------------------------------------

    def _lazy_init(self) -> None:
        if self._init_attempted:
            return
        self._init_attempted = True
        try:
            import chromadb  # type: ignore
        except Exception:
            return
        try:
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection("syntrx_evidence")
        except Exception:
            self._client = None
            self._collection = None

    def _collection_count(self) -> int:
        try:
            return self._collection.count() if self._collection else 0
        except Exception:
            return 0

    @classmethod
    def get_default(cls) -> "VectorStore":
        if cls._default is None:
            cls._default = cls()
        return cls._default
