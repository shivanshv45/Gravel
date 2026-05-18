import numpy as np
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    raw_score: float
    selection_probability: float


class ExponentialMechanism:

    def __init__(self, epsilon: float = 1.0, sensitivity: float = 1.0):
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        self._rng = np.random.default_rng()

    def _compute_probabilities(self, scores: np.ndarray) -> np.ndarray:
        scaled = (self.epsilon * scores) / (2.0 * self.sensitivity)
        scaled = scaled - np.max(scaled)
        exp_scores = np.exp(scaled)
        probabilities = exp_scores / np.sum(exp_scores)
        return probabilities

    def select(self, scores: np.ndarray, k: int = 5) -> List[int]:
        if len(scores) == 0:
            return []

        k = min(k, len(scores))
        probabilities = self._compute_probabilities(scores)

        selected = []
        remaining_indices = np.arange(len(scores))
        remaining_probs = probabilities.copy()

        for _ in range(k):
            if len(remaining_indices) == 0:
                break

            prob_sum = np.sum(remaining_probs)
            if prob_sum < 1e-15:
                break
            normalized = remaining_probs / prob_sum

            chosen_pos = self._rng.choice(len(remaining_indices), p=normalized)
            chosen_idx = remaining_indices[chosen_pos]
            selected.append(int(chosen_idx))

            remaining_indices = np.delete(remaining_indices, chosen_pos)
            remaining_probs = np.delete(remaining_probs, chosen_pos)

        return selected


class PrivateRetriever:

    def __init__(self, retrieval_epsilon: float = 2.0,
                 score_sensitivity: float = 1.0):
        self.exp_mechanism = ExponentialMechanism(
            epsilon=retrieval_epsilon,
            sensitivity=score_sensitivity,
        )

    def retrieve(self, query_embedding: np.ndarray,
                 stored_embeddings: np.ndarray,
                 metadata: List[dict],
                 top_k: int = 5) -> List[RetrievalResult]:

        if len(stored_embeddings) == 0:
            return []

        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 1e-10:
            query_normalized = query_embedding / query_norm
        else:
            query_normalized = query_embedding

        stored_norms = np.linalg.norm(stored_embeddings, axis=1, keepdims=True)
        stored_norms = np.maximum(stored_norms, 1e-10)
        stored_normalized = stored_embeddings / stored_norms

        scores = stored_normalized @ query_normalized

        selected_indices = self.exp_mechanism.select(scores, k=top_k)

        probabilities = self.exp_mechanism._compute_probabilities(scores)

        results = []
        for idx in selected_indices:
            meta = metadata[idx] if idx < len(metadata) else {}
            results.append(RetrievalResult(
                chunk_id=meta.get("chunk_id", f"chunk_{idx}"),
                file_path=meta.get("file_path", "unknown"),
                start_line=meta.get("start_line", 0),
                end_line=meta.get("end_line", 0),
                content=meta.get("content", ""),
                raw_score=float(scores[idx]),
                selection_probability=float(probabilities[idx]),
            ))

        results.sort(key=lambda r: r.raw_score, reverse=True)
        return results
