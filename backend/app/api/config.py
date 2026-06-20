from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()


class ConfigResponse(BaseModel):
    dp_epsilon: float
    dp_clip_norm: float
    dp_mechanism: str
    retrieval_epsilon: float
    llm_configured: bool
    llm_model: str
    default_budget: float


@router.get("", response_model=ConfigResponse)
def get_config(current_user: User = Depends(get_current_user)):
    from app.main import get_vector_store
    from app.services.llm_client import LLMClient

    vs = get_vector_store()
    llm = LLMClient()

    return ConfigResponse(
        dp_epsilon=vs.dp_config.epsilon,
        dp_clip_norm=vs.dp_config.clip_norm,
        dp_mechanism=vs.dp_config.mechanism.value,
        retrieval_epsilon=vs.retriever.exp_mechanism.epsilon,
        llm_configured=llm._has_valid_key,
        llm_model=llm.default_model,
        default_budget=1000.0,
    )
