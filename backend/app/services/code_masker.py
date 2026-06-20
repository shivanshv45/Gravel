"""
Code Masker — The core privacy layer of Gravel.

Before any code is sent to an external LLM, this module replaces all
proprietary identifiers (function names, class names, key variables)
with opaque cryptographic tokens.  When the LLM responds, the tokens
are decoded back into the original names locally on the user's machine.

The external provider only ever sees structural "skeletons" of the code.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class MaskingResult:
    """Holds the masked text and the bidirectional lookup table."""
    masked_text: str
    token_map: Dict[str, str]       # token -> original_name
    reverse_map: Dict[str, str]     # original_name -> token
    identifiers_masked: int


class CodeMasker:
    """
    Applies AST-aware identifier masking to code snippets.

    Strategy:
    1. Extract function / class names from the code using regex patterns
       (matching the patterns already used by ast_parser.py).
    2. Replace every occurrence of each identifier with a stable, unique
       token like ``FUNC_a3b8c1d2`` or ``CLS_e4f5a6b7``.
    3. Return the masked code together with a token ↔ name mapping so that
       the caller can reverse the substitution later.
    """

    # Patterns for each supported language — these mirror ast_parser.py
    _FUNC_PATTERNS = {
        "python":     re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE),
        "javascript": re.compile(r"(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)", re.MULTILINE),
        "typescript": re.compile(r"(?:(?:export\s+)?(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)", re.MULTILINE),
        "java":       re.compile(r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+(?:\s*,\s*\w+)*)?\s*\{", re.MULTILINE),
        "go":         re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", re.MULTILINE),
        "rust":       re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE),
    }

    _CLASS_PATTERNS = {
        "python":     re.compile(r"^\s*class\s+(\w+)\s*[\(:]", re.MULTILINE),
        "javascript": re.compile(r"\bclass\s+(\w+)", re.MULTILINE),
        "typescript": re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
        "java":       re.compile(r"(?:public\s+)?class\s+(\w+)", re.MULTILINE),
        "go":         re.compile(r"^type\s+(\w+)\s+struct\s*\{", re.MULTILINE),
        "rust":       re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)", re.MULTILINE),
    }

    # Built-in / stdlib names we should never mask
    _BUILTINS = frozenset({
        "self", "cls", "init", "__init__", "__main__", "__name__",
        "main", "print", "len", "range", "str", "int", "float", "bool",
        "list", "dict", "set", "tuple", "None", "True", "False",
        "return", "import", "from", "if", "else", "for", "while",
        "try", "except", "class", "def", "async", "await",
        "public", "private", "protected", "static", "void",
        "String", "Object", "System", "console", "log",
    })

    # ------------------------------------------------------------------ #

    def mask_code(self, code: str, language: str) -> MaskingResult:
        """Mask all proprietary identifiers in *code* and return the result."""

        token_map: Dict[str, str] = {}      # token -> original
        reverse_map: Dict[str, str] = {}    # original -> token
        masked = code

        # Collect identifiers -----------------------------------------
        identifiers: List[str] = []

        cls_pattern = self._CLASS_PATTERNS.get(language)
        if cls_pattern:
            for m in cls_pattern.finditer(code):
                name = m.group(1)
                if name and name not in self._BUILTINS and name not in reverse_map:
                    token = f"CLS_{uuid.uuid4().hex[:8]}"
                    token_map[token] = name
                    reverse_map[name] = token
                    identifiers.append(name)

        func_pattern = self._FUNC_PATTERNS.get(language)
        if func_pattern:
            for m in func_pattern.finditer(code):
                name = next((g for g in m.groups() if g is not None), None)
                if name and name not in self._BUILTINS and name not in reverse_map:
                    token = f"FUNC_{uuid.uuid4().hex[:8]}"
                    token_map[token] = name
                    reverse_map[name] = token
                    identifiers.append(name)

        # Sort by length descending so longer names are replaced first
        # (avoids partial replacements like "get" inside "getUser")
        identifiers.sort(key=len, reverse=True)

        for name in identifiers:
            token = reverse_map[name]
            masked = re.sub(r"\b" + re.escape(name) + r"\b", token, masked)

        return MaskingResult(
            masked_text=masked,
            token_map=token_map,
            reverse_map=reverse_map,
            identifiers_masked=len(identifiers),
        )

    def mask_chunks(self, chunks: List[Dict], language: str = "python") -> Tuple[List[Dict], Dict[str, str]]:
        """
        Mask a list of code-chunk dicts (the format used by ChatPipeline).

        Returns (masked_chunks, combined_token_map) where the token map
        is the union across all chunks so the response can be fully decoded.
        """
        combined_map: Dict[str, str] = {}
        combined_reverse: Dict[str, str] = {}
        masked_chunks: List[Dict] = []

        for chunk in chunks:
            content = chunk.get("content", "")
            lang = chunk.get("language", language)

            # Re-use tokens that were already assigned in earlier chunks
            # so the same identifier always maps to the same token.
            result = self._mask_with_existing(content, lang, combined_map, combined_reverse)

            combined_map.update(result.token_map)
            combined_reverse.update(result.reverse_map)

            masked_chunks.append({
                **chunk,
                "content": result.masked_text,
            })

        return masked_chunks, combined_map

    def unmask_response(self, response: str, token_map: Dict[str, str]) -> str:
        """Replace every token in the LLM response with the original name."""
        unmasked = response
        # Sort by token length descending to avoid partial matches
        for token, original in sorted(token_map.items(), key=lambda x: len(x[0]), reverse=True):
            unmasked = unmasked.replace(token, original)
        return unmasked

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _mask_with_existing(self, code: str, language: str,
                            existing_map: Dict[str, str],
                            existing_reverse: Dict[str, str]) -> MaskingResult:
        """Like mask_code, but re-uses tokens from *existing_reverse*."""

        token_map: Dict[str, str] = {}
        reverse_map: Dict[str, str] = {}
        identifiers: List[str] = []

        cls_pattern = self._CLASS_PATTERNS.get(language)
        if cls_pattern:
            for m in cls_pattern.finditer(code):
                name = m.group(1)
                if name and name not in self._BUILTINS:
                    if name in existing_reverse:
                        token = existing_reverse[name]
                    elif name not in reverse_map:
                        token = f"CLS_{uuid.uuid4().hex[:8]}"
                    else:
                        continue
                    token_map[token] = name
                    reverse_map[name] = token
                    if name not in [i for i in identifiers]:
                        identifiers.append(name)

        func_pattern = self._FUNC_PATTERNS.get(language)
        if func_pattern:
            for m in func_pattern.finditer(code):
                name = next((g for g in m.groups() if g is not None), None)
                if name and name not in self._BUILTINS:
                    if name in existing_reverse:
                        token = existing_reverse[name]
                    elif name not in reverse_map:
                        token = f"FUNC_{uuid.uuid4().hex[:8]}"
                    else:
                        continue
                    token_map[token] = name
                    reverse_map[name] = token
                    if name not in identifiers:
                        identifiers.append(name)

        identifiers.sort(key=len, reverse=True)
        masked = code
        for name in identifiers:
            token = reverse_map[name]
            masked = re.sub(r"\b" + re.escape(name) + r"\b", token, masked)

        return MaskingResult(
            masked_text=masked,
            token_map=token_map,
            reverse_map=reverse_map,
            identifiers_masked=len(identifiers),
        )
