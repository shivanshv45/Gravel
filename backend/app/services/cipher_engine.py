"""
Gravel Fixed Cipher Engine
===========================
Deterministic keyword-derived substitution cipher.
Only letters (a-z, A-Z) and digits (0-9) are substituted.
All punctuation, brackets, operators, whitespace stay intact
so the LLM can still parse code structure.

The cipher table is derived from a secret key using SHA-256
seeded shuffle -- standard B.Tech cryptography approach.
"""

import hashlib
import random
import string
import uuid
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger("gravel.cipher")

SECRET_KEY = "gravel_privacy_2026"


@dataclass
class CipherSession:
    session_id: str
    enc_table: dict
    dec_table: dict
    validation_plain: str
    validation_encrypted: str


class CipherEngine:

    # ── Fixed cipher table (derived from secret key) ──

    @staticmethod
    def _build_tables(key: str):
        seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        lower = list(string.ascii_lowercase)
        shuf_lower = lower.copy(); rng.shuffle(shuf_lower)

        upper = list(string.ascii_uppercase)
        shuf_upper = upper.copy(); rng.shuffle(shuf_upper)

        digits = list(string.digits)
        shuf_digits = digits.copy(); rng.shuffle(shuf_digits)

        src = ''.join(lower + upper + digits)
        dst = ''.join(shuf_lower + shuf_upper + shuf_digits)

        enc = str.maketrans(src, dst)
        dec = str.maketrans(dst, src)
        return enc, dec

    ENC_TABLE, DEC_TABLE = None, None

    @classmethod
    def _ensure_tables(cls):
        if cls.ENC_TABLE is None:
            cls.ENC_TABLE, cls.DEC_TABLE = cls._build_tables(SECRET_KEY)

    # ── Validation snippets (weird code the LLM can't predict) ──

    VALIDATION_BANK = [
        "def zulu_check_99(alpha, beta):\n    gamma = alpha ^ beta\n    return gamma % 7 == 0",
        "def xray_ping_42(host, port=3301):\n    return f\"{host}:{port}\"",
        "QUOTA_MAX = 7788\ndef verify_quota(used):\n    return used <= QUOTA_MAX",
    ]

    # ── Few-shot examples (cover all 62 chars a-z A-Z 0-9) ──

    FEW_SHOT_EXAMPLES = [
        {
            "code": (
                'def quick_sort(arr):\n'
                '    pivot = arr[0]\n'
                '    left = [x for x in arr if x < pivot]\n'
                '    right = [x for x in arr if x > pivot]\n'
                '    return quick_sort(left) + [pivot] + quick_sort(right)'
            ),
            "meaning": (
                "Recursive quick sort picking first element as pivot, "
                "splitting into left and right sublists."
            ),
        },
        {
            "code": (
                'MAX_VALUE = 9876\nTIMEOUT = 5310\n'
                'class HTTPServer:\n'
                '    VERSION = "2.4"\n'
                '    def __init__(self, host, port=8080):\n'
                '        self.host = host'
            ),
            "meaning": (
                "Sets MAX_VALUE to 9876, TIMEOUT to 5310. "
                "HTTPServer has VERSION 2.4, takes host and port defaulting to 8080."
            ),
        },
        {
            "code": (
                'import json\n'
                'def fuzzy_match(query, items):\n'
                '    results = []\n'
                '    for idx, item in enumerate(items):\n'
                '        results.append({"index": idx, "value": item})\n'
                '    return sorted(results, key=lambda r: r["index"])'
            ),
            "meaning": (
                "Imports json. fuzzy_match loops items with enumerate, "
                "builds dicts with index and value, returns sorted by index."
            ),
        },
        {
            "code": (
                'DATABASE_URL = "postgres://localhost:5432"\n'
                'GZIP_ENABLED = True\nQUOTA_LIMIT = 500\n'
                'def analyze(text):\n'
                '    words = text.split()\n'
                '    return {"count": len(words), "unique": len(set(words))}'
            ),
            "meaning": (
                "DATABASE_URL points to postgres on 5432. GZIP enabled, QUOTA is 500. "
                "analyze splits text, returns word count and unique count."
            ),
        },
        {
            "code": (
                'FILE_KEY = "xyz_wuz"\nCACHE_SIZE = 1024\n'
                'def JoinWordsYearly(chunks):\n'
                '    return " ".join(chunks)'
            ),
            "meaning": (
                "FILE_KEY is xyz_wuz. CACHE_SIZE is 1024. "
                "JoinWordsYearly joins chunks with spaces."
            ),
        },
    ]

    # ── Core encrypt / decrypt ──

    def encrypt(self, text: str) -> str:
        self._ensure_tables()
        return text.translate(self.ENC_TABLE)

    def decrypt(self, text: str) -> str:
        self._ensure_tables()
        return text.translate(self.DEC_TABLE)

    # ── Session management ──

    def create_session(self, language="python") -> CipherSession:
        self._ensure_tables()
        session_id = uuid.uuid4().hex[:12]

        val_plain = random.choice(self.VALIDATION_BANK)
        val_encrypted = self.encrypt(val_plain)

        return CipherSession(
            session_id=session_id,
            enc_table=self.ENC_TABLE,
            dec_table=self.DEC_TABLE,
            validation_plain=val_plain,
            validation_encrypted=val_encrypted,
        )

    # ── Encrypt chunks ──

    def encrypt_chunks(self, chunks: List[Dict], session: CipherSession = None) -> List[Dict]:
        encrypted = []
        for chunk in chunks:
            encrypted.append({
                **chunk,
                "content": self.encrypt(chunk.get("content", "")),
                "file_path": self.encrypt(chunk.get("file_path", "")),
            })
        return encrypted

    # ── Build system prompt ──

    def build_system_prompt(self, session: CipherSession) -> str:
        blocks = []
        for i, ex in enumerate(self.FEW_SHOT_EXAMPLES, 1):
            enc_code = self.encrypt(ex["code"])
            blocks.append(
                f"Example {i}:\n"
                f"Encrypted code:\n{enc_code}\n\n"
                f"What this code actually does (plain English):\n{ex['meaning']}"
            )

        examples_text = "\n\n---\n\n".join(blocks)

        return (
            "You are Gravel, a privacy-first code analysis AI.\n\n"
            "The code you receive has been encrypted with a character substitution cipher "
            "to protect intellectual property.\n"
            "Only letters (a-z, A-Z) and digits (0-9) are substituted. "
            "Punctuation, brackets, operators, colons, dots, quotes, and whitespace are NOT changed.\n\n"
            "Here are examples of encrypted code alongside what the code actually means. "
            "Use these to learn the substitution pattern:\n\n"
            f"{examples_text}\n\n"
            "---\n\n"
            "YOUR TASK:\n"
            "1. You will receive encrypted code snippets and an encrypted question.\n"
            "2. Use the pattern you learned to mentally decrypt the code and the question.\n"
            "3. Answer the question in PLAIN ENGLISH based on what the code does.\n"
            "4. You will also receive a short encrypted validation snippet. "
            "Decrypt it back to the EXACT original code, character by character.\n\n"
            "Respond with a JSON object with two fields:\n"
            "- \"answer\": your plain English answer to the decrypted question\n"
            "- \"validation\": the EXACT decrypted code of the validation snippet "
            "(not an explanation, the actual decrypted code)"
        )

    # ── Build user prompt ──

    def build_user_prompt(self, question: str, encrypted_chunks: List[Dict],
                          session: CipherSession) -> str:
        context_parts = []
        for chunk in encrypted_chunks:
            context_parts.append(
                f"--- {chunk['file_path']} "
                f"(lines {chunk['start_line']}-{chunk['end_line']}) ---\n"
                f"{chunk['content']}"
            )

        context_block = "\n\n".join(context_parts)
        enc_question = self.encrypt(question)

        return (
            f"Encrypted project code:\n\n"
            f"{context_block}\n\n"
            f"Encrypted question: {enc_question}\n\n"
            f"Encrypted validation snippet (decrypt this back to the original code exactly):\n"
            f"{session.validation_encrypted}"
        )

    # ── Parse response (JSON) ──

    def parse_response(self, raw_response: str) -> Tuple[str, str]:
        answer = ""
        validation = ""

        try:
            parsed = json.loads(raw_response)
            answer = parsed.get("answer", "")
            validation = parsed.get("validation", "")
        except json.JSONDecodeError:
            # Fallback: extract from truncated JSON
            import re
            ans_match = re.search(r'"answer"\s*:\s*"(.*?)"', raw_response, re.DOTALL)
            val_match = re.search(r'"validation"\s*:\s*"(.*?)(?:"|$)', raw_response, re.DOTALL)
            if ans_match:
                answer = ans_match.group(1).replace('\\"', '"').replace('\\n', '\n')
            if val_match:
                validation = val_match.group(1).replace('\\"', '"').replace('\\n', '\n')

        return answer, validation

    # ── Validate response (exact decryption match) ──

    def validate_response(self, validation_text: str, session: CipherSession) -> float:
        if not validation_text or not session.validation_plain:
            return 0.0

        import re
        import difflib

        # Normalize whitespace to avoid penalizing indentation differences
        got = re.sub(r'\s+', ' ', validation_text.strip())
        expected = re.sub(r'\s+', ' ', session.validation_plain.strip())

        # Use SequenceMatcher to get a character-level similarity ratio (0.0 to 1.0)
        matcher = difflib.SequenceMatcher(None, got, expected)
        similarity = matcher.ratio()

        return similarity

    # ── Build JSON response format for API call ──

    def get_response_format(self) -> dict:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "cipher_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "Your answer to the encrypted question, in plain English"
                        },
                        "validation": {
                            "type": "string",
                            "description": "The exact decrypted code of the validation snippet"
                        }
                    },
                    "required": ["answer", "validation"],
                    "additionalProperties": False
                }
            }
        }
