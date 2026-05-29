from typing import List, Optional, Dict
from dataclasses import dataclass, field

from app.services.vector_store import VectorStore
from app.services.llm_client import LLMClient, LLMResponse, LLMError
from app.services.private_retrieval import RetrievalResult


@dataclass
class Citation:
    file_path: str
    start_line: int
    end_line: int
    snippet: str
    relevance_score: float


@dataclass
class ChatResponse:
    answer: str
    citations: List[Citation]
    model: str
    tokens_used: int
    chunks_retrieved: int
    privacy_metadata: Dict


class ChatPipeline:

    def __init__(self, vector_store: VectorStore,
                 llm_client: Optional[LLMClient] = None):
        self.vector_store = vector_store
        self.llm_client = llm_client or LLMClient()

    def ask(self, question: str, repo_id: int,
            top_k: int = 5,
            model: Optional[str] = None) -> ChatResponse:

        results = self.vector_store.search(repo_id, question, top_k=top_k)

        if not results:
            return ChatResponse(
                answer="No indexed code found for this repository. Please index the repository first.",
                citations=[],
                model="none",
                tokens_used=0,
                chunks_retrieved=0,
                privacy_metadata={},
            )

        code_chunks = [
            {
                "file_path": r.file_path,
                "start_line": r.start_line,
                "end_line": r.end_line,
                "content": r.content,
            }
            for r in results
        ]

        llm_response = self.llm_client.query_with_context(
            question=question,
            code_chunks=code_chunks,
            model=model,
        )

        citations = [
            Citation(
                file_path=r.file_path,
                start_line=r.start_line,
                end_line=r.end_line,
                snippet=r.content[:200],
                relevance_score=r.raw_score,
            )
            for r in results
        ]

        dp_config = self.vector_store.dp_config
        privacy_metadata = {
            "dp_mechanism": dp_config.mechanism.value,
            "embedding_epsilon": dp_config.epsilon,
            "retrieval_epsilon": self.vector_store.retriever.exp_mechanism.epsilon,
            "clip_norm": dp_config.clip_norm,
        }

        return ChatResponse(
            answer=llm_response.content,
            citations=citations,
            model=llm_response.model,
            tokens_used=llm_response.tokens_used,
            chunks_retrieved=len(results),
            privacy_metadata=privacy_metadata,
        )
