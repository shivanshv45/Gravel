import os
import time
import httpx
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger("gravel.llm")


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    finish_reason: str


PROVIDERS = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "models": [
            "gemini-3.5-flash",
            "gemini-3.1-pro-preview",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ],
        "default": "gemini-3.5-flash",
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ],
        "default": "llama-3.3-70b-versatile",
    },
}


class LLMClient:

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")

        # Gemini primary, Groq fallback
        if self._is_valid(self.gemini_key):
            self.provider = "gemini"
            self.api_key = self.gemini_key
        elif self._is_valid(self.groq_key):
            self.provider = "groq"
            self.api_key = self.groq_key
        else:
            self.provider = None
            self.api_key = ""

        config = PROVIDERS.get(self.provider, {})
        self.api_url = config.get("url", "")
        self.default_model = config.get("default", "")
        self.available_models = config.get("models", [])

    def _is_valid(self, key):
        return bool(key) and key not in (
            "", "your_groq_api_key_here", "YOUR_GROQ_API_KEY",
            "your_gemini_api_key_here",
        )

    def _build_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_provider_for_model(self, model: str):
        """Route model to the correct provider and API key."""
        for prov_name, prov_config in PROVIDERS.items():
            if model in prov_config["models"]:
                key = self.gemini_key if prov_name == "gemini" else self.groq_key
                if self._is_valid(key):
                    return prov_config["url"], key
        return self.api_url, self.api_key

    def query(self, system_prompt: str, user_prompt: str,
              model: Optional[str] = None,
              temperature: float = 0.3,
              max_tokens: int = 4096,
              response_format: Optional[dict] = None) -> LLMResponse:

        if not self.provider:
            return self._local_fallback(user_prompt)

        model = model or self.default_model
        api_url, api_key = self._get_provider_for_model(model)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        try:
            response = None
            for attempt in range(3):
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(api_url, headers=headers, json=payload)

                if response.status_code == 503:
                    wait = 5 * (attempt + 1)
                    logger.warning("503 overload on %s, retrying in %ds...", model, wait)
                    time.sleep(wait)
                    continue
                break

            if response.status_code != 200:
                raise LLMError(
                    f"{model} API error {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            choice = data["choices"][0]

            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", model),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=choice.get("finish_reason", "unknown"),
            )
        except httpx.ConnectError:
            return self._local_fallback(user_prompt)

    def query_with_context(self, question: str,
                           code_chunks: List[Dict],
                           model: Optional[str] = None) -> LLMResponse:

        context_parts = []
        for chunk in code_chunks:
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

    def _local_fallback(self, prompt: str) -> LLMResponse:
        files_mentioned = []
        for line in prompt.split("\n"):
            if line.startswith("--- File:") or line.startswith("---"):
                files_mentioned.append(line.replace("--- File:", "").strip())

        if files_mentioned:
            file_list = "\n".join(f"  - {f}" for f in files_mentioned[:5])
            answer = (
                f"**[Local Mode - No LLM API key configured]**\n\n"
                f"I found {len(files_mentioned)} relevant code chunks.\n\n"
                f"{file_list}\n\n"
                f"Add GEMINI_API_KEY or GROQ_API_KEY to your .env file."
            )
        else:
            answer = (
                "**[Local Mode]** No API key found. "
                "Add GEMINI_API_KEY or GROQ_API_KEY to your .env file."
            )

        return LLMResponse(
            content=answer, model="local-fallback",
            tokens_used=0, finish_reason="local",
        )


class LLMError(Exception):
    pass
