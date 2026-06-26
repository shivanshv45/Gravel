from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.repository import Repository
from app.services.pipeline import ChatPipeline

router = APIRouter()


def _get_vector_store():
    from app.main import get_vector_store
    return get_vector_store()


def _get_pipeline():
    from app.main import get_vector_store
    vs = get_vector_store()
    return ChatPipeline(vector_store=vs)


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
    ai_answer: Optional[str] = None


import json
from app.services.llm_client import LLMClient
from app.services.cipher_engine import CipherEngine
from app.services.code_masker import CodeMasker

@router.get("", response_model=SearchResponse)
def semantic_search(
    q: str = Query(..., min_length=1, description="Search query"),
    repo_id: int = Query(..., description="Repository ID to search"),
    top_k: int = Query(10, ge=1, le=20, description="Number of results"),
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
    # Get a larger pool of results to filter down
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

    filtered_items = items
    if len(items) > 0:
        try:
            # Use Privacy engine to encrypt chunks
            cipher = CipherEngine()
            session_data = cipher.create_session(language="python")
            
            # Prepare chunks for LLM
            chunks_for_llm = []
            for idx, r in enumerate(results):
                chunks_for_llm.append({
                    "id": idx,
                    "content": r.content,
                    "file_path": r.file_path,
                    "start_line": r.start_line,
                    "end_line": r.end_line
                })
                
            enc_chunks = cipher.encrypt_chunks(chunks_for_llm)
            
            context_parts = []
            for chunk in enc_chunks:
                context_parts.append(
                    f"--- CHUNK {chunk['id']} (File: {chunk['file_path']}) ---\n"
                    f"{chunk['content']}"
                )
            context_block = "\n\n".join(context_parts)
            enc_q = cipher.encrypt(q)
            
            system_prompt = (
                "You are an expert code search AI. Your task is to identify the EXACT code chunks that answer the user's question.\n"
                "The code and question are encrypted with a substitution cipher to protect privacy. "
                "Only letters and numbers are substituted; structure and punctuation remain intact.\n\n"
                "Review the provided CHUNKS. Select the 1 or 2 chunks that MOST DIRECTLY answer the user's question. "
                "Return ONLY a JSON array of the integer IDs of the relevant chunks. For example: [0, 2]. "
                "If none are relevant, return an empty array []. Do not explain."
            )
            
            user_prompt = f"Encrypted Question: {enc_q}\n\nEncrypted Chunks:\n\n{context_block}"
            
            llm = LLMClient()
            response = llm.query(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gemini-2.5-flash",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "relevant_chunks",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "relevant_ids": {
                                    "type": "array",
                                    "items": {"type": "integer"}
                                }
                            },
                            "required": ["relevant_ids"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            parsed = json.loads(response.content)
            relevant_ids = parsed.get("relevant_ids", [])
            
            if relevant_ids:
                filtered_items = [items[i] for i in relevant_ids if 0 <= i < len(items)]
                # Keep top 2 max as requested by user
                filtered_items = filtered_items[:2]
                
                # Boost scores for visual feedback
                for item in filtered_items:
                    item.score = min(item.score + 0.2, 0.99)
            
        except Exception as e:
            print(f"Failed to use LLM smart filter: {e}")
            # Fallback to top 2 semantic results
            filtered_items = items[:2]

    return SearchResponse(
        query=q,
        repo_id=repo_id,
        results=filtered_items,
        total_results=len(filtered_items),
        ai_answer=None,
    )
