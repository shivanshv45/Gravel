import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum


class DPMechanism(str, Enum):
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"


@dataclass
class DPConfig:
    epsilon: float = 1.0
    clip_norm: float = 1.0
    mechanism: DPMechanism = DPMechanism.LAPLACE
    delta: float = 1e-5
    dimension: int = 384

    @property
    def sensitivity(self) -> float:
        return 2.0 * self.clip_norm


class DPEngine:

    def __init__(self, config: Optional[DPConfig] = None):
        self.config = config or DPConfig()
        self._rng = np.random.default_rng()

    def clip(self, vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm > self.config.clip_norm:
            vector = vector * (self.config.clip_norm / norm)
        return vector

    def _laplace_noise(self, shape: tuple) -> np.ndarray:
        scale = self.config.sensitivity / self.config.epsilon
        return self._rng.laplace(0.0, scale, size=shape)

    def _gaussian_noise(self, shape: tuple) -> np.ndarray:
        sigma = (self.config.sensitivity / self.config.epsilon) * np.sqrt(
            2.0 * np.log(1.25 / self.config.delta)
        )
        return self._rng.normal(0.0, sigma, size=shape)

    def add_noise(self, vector: np.ndarray) -> np.ndarray:
        if self.config.mechanism == DPMechanism.LAPLACE:
            noise = self._laplace_noise(vector.shape)
        elif self.config.mechanism == DPMechanism.GAUSSIAN:
            noise = self._gaussian_noise(vector.shape)
        else:
            raise ValueError(f"Unknown mechanism: {self.config.mechanism}")
        return vector + noise

    def privatize(self, vector: np.ndarray) -> np.ndarray:
        clipped = self.clip(vector)
        noisy = self.add_noise(clipped)
        return noisy

    def privatize_batch(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        scale = np.minimum(1.0, self.config.clip_norm / (norms + 1e-10))
        clipped = vectors * scale

        if self.config.mechanism == DPMechanism.LAPLACE:
            noise = self._laplace_noise(clipped.shape)
        else:
            noise = self._gaussian_noise(clipped.shape)

        return clipped + noise

    def compute_privacy_cost(self, num_queries: int) -> dict:
        if self.config.mechanism == DPMechanism.LAPLACE:
            total_epsilon = num_queries * self.config.epsilon
            return {
                "mechanism": "laplace",
                "per_query_epsilon": self.config.epsilon,
                "num_queries": num_queries,
                "total_epsilon_sequential": total_epsilon,
                "delta": 0.0,
            }
        else:
            per_query_epsilon = self.config.epsilon
            total_epsilon_naive = num_queries * per_query_epsilon

            alpha = 1.0 + (1.0 / per_query_epsilon) if per_query_epsilon > 0 else 2.0
            rdp_per_query = alpha / (2.0 * (self.config.sensitivity ** 2))
            total_rdp = num_queries * rdp_per_query
            total_epsilon_rdp = total_rdp + np.log(1.0 / self.config.delta) / (alpha - 1.0)

            return {
                "mechanism": "gaussian",
                "per_query_epsilon": per_query_epsilon,
                "num_queries": num_queries,
                "total_epsilon_naive": total_epsilon_naive,
                "total_epsilon_rdp": float(total_epsilon_rdp),
                "rdp_alpha": float(alpha),
                "delta": self.config.delta,
            }
