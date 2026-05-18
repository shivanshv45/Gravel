import numpy as np
from typing import List, Optional
from dataclasses import dataclass, field

from app.services.dp_engine import DPEngine, DPConfig, DPMechanism


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
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()

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
        return self._model.encode(texts, normalize_embeddings=True, batch_size=32)

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
        raw_batch = self.embed_raw_batch(texts)
        private_batch = self.dp_engine.privatize_batch(raw_batch)

        results = []
        for i in range(len(texts)):
            snr = self._compute_snr(raw_batch[i], private_batch[i])
            results.append(EmbeddingResult(
                raw=raw_batch[i],
                private=private_batch[i],
                epsilon_spent=self.dp_config.epsilon,
                snr_db=snr,
            ))
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
