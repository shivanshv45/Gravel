import os
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    finish_reason: str


class LLMClient:

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None,
                 default_model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.default_model = default_model

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def query(self, system_prompt: str, user_prompt: str,
              model: Optional[str] = None,
              temperature: float = 0.3,
              max_tokens: int = 2048) -> LLMResponse:

        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.GROQ_API_URL,
                headers=self._build_headers(),
                json=payload,
            )

        if response.status_code != 200:
            raise LLMError(
                f"Groq API error {response.status_code}: {response.text}"
            )

        data = response.json()
        choice = data["choices"][0]

        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", model),
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "unknown"),
        )

    def query_with_context(self, question: str,
                           code_chunks: List[Dict],
                           model: Optional[str] = None) -> LLMResponse:

        context_parts = []
        for i, chunk in enumerate(code_chunks):
            context_parts.append(
                f"--- File: {chunk['file_path']} "
                f"(lines {chunk['start_line']}-{chunk['end_line']}) ---\n"
                f"{chunk['content']}"
            )

        context_block = "\n\n".join(context_parts)

        system_prompt = (
            "You are Gravel, a privacy-first AI code intelligence assistant. "
            "You analyze source code and answer developer questions accurately. "
            "Always cite the specific file and line numbers in your response. "
            "Be concise and technical."
        )

        user_prompt = (
            f"Here is the relevant code context:\n\n"
            f"{context_block}\n\n"
            f"Question: {question}"
        )

        return self.query(system_prompt, user_prompt, model=model)


class LLMError(Exception):
    pass
