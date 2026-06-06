from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.repository import Repository
from app.services.pipeline import ChatPipeline
from app.services.llm_client import LLMClient, LLMError

router = APIRouter()


def _get_pipeline():
    from app.main import get_vector_store
    vs = get_vector_store()
    return ChatPipeline(vector_store=vs)


class ChatRequest(BaseModel):
    query: str
    repo_id: int
    top_k: Optional[int] = 5
    model: Optional[str] = None


class CitationItem(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    snippet: str
    relevance_score: float


class ChatResponseModel(BaseModel):
    answer: str
    citations: List[CitationItem]
    model: str
    tokens_used: int
    chunks_retrieved: int
    privacy_metadata: Dict


@router.post("", response_model=ChatResponseModel)
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = db.query(Repository).filter(
        Repository.id == req.repo_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    pipeline = _get_pipeline()

    try:
        result = pipeline.ask(
            question=req.query,
            repo_id=req.repo_id,
            top_k=req.top_k or 5,
            model=req.model,
        )
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

    return ChatResponseModel(
        answer=result.answer,
        citations=[
            CitationItem(
                file_path=c.file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                snippet=c.snippet,
                relevance_score=c.relevance_score,
            )
            for c in result.citations
        ],
        model=result.model,
        tokens_used=result.tokens_used,
        chunks_retrieved=result.chunks_retrieved,
        privacy_metadata=result.privacy_metadata,
    )
