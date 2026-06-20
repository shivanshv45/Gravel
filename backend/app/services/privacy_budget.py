import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path


class PrivacyBudgetExhausted(Exception):
    pass


@dataclass
class BudgetEntry:
    timestamp: str
    epsilon_spent: float
    operation: str
    file_path: Optional[str] = None
    chunk_id: Optional[str] = None


@dataclass
class RepoBudget:
    repo_id: int
    total_epsilon: float = 1000.0
    entries: List[BudgetEntry] = field(default_factory=list)

    @property
    def epsilon_spent(self) -> float:
        return sum(e.epsilon_spent for e in self.entries)

    @property
    def epsilon_remaining(self) -> float:
        return max(0.0, self.total_epsilon - self.epsilon_spent)

    @property
    def utilization_pct(self) -> float:
        if self.total_epsilon <= 0:
            return 100.0
        return min(100.0, (self.epsilon_spent / self.total_epsilon) * 100.0)

    def can_spend(self, epsilon: float) -> bool:
        return self.epsilon_remaining >= epsilon

    def spend(self, epsilon: float, operation: str,
              file_path: Optional[str] = None,
              chunk_id: Optional[str] = None) -> BudgetEntry:
        if not self.can_spend(epsilon):
            raise PrivacyBudgetExhausted(
                f"Budget exhausted for repo {self.repo_id}. "
                f"Remaining: {self.epsilon_remaining:.6f}, "
                f"Requested: {epsilon:.6f}"
            )

        entry = BudgetEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            epsilon_spent=epsilon,
            operation=operation,
            file_path=file_path,
            chunk_id=chunk_id,
        )
        self.entries.append(entry)
        return entry

    def to_dict(self) -> dict:
        return {
            "repo_id": self.repo_id,
            "total_epsilon": self.total_epsilon,
            "epsilon_spent": self.epsilon_spent,
            "epsilon_remaining": self.epsilon_remaining,
            "utilization_pct": self.utilization_pct,
            "num_operations": len(self.entries),
            "entries": [asdict(e) for e in self.entries],
        }


class PrivacyBudgetManager:

    def __init__(self, storage_dir: Optional[str] = None):
        self._budgets: dict[int, RepoBudget] = {}
        self._lock = threading.RLock()
        self._storage_dir = storage_dir

        if self._storage_dir:
            os.makedirs(self._storage_dir, exist_ok=True)
            self._load_all()

    def _budget_path(self, repo_id: int) -> Path:
        return Path(self._storage_dir) / f"budget_repo_{repo_id}.json"

    def _load_all(self):
        if not self._storage_dir:
            return
        storage = Path(self._storage_dir)
        for f in storage.glob("budget_repo_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                repo_id = data["repo_id"]
                budget = RepoBudget(
                    repo_id=repo_id,
                    total_epsilon=data["total_epsilon"],
                    entries=[BudgetEntry(**e) for e in data.get("entries", [])],
                )
                self._budgets[repo_id] = budget
            except (json.JSONDecodeError, KeyError):
                continue

    def _persist(self, repo_id: int):
        if not self._storage_dir:
            return
        budget = self._budgets.get(repo_id)
        if budget:
            path = self._budget_path(repo_id)
            path.write_text(
                json.dumps(budget.to_dict(), indent=2),
                encoding="utf-8",
            )

    def get_or_create(self, repo_id: int, total_epsilon: float = 1000.0) -> RepoBudget:
        with self._lock:
            if repo_id not in self._budgets:
                self._budgets[repo_id] = RepoBudget(
                    repo_id=repo_id,
                    total_epsilon=total_epsilon,
                )
            return self._budgets[repo_id]

    def spend(self, repo_id: int, epsilon: float, operation: str,
              file_path: Optional[str] = None,
              chunk_id: Optional[str] = None) -> BudgetEntry:
        with self._lock:
            budget = self.get_or_create(repo_id)
            entry = budget.spend(epsilon, operation, file_path, chunk_id)
            self._persist(repo_id)
            return entry

    def spend_batch(self, repo_id: int, epsilon_per_op: float,
                    operations: List[dict]):
        """Record multiple budget entries with a single disk write."""
        with self._lock:
            budget = self.get_or_create(repo_id)
            total_needed = epsilon_per_op * len(operations)
            if not budget.can_spend(total_needed):
                raise PrivacyBudgetExhausted(
                    f"Budget exhausted for repo {repo_id}. "
                    f"Remaining: {budget.epsilon_remaining:.6f}, "
                    f"Requested: {total_needed:.6f}"
                )
            for op in operations:
                budget.spend(
                    epsilon_per_op,
                    op.get("operation", "index_chunk"),
                    op.get("file_path"),
                    op.get("chunk_id"),
                )
            # Single disk write at the end
            self._persist(repo_id)

    def get_status(self, repo_id: int) -> dict:
        with self._lock:
            budget = self.get_or_create(repo_id)
            return budget.to_dict()

    def reset(self, repo_id: int, new_total: Optional[float] = None):
        with self._lock:
            old = self._budgets.get(repo_id)
            total = new_total or (old.total_epsilon if old else 10.0)
            self._budgets[repo_id] = RepoBudget(
                repo_id=repo_id,
                total_epsilon=total,
            )
            self._persist(repo_id)

    def all_budgets(self) -> List[dict]:
        with self._lock:
            return [b.to_dict() for b in self._budgets.values()]
