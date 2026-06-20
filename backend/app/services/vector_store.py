import numpy as np
import json
import os
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("gravel.vectorstore")

from app.services.dp_embedder import DPEmbedder, EmbeddingResult
from app.services.dp_engine import DPConfig
from app.services.privacy_budget import PrivacyBudgetManager, PrivacyBudgetExhausted
from app.services.private_retrieval import PrivateRetriever, RetrievalResult
from app.services.chunker import CodeChunk


@dataclass
class IndexedChunk:
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    embedding: np.ndarray


class VectorStore:

    def __init__(self, dp_config: Optional[DPConfig] = None,
                 budget_manager: Optional[PrivacyBudgetManager] = None,
                 retrieval_epsilon: float = 2.0,
                 storage_dir: Optional[str] = None):
        self.dp_config = dp_config or DPConfig()
        self.embedder = DPEmbedder(dp_config=self.dp_config)
        self.budget_manager = budget_manager or PrivacyBudgetManager()
        self.retriever = PrivateRetriever(retrieval_epsilon=retrieval_epsilon)

        self._store: Dict[int, List[IndexedChunk]] = {}
        self._embeddings_cache: Dict[int, np.ndarray] = {}

        # Persistent storage
        self._storage_dir = storage_dir
        if self._storage_dir:
            os.makedirs(self._storage_dir, exist_ok=True)
            self._load_all_from_disk()

    # ------------------------------------------------------------------ #
    # Disk persistence
    # ------------------------------------------------------------------ #

    def _repo_dir(self, repo_id: int) -> Path:
        return Path(self._storage_dir) / f"repo_{repo_id}"

    def _save_to_disk(self, repo_id: int):
        """Save a single repo's indexed data to disk."""
        if not self._storage_dir:
            return
        chunks = self._store.get(repo_id, [])
        if not chunks:
            return

        repo_dir = self._repo_dir(repo_id)
        os.makedirs(repo_dir, exist_ok=True)

        # Save embeddings as numpy array
        embeddings = np.array([c.embedding for c in chunks])
        np.save(str(repo_dir / "embeddings.npy"), embeddings)

        # Save metadata as JSON
        metadata = []
        for c in chunks:
            metadata.append({
                "chunk_id": c.chunk_id,
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "content": c.content,
            })
        (repo_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

    def _load_all_from_disk(self):
        """Load all previously saved repos from disk on startup."""
        if not self._storage_dir:
            return
        storage = Path(self._storage_dir)
        if not storage.exists():
            return

        for repo_dir in storage.iterdir():
            if not repo_dir.is_dir() or not repo_dir.name.startswith("repo_"):
                continue

            try:
                repo_id = int(repo_dir.name.split("_")[1])
            except (ValueError, IndexError):
                continue

            embeddings_path = repo_dir / "embeddings.npy"
            metadata_path = repo_dir / "metadata.json"

            if not embeddings_path.exists() or not metadata_path.exists():
                continue

            try:
                embeddings = np.load(str(embeddings_path))
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

                chunks = []
                for i, meta in enumerate(metadata):
                    chunks.append(IndexedChunk(
                        chunk_id=meta["chunk_id"],
                        file_path=meta["file_path"],
                        start_line=meta["start_line"],
                        end_line=meta["end_line"],
                        content=meta["content"],
                        embedding=embeddings[i],
                    ))

                self._store[repo_id] = chunks
                self._rebuild_cache(repo_id)
            except Exception:
                continue

    def _delete_from_disk(self, repo_id: int):
        """Remove a repo's persisted data from disk."""
        if not self._storage_dir:
            return
        import shutil
        repo_dir = self._repo_dir(repo_id)
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)

    # ------------------------------------------------------------------ #
    # Core operations
    # ------------------------------------------------------------------ #

    def index_chunks(self, repo_id: int, chunks: List[CodeChunk]) -> dict:
        import time
        budget = self.budget_manager.get_or_create(repo_id)
        total_cost = len(chunks) * self.dp_config.epsilon

        if not budget.can_spend(total_cost):
            raise PrivacyBudgetExhausted(
                f"Insufficient budget. Need {total_cost:.4f}, "
                f"have {budget.epsilon_remaining:.4f}"
            )

        texts = [c.content for c in chunks]
        results = self.embedder.embed_private_batch(texts)

        logger.info("[Post-embed] Building index entries...")
        t0 = time.time()
        indexed = []
        for chunk, result in zip(chunks, results):
            ic = IndexedChunk(
                chunk_id=chunk.chunk_id,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                embedding=result.private,
            )
            indexed.append(ic)

        logger.info("[Post-embed] Built %d entries in %.2fs", len(indexed), time.time() - t0)

        # Batch budget accounting (persist only once at the end)
        logger.info("[Post-embed] Recording privacy budget...")
        t0 = time.time()
        self.budget_manager.spend_batch(
            repo_id=repo_id,
            epsilon_per_op=self.dp_config.epsilon,
            operations=[
                {
                    "operation": "index_chunk",
                    "file_path": chunk.file_path,
                    "chunk_id": chunk.chunk_id,
                }
                for chunk in chunks
            ],
        )
        logger.info("[Post-embed] Budget recorded in %.2fs", time.time() - t0)

        if repo_id not in self._store:
            self._store[repo_id] = []
        self._store[repo_id].extend(indexed)

        self._rebuild_cache(repo_id)

        logger.info("[Post-embed] Saving vectors to disk...")
        t0 = time.time()
        self._save_to_disk(repo_id)
        logger.info("[Post-embed] Saved in %.2fs", time.time() - t0)

        avg_snr = np.mean([r.snr_db for r in results])
        return {
            "chunks_indexed": len(indexed),
            "epsilon_spent": total_cost,
            "avg_snr_db": float(avg_snr),
            "budget_remaining": budget.epsilon_remaining,
        }

    def search(self, repo_id: int, query: str,
               top_k: int = 5) -> List[RetrievalResult]:
        if repo_id not in self._store or len(self._store[repo_id]) == 0:
            return []

        query_embedding = self.embedder.embed_raw(query)

        embeddings = self._embeddings_cache.get(repo_id)
        if embeddings is None:
            self._rebuild_cache(repo_id)
            embeddings = self._embeddings_cache[repo_id]

        metadata = [
            {
                "chunk_id": ic.chunk_id,
                "file_path": ic.file_path,
                "start_line": ic.start_line,
                "end_line": ic.end_line,
                "content": ic.content,
            }
            for ic in self._store[repo_id]
        ]

        return self.retriever.retrieve(
            query_embedding=query_embedding,
            stored_embeddings=embeddings,
            metadata=metadata,
            top_k=top_k,
        )

    def _rebuild_cache(self, repo_id: int):
        chunks = self._store.get(repo_id, [])
        if chunks:
            self._embeddings_cache[repo_id] = np.array(
                [c.embedding for c in chunks]
            )
        else:
            self._embeddings_cache.pop(repo_id, None)

    def get_repo_stats(self, repo_id: int) -> dict:
        chunks = self._store.get(repo_id, [])
        budget_status = self.budget_manager.get_status(repo_id)
        return {
            "total_chunks": len(chunks),
            "privacy": budget_status,
            "dp_config": {
                "epsilon": self.dp_config.epsilon,
                "mechanism": self.dp_config.mechanism.value,
                "clip_norm": self.dp_config.clip_norm,
            },
        }

    def delete_repo(self, repo_id: int):
        self._store.pop(repo_id, None)
        self._embeddings_cache.pop(repo_id, None)
        self._delete_from_disk(repo_id)
