from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet down noisy third-party loggers
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from app.api import auth
from app.api import repos
from app.api import indexing
from app.api import search
from app.api import chat
from app.api import config
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.repository import Repository, CodeFile
from app.services.vector_store import VectorStore
from app.services.dp_engine import DPConfig, DPMechanism
from app.services.privacy_budget import PrivacyBudgetManager

budget_dir = Path(__file__).resolve().parent.parent / "privacy_budgets"
budget_manager = PrivacyBudgetManager(storage_dir=str(budget_dir))

dp_config = DPConfig(
    epsilon=float(os.getenv("DP_EPSILON", "1.0")),
    clip_norm=float(os.getenv("DP_CLIP_NORM", "1.0")),
    mechanism=DPMechanism(os.getenv("DP_MECHANISM", "laplace")),
)

vector_store_dir = Path(__file__).resolve().parent.parent / "vector_data"

vector_store = VectorStore(
    dp_config=dp_config,
    budget_manager=budget_manager,
    retrieval_epsilon=float(os.getenv("DP_RETRIEVAL_EPSILON", "2.0")),
    storage_dir=str(vector_store_dir),
)


def get_vector_store() -> VectorStore:
    return vector_store


def get_budget_manager() -> PrivacyBudgetManager:
    return budget_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import create_tables
    create_tables()
    yield


app = FastAPI(title="Gravel API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(repos.router, prefix="/api/repos", tags=["repos"])
app.include_router(indexing.router, prefix="/api/indexing", tags=["indexing"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(config.router, prefix="/api/config", tags=["config"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Gravel Backend API"}


@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }
