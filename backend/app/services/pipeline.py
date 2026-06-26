import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

from app.services.vector_store import VectorStore
from app.services.llm_client import LLMClient, LLMResponse, LLMError
from app.services.private_retrieval import RetrievalResult
from app.services.code_masker import CodeMasker
from app.services.canary_engine import CanaryEngine
from app.services.cipher_engine import CipherEngine

logger = logging.getLogger("gravel.pipeline")

VALIDATION_THRESHOLD = 0.7
MAX_RETRIES = 3


@dataclass
class Citation:
    file_path: str
    start_line: int
    end_line: int
    snippet: str
    relevance_score: float


@dataclass
class ChatResponse:
    answer: str
    citations: List[Citation]
    model: str
    tokens_used: int
    chunks_retrieved: int
    privacy_metadata: Dict


class ChatPipeline:

    def __init__(self, vector_store: VectorStore,
                 llm_client: Optional[LLMClient] = None,
                 canary_engine: Optional[CanaryEngine] = None):
        self.vector_store = vector_store
        self.llm_client = llm_client or LLMClient()
        self.masker = CodeMasker()
        self.canary_engine = canary_engine or CanaryEngine()
        self.cipher = CipherEngine()

    def ask(self, question: str, repo_id: int,
            top_k: int = 5,
            model: Optional[str] = None) -> ChatResponse:

        logger.info("")
        logger.info("=" * 60)
        logger.info("GRAVEL PRIVACY PIPELINE")
        logger.info("=" * 60)
        logger.info("[INPUT] User question: %s", question)

        results = self.vector_store.search(repo_id, question, top_k=top_k)

        if not results:
            return ChatResponse(
                answer="No indexed code found. Please index the repository first.",
                citations=[], model="none", tokens_used=0,
                chunks_retrieved=0, privacy_metadata={},
            )

        logger.info("[STEP 1] Retrieved %d code chunks from DP vector store", len(results))

        code_chunks = [
            {
                "file_path": r.file_path,
                "start_line": r.start_line,
                "end_line": r.end_line,
                "content": r.content,
            }
            for r in results
        ]

        language = self._detect_language(results)
        masked_chunks, token_map = self.masker.mask_chunks(code_chunks, language=language)
        logger.info("[STEP 2] AST Masking: %d identifiers replaced", len(token_map))
        for token, original in list(token_map.items())[:5]:
            logger.info("         %s -> %s", original, token)

        canary_id = None
        try:
            if masked_chunks:
                last = masked_chunks[-1].copy()
                injected, canary_id = self.canary_engine.inject_into_prompt(last["content"])
                last["content"] = injected
                masked_chunks = masked_chunks[:-1] + [last]
                logger.info("[STEP 3] Canary token injected: %s", canary_id)
        except Exception:
            logger.info("[STEP 3] Canary injection skipped")

        llm_response, cipher_meta = self._ciphered_query(
            question=question,
            masked_chunks=masked_chunks,
            language=language,
            model=model,
        )

        raw_answer = llm_response.content

        canary_leaked = False
        if canary_id:
            leaked = self.canary_engine.check_for_leakage(raw_answer)
            canary_leaked = len(leaked) > 0
            logger.info("[STEP 7] Canary leak check: %s",
                        "LEAKED!" if canary_leaked else "clean")

        unmasked = self.masker.unmask_response(raw_answer, token_map)
        logger.info("[STEP 8] Unmasked identifiers in response")
        logger.info("")
        logger.info("=" * 60)
        logger.info("[OUTPUT] Final answer shown to user:")
        logger.info("=" * 60)
        for line in unmasked.split("\n")[:10]:
            logger.info("  %s", line)
        if len(unmasked.split("\n")) > 10:
            logger.info("  ...")
        logger.info("=" * 60)

        citations = [
            Citation(
                file_path=r.file_path,
                start_line=r.start_line,
                end_line=r.end_line,
                snippet=r.content[:200],
                relevance_score=r.raw_score,
            )
            for r in results
        ]

        dp_config = self.vector_store.dp_config
        privacy_metadata = {
            "dp_mechanism": dp_config.mechanism.value,
            "embedding_epsilon": dp_config.epsilon,
            "retrieval_epsilon": self.vector_store.retriever.exp_mechanism.epsilon,
            "clip_norm": dp_config.clip_norm,
            "identifiers_masked": len(token_map),
            "canary_injected": canary_id is not None,
            "canary_leaked": canary_leaked,
            **cipher_meta,
        }

        return ChatResponse(
            answer=unmasked,
            citations=citations,
            model=llm_response.model,
            tokens_used=llm_response.tokens_used,
            chunks_retrieved=len(results),
            privacy_metadata=privacy_metadata,
        )

    def _ciphered_query(self, question: str, masked_chunks: List[Dict],
                        language: str, model: Optional[str] = None) -> tuple:

        models_to_try = []
        if model:
            models_to_try.append(model)

        # Gemini 3.5 Flash primary, 2.5 Flash fallback
        preferred = ["gemini-3.5-flash", "gemini-2.5-flash"]
        for m in preferred:
            if m not in models_to_try:
                models_to_try.append(m)

        fallbacks = getattr(self.llm_client, "available_models", [])
        models_to_try.extend(m for m in fallbacks if m not in models_to_try)

        best_response = None
        best_score = -1.0
        total_attempts = 0

        for try_model in models_to_try:
            for attempt in range(MAX_RETRIES):
                total_attempts += 1
                session = self.cipher.create_session(language=language)

                logger.info("")
                logger.info("[STEP 4] Cipher session: %s (attempt %d, model: %s)",
                            session.session_id, total_attempts, try_model)

                encrypted_chunks = self.cipher.encrypt_chunks(masked_chunks)

                # ── Console: show what was sent ──
                logger.info("[STEP 4] ── WHAT IS BEING SENT TO LLM ──")
                logger.info("[STEP 4] Code BEFORE cipher (masked):")
                for chunk in masked_chunks[:2]:
                    for line in chunk["content"].split("\n")[:3]:
                        logger.info("    %s", line)
                    logger.info("    ...")

                logger.info("[STEP 4] Code AFTER cipher (what LLM receives):")
                for chunk in encrypted_chunks[:2]:
                    for line in chunk["content"].split("\n")[:3]:
                        logger.info("    %s", line)
                    logger.info("    ...")

                logger.info("[STEP 4] Question (plain):     %s", question[:80])
                logger.info("[STEP 4] Question (encrypted): %s",
                            self.cipher.encrypt(question)[:80])
                logger.info("[STEP 4] Validation snippet (plain):")
                for line in session.validation_plain.split("\n"):
                    logger.info("    %s", line)
                logger.info("[STEP 4] Validation snippet (encrypted):")
                for line in session.validation_encrypted.split("\n"):
                    logger.info("    %s", line)

                system_prompt = self.cipher.build_system_prompt(session)
                user_prompt = self.cipher.build_user_prompt(
                    question, encrypted_chunks, session
                )

                # -- Full prompt dump (what EXACTLY goes to the LLM) --
                logger.info("")
                logger.info("=" * 64)
                logger.info("[PROMPT SENT] FULL SYSTEM PROMPT (%d chars):", len(system_prompt))
                logger.info("=" * 64)
                for line in system_prompt.split("\n"):
                    logger.info("  %s", line)
                logger.info("")
                logger.info("=" * 64)
                logger.info("[PROMPT SENT] FULL USER PROMPT (%d chars):", len(user_prompt))
                logger.info("=" * 64)
                for line in user_prompt.split("\n"):
                    logger.info("  %s", line)
                logger.info("")
                logger.info("[PROMPT SENT] Combined size: %d chars",
                            len(system_prompt) + len(user_prompt))
                logger.info("=" * 64)

                # -- Expected validation decryption --
                logger.info("")
                logger.info("[EXPECTED] Validation snippet the LLM SHOULD decrypt to:")
                for line in session.validation_plain.split("\n"):
                    logger.info("    %s", line)
                logger.info("")

                # -- Save the entire prompt and expected validation to a file --
                try:
                    with open("prompt_dumps.txt", "a", encoding="utf-8") as dump_file:
                        dump_file.write("=" * 80 + "\n")
                        dump_file.write(f"SESSION ID: {session.session_id}\n")
                        dump_file.write("=" * 80 + "\n")
                        dump_file.write(system_prompt + "\n")
                        dump_file.write(user_prompt + "\n")
                        dump_file.write("\n" + "-" * 80 + "\n")
                        dump_file.write("EXPECTED VALIDATION OUTPUT:\n")
                        dump_file.write(session.validation_plain + "\n\n")
                except Exception as e:
                    logger.warning("Failed to write to prompt_dumps.txt: %s", e)


                try:
                    llm_response = self.llm_client.query(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=try_model,
                        response_format=self.cipher.get_response_format(),
                    )
                except (LLMError, Exception) as e:
                    logger.warning("[STEP 5] LLM call failed: %s", str(e))
                    continue

                # ── Console: show what the LLM responded with ──
                logger.info("[STEP 5] ── LLM RAW RESPONSE ──")
                logger.info("[STEP 5] Raw response (%d chars):", len(llm_response.content))
                for line in llm_response.content.split("\n")[:10]:
                    logger.info("    %s", line[:120])

                answer, validation_text = self.cipher.parse_response(
                    llm_response.content
                )

                logger.info("[STEP 6] Parsed answer: %s", answer[:100] if answer else "(empty)")
                logger.info("[STEP 6] Parsed validation (raw from LLM):")
                if validation_text:
                    for line in validation_text.split("\n"):
                        logger.info("    %s", line)
                else:
                    logger.info("    (empty)")

                # -- Decrypt what the LLM returned (in case it responded in cipher) --
                decrypted_llm_validation = self.cipher.decrypt(validation_text) if validation_text else ""
                logger.info("[STEP 6] LLM validation -> decrypted with our cipher:")
                if decrypted_llm_validation:
                    for line in decrypted_llm_validation.split("\n"):
                        logger.info("    %s", line)
                else:
                    logger.info("    (empty)")

                logger.info("[STEP 6] Expected validation (ground truth):")
                for line in session.validation_plain.split("\n"):
                    logger.info("    %s", line)

                score = self.cipher.validate_response(validation_text, session)
                logger.info("[STEP 6] Validation score (confidence): %.2f (threshold: %.2f)",
                            score, VALIDATION_THRESHOLD)

                if score >= VALIDATION_THRESHOLD:
                    logger.info("[STEP 6] Validation PASSED! Confidence: %.0f%%", score * 100)
                    final = LLMResponse(
                        content=answer,
                        model=llm_response.model,
                        tokens_used=llm_response.tokens_used,
                        finish_reason=llm_response.finish_reason,
                    )
                    meta = {
                        "cipher_enabled": True,
                        "cipher_session": session.session_id,
                        "cipher_confidence": round(score, 2),
                        "cipher_attempts": total_attempts,
                        "cipher_model": try_model,
                        "cipher_type": "fixed_key_substitution",
                    }
                    return final, meta

                logger.info("[STEP 6] Validation FAILED (%.0f%%). Retrying...", score * 100)

                if best_response is None or score > best_score:
                    best_score = score
                    best_response = LLMResponse(
                        content=answer if answer else llm_response.content,
                        model=llm_response.model,
                        tokens_used=llm_response.tokens_used,
                        finish_reason=llm_response.finish_reason,
                    )

            if total_attempts >= MAX_RETRIES * len(models_to_try):
                break

        logger.warning("[CIPHER] All %d attempts done. Using best (confidence=%.2f)",
                        total_attempts, best_score)

        if best_response is None:
            best_response = LLMResponse(
                content="The privacy cipher could not be validated after multiple attempts. Please try again.",
                model="none", tokens_used=0, finish_reason="cipher_failed",
            )

        meta = {
            "cipher_enabled": True,
            "cipher_validated": best_score >= VALIDATION_THRESHOLD,
            "cipher_confidence": round(best_score, 2),
            "cipher_attempts": total_attempts,
            "cipher_type": "fixed_key_substitution",
        }
        return best_response, meta

    def _detect_language(self, results: List[RetrievalResult]) -> str:
        ext_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".tsx": "typescript", ".jsx": "javascript",
            ".java": "java", ".go": "go", ".rs": "rust",
            ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp",
        }
        for r in results:
            for ext, lang in ext_map.items():
                if r.file_path.endswith(ext):
                    return lang
        return "python"
