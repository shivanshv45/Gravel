from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

from app.api import auth
from app.api import repos
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.repository import Repository, CodeFile

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
   

app = FastAPI(title="Gravel API", version="1.0.0", lifespan=lifespan)

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(repos.router, prefix="/api/repos", tags=["repos"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Gravel Backend API"}

@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }
