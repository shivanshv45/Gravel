from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json
import os

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.repository import Repository, CodeFile
from app.services.repo_scanner import scan_repository
from app.services.ast_parser import parse_file

router = APIRouter()

class RepoIngestRequest(BaseModel):
    path: str
    name: str

class RepoResponse(BaseModel):
    id: int
    name: str
    local_path: str
    owner_id: int
    file_count: int

class CodeFileResponse(BaseModel):
    id: int
    file_path: str
    language: Optional[str]
    functions: List[str]
    classes: List[str]
    imports: List[str]
    comment_count: int

@router.post("/ingest", response_model=RepoResponse)
def ingest_repository(
    req: RepoIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    
    if not os.path.isdir(req.path):
        raise HTTPException(status_code=400, detail=f"Directory not found: {req.path}")

    
    existing = db.query(Repository).filter(
        Repository.local_path == req.path,
        Repository.owner_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Repository already ingested. Delete it first or use a different path.")

    
    repo = Repository(
        name=req.name,
        local_path=req.path,
        owner_id=current_user.id,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    
    try:
        file_infos = scan_repository(req.path)
    except ValueError as e:
        db.delete(repo)
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    
    file_count = 0
    for fi in file_infos:
        try:
            with open(fi.path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            parsed = parse_file(fi.path, fi.language, content)

            code_file = CodeFile(
                repo_id=repo.id,
                file_path=os.path.relpath(fi.path, req.path),  
                language=fi.language,
                raw_content=content,
                ast_metadata_json=json.dumps({
                    "functions": parsed.functions,
                    "classes": parsed.classes,
                    "imports": parsed.imports,
                    "comments": parsed.comments,
                }),
            )
            db.add(code_file)
            file_count += 1
        except Exception:
            
            continue

    db.commit()

    return RepoResponse(
        id=repo.id,
        name=repo.name,
        local_path=repo.local_path,
        owner_id=repo.owner_id,
        file_count=file_count,
    )

@router.get("/{repo_id}/files", response_model=List[CodeFileResponse])
def list_repo_files(
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

    files = db.query(CodeFile).filter(CodeFile.repo_id == repo_id).all()

    results = []
    for cf in files:
        meta = json.loads(cf.ast_metadata_json) if cf.ast_metadata_json else {}
        results.append(CodeFileResponse(
            id=cf.id,
            file_path=cf.file_path,
            language=cf.language,
            functions=meta.get("functions", []),
            classes=meta.get("classes", []),
            imports=meta.get("imports", []),
            comment_count=len(meta.get("comments", [])),
        ))

    return results

@router.get("", response_model=List[RepoResponse])
def list_repos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    repos = db.query(Repository).filter(Repository.owner_id == current_user.id).all()
    results = []
    for repo in repos:
        file_count = db.query(CodeFile).filter(CodeFile.repo_id == repo.id).count()
        results.append(RepoResponse(
            id=repo.id,
            name=repo.name,
            local_path=repo.local_path,
            owner_id=repo.owner_id,
            file_count=file_count,
        ))
    return results
