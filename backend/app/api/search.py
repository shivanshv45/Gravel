from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.repository import Repository

router = APIRouter()


def _get_vector_store():
    from app.main import get_vector_store
    return get_vector_store()


class SearchResultItem(BaseModel):
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    repo_id: int
    results: List[SearchResultItem]
    total_results: int


@router.get("", response_model=SearchResponse)
def semantic_search(
    q: str = Query(..., min_length=1, description="Search query"),
    repo_id: int = Query(..., description="Repository ID to search"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    vs = _get_vector_store()
    results = vs.search(repo_id, q, top_k=top_k)

    items = [
        SearchResultItem(
            chunk_id=r.chunk_id,
            file_path=r.file_path,
            start_line=r.start_line,
            end_line=r.end_line,
            content=r.content,
            score=r.raw_score,
        )
        for r in results
    ]

    return SearchResponse(
        query=q,
        repo_id=repo_id,
        results=items,
        total_results=len(items),
    )
