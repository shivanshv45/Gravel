import numpy as np
from typing import List, Optional, Dict
from dataclasses import dataclass

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
                 retrieval_epsilon: float = 2.0):
        self.dp_config = dp_config or DPConfig()
        self.embedder = DPEmbedder(dp_config=self.dp_config)
        self.budget_manager = budget_manager or PrivacyBudgetManager()
        self.retriever = PrivateRetriever(retrieval_epsilon=retrieval_epsilon)

        self._store: Dict[int, List[IndexedChunk]] = {}
        self._embeddings_cache: Dict[int, np.ndarray] = {}

    def index_chunks(self, repo_id: int, chunks: List[CodeChunk]) -> dict:
        budget = self.budget_manager.get_or_create(repo_id)
        total_cost = len(chunks) * self.dp_config.epsilon

        if not budget.can_spend(total_cost):
            raise PrivacyBudgetExhausted(
                f"Insufficient budget. Need {total_cost:.4f}, "
                f"have {budget.epsilon_remaining:.4f}"
            )

        texts = [c.content for c in chunks]
        results = self.embedder.embed_private_batch(texts)

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

            self.budget_manager.spend(
                repo_id=repo_id,
                epsilon=self.dp_config.epsilon,
                operation="index_chunk",
                file_path=chunk.file_path,
                chunk_id=chunk.chunk_id,
            )

        if repo_id not in self._store:
            self._store[repo_id] = []
        self._store[repo_id].extend(indexed)

        self._rebuild_cache(repo_id)

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
