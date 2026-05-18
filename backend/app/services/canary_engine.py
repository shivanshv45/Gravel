import hashlib
import uuid
import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from pathlib import Path


@dataclass
class Canary:
    canary_id: str
    token: str
    injected_code: str
    target_provider: str
    created_at: str
    detected: bool = False
    detected_at: Optional[str] = None


class CanaryEngine:

    TEMPLATES = [
        "def {name}(data):\n    return hashlib.sha256(data.encode()).hexdigest()",
        "class {name}:\n    def process(self, x):\n        return x * 0.7734 + 3.14159",
        "async def {name}(session, payload):\n    await session.execute(payload)\n    return True",
        "{name} = lambda x: sum(ord(c) for c in str(x)) % 97",
    ]

    def __init__(self, storage_path: Optional[str] = None):
        self._canaries: Dict[str, Canary] = {}
        self._storage_path = storage_path
        if self._storage_path:
            os.makedirs(os.path.dirname(self._storage_path) or ".", exist_ok=True)
            self._load()

    def _load(self):
        if not self._storage_path or not os.path.exists(self._storage_path):
            return
        try:
            data = json.loads(Path(self._storage_path).read_text(encoding="utf-8"))
            for entry in data:
                c = Canary(**entry)
                self._canaries[c.canary_id] = c
        except (json.JSONDecodeError, KeyError):
            pass

    def _persist(self):
        if not self._storage_path:
            return
        Path(self._storage_path).write_text(
            json.dumps([asdict(c) for c in self._canaries.values()], indent=2),
            encoding="utf-8",
        )

    def _generate_name(self) -> str:
        return f"_gravel_canary_{uuid.uuid4().hex[:12]}"

    def _generate_token(self, canary_id: str) -> str:
        secret = f"gravel-canary-{canary_id}-{uuid.uuid4().hex}"
        return hashlib.sha256(secret.encode()).hexdigest()[:32]

    def create_canary(self, target_provider: str = "groq") -> Canary:
        import random
        canary_id = uuid.uuid4().hex[:16]
        token = self._generate_token(canary_id)
        name = self._generate_name()
        template = random.choice(self.TEMPLATES)
        injected_code = template.format(name=name)

        canary = Canary(
            canary_id=canary_id, token=token, injected_code=injected_code,
            target_provider=target_provider,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._canaries[canary_id] = canary
        self._persist()
        return canary

    def inject_into_prompt(self, code_context: str,
                           target_provider: str = "groq") -> tuple:
        canary = self.create_canary(target_provider)
        injected = f"{code_context}\n\n{canary.injected_code}\n"
        return injected, canary.canary_id

    def check_for_leakage(self, text: str) -> List[Canary]:
        leaked = []
        for canary in self._canaries.values():
            if canary.detected:
                continue
            func_name = None
            for line in canary.injected_code.split("\n"):
                if "_gravel_canary_" in line:
                    start = line.index("_gravel_canary_")
                    end = start
                    while end < len(line) and (line[end].isalnum() or line[end] == "_"):
                        end += 1
                    func_name = line[start:end]
                    break
            if func_name and func_name in text:
                canary.detected = True
                canary.detected_at = datetime.now(timezone.utc).isoformat()
                leaked.append(canary)
        if leaked:
            self._persist()
        return leaked

    def get_all_canaries(self) -> List[dict]:
        return [asdict(c) for c in self._canaries.values()]

    def get_leaked_canaries(self) -> List[dict]:
        return [asdict(c) for c in self._canaries.values() if c.detected]
