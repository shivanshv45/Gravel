import numpy as np
import logging
import time
from typing import List, Optional
from dataclasses import dataclass, field

from app.services.dp_engine import DPEngine, DPConfig, DPMechanism

logger = logging.getLogger("gravel.embedder")


@dataclass
class EmbeddingResult:
    raw: np.ndarray
    private: np.ndarray
    epsilon_spent: float
    snr_db: float


class DPEmbedder:

    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 dp_config: Optional[DPConfig] = None):
        self._model = None
        self._model_name = model_name
        self.dp_config = dp_config or DPConfig()
        self.dp_engine = DPEngine(self.dp_config)
        self._dimension = None

    def _load_model(self):
        if self._model is None:
            logger.info("Loading sentence-transformer model '%s'...", self._model_name)
            t0 = time.time()
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            try:
                self._dimension = self._model.get_embedding_dimension()
            except AttributeError:
                self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info("Model loaded in %.1fs (dim=%d)", time.time() - t0, self._dimension)

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._load_model()
        return self._dimension

    def embed_raw(self, text: str) -> np.ndarray:
        self._load_model()
        return self._model.encode(text, normalize_embeddings=True)

    def embed_raw_batch(self, texts: List[str]) -> np.ndarray:
        self._load_model()
        return self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=64,
            show_progress_bar=False,
        )

    def embed_private(self, text: str) -> EmbeddingResult:
        raw = self.embed_raw(text)
        private = self.dp_engine.privatize(raw)
        snr = self._compute_snr(raw, private)
        return EmbeddingResult(
            raw=raw,
            private=private,
            epsilon_spent=self.dp_config.epsilon,
            snr_db=snr,
        )

    def embed_private_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        total = len(texts)
        logger.info("[Embedding] Starting batch embedding of %d chunks...", total)

        # Process in sub-batches to show progress and keep memory under control
        SUB_BATCH = 64
        all_raw = []
        all_private = []

        t0 = time.time()
        for start in range(0, total, SUB_BATCH):
            end = min(start + SUB_BATCH, total)
            batch_texts = texts[start:end]

            raw_batch = self.embed_raw_batch(batch_texts)
            private_batch = self.dp_engine.privatize_batch(raw_batch)

            all_raw.append(raw_batch)
            all_private.append(private_batch)

            elapsed = time.time() - t0
            pct = (end / total) * 100
            rate = end / elapsed if elapsed > 0 else 0
            eta = (total - end) / rate if rate > 0 else 0
            logger.info(
                "[Embedding] %d/%d chunks (%.0f%%) | %.1f chunks/sec | ETA: %.0fs",
                end, total, pct, rate, eta,
            )

        raw_all = np.concatenate(all_raw, axis=0)
        private_all = np.concatenate(all_private, axis=0)

        results = []
        for i in range(total):
            snr = self._compute_snr(raw_all[i], private_all[i])
            results.append(EmbeddingResult(
                raw=raw_all[i],
                private=private_all[i],
                epsilon_spent=self.dp_config.epsilon,
                snr_db=snr,
            ))

        total_time = time.time() - t0
        logger.info(
            "[Embedding] Done! %d chunks in %.1fs (%.1f chunks/sec)",
            total, total_time, total / total_time if total_time > 0 else 0,
        )
        return results

    def _compute_snr(self, raw: np.ndarray, noisy: np.ndarray) -> float:
        noise = noisy - raw
        signal_power = np.mean(raw ** 2)
        noise_power = np.mean(noise ** 2)
        if noise_power < 1e-15:
            return 100.0
        return float(10.0 * np.log10(signal_power / noise_power))

    def similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-10 or norm2 < 1e-10:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
