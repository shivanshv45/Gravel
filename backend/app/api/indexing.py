from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
import logging
import time

logger = logging.getLogger("gravel.indexing")

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.repository import Repository, CodeFile
from app.services.vector_store import VectorStore
from app.services.chunker import CodeChunker
from app.services.privacy_budget import PrivacyBudgetManager, PrivacyBudgetExhausted

router = APIRouter()

chunker = CodeChunker()


def _get_vector_store():
    from app.main import get_vector_store
    return get_vector_store()


def _get_budget_manager():
    from app.main import get_budget_manager
    return get_budget_manager()


class IndexRequest(BaseModel):
    epsilon: Optional[float] = None


class IndexResponse(BaseModel):
    repo_id: int
    repo_name: str
    chunks_indexed: int
    epsilon_spent: float
    avg_snr_db: float
    budget_remaining: float


class BudgetResponse(BaseModel):
    repo_id: int
    total_epsilon: float
    epsilon_spent: float
    epsilon_remaining: float
    utilization_pct: float
    num_operations: int


@router.post("/{repo_id}/index", response_model=IndexResponse)
def index_repository(
    repo_id: int,
    req: Optional[IndexRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t_start = time.time()
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    logger.info("")
    logger.info("=" * 60)
    logger.info("INDEXING: %s (repo_id=%d)", repo.name, repo_id)
    logger.info("=" * 60)

    files = db.query(CodeFile).filter(CodeFile.repo_id == repo_id).all()
    if not files:
        raise HTTPException(status_code=400, detail="No files found. Ingest the repository first.")

    logger.info("[1/3] Chunking %d files...", len(files))
    t_chunk = time.time()
    all_chunks = []
    for cf in files:
        if not cf.raw_content:
            continue
        language = cf.language or "python"
        chunks = chunker.chunk_file(cf.file_path, cf.raw_content, language)
        all_chunks.extend(chunks)
    logger.info("[1/3] Produced %d chunks in %.1fs", len(all_chunks), time.time() - t_chunk)

    if not all_chunks:
        raise HTTPException(status_code=400, detail="No code chunks produced from repository files")

    vs = _get_vector_store()

    logger.info("[2/3] Generating DP embeddings (ε=%.2f, mechanism=%s)...",
                vs.dp_config.epsilon, vs.dp_config.mechanism.value)

    try:
        result = vs.index_chunks(repo_id, all_chunks)
    except PrivacyBudgetExhausted as e:
        logger.warning("Budget exhausted: %s", str(e))
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.error("Indexing failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    total_time = time.time() - t_start
    logger.info("[3/3] Saved to disk")
    logger.info("")
    logger.info("INDEXING COMPLETE in %.1fs", total_time)
    logger.info("  Chunks indexed: %d", result["chunks_indexed"])
    logger.info("  Epsilon spent:  %.4f", result["epsilon_spent"])
    logger.info("  Avg SNR:        %.1f dB", result["avg_snr_db"])
    logger.info("  Budget left:    %.2f", result["budget_remaining"])
    logger.info("=" * 60)
    logger.info("")

    return IndexResponse(
        repo_id=repo_id,
        repo_name=repo.name,
        chunks_indexed=result["chunks_indexed"],
        epsilon_spent=result["epsilon_spent"],
        avg_snr_db=result["avg_snr_db"],
        budget_remaining=result["budget_remaining"],
    )


@router.get("/{repo_id}/budget", response_model=BudgetResponse)
def get_privacy_budget(
    repo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    bm = _get_budget_manager()
    status = bm.get_status(repo_id)

    return BudgetResponse(
        repo_id=repo_id,
        total_epsilon=status["total_epsilon"],
        epsilon_spent=status["epsilon_spent"],
        epsilon_remaining=status["epsilon_remaining"],
        utilization_pct=status["utilization_pct"],
        num_operations=status["num_operations"],
    )


class ResetBudgetRequest(BaseModel):
    new_total: Optional[float] = None


@router.post("/{repo_id}/budget/reset")
def reset_privacy_budget(
    repo_id: int,
    req: Optional[ResetBudgetRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    bm = _get_budget_manager()
    new_total = req.new_total if req else None
    bm.reset(repo_id, new_total=new_total)

    return {"message": "Privacy budget reset", "repo_id": repo_id}


@router.get("/{repo_id}/stats")
def get_index_stats(
    repo_id: int,
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
    stats = vs.get_repo_stats(repo_id)

    return {
        "repo_id": repo_id,
        "repo_name": repo.name,
        **stats,
    }
