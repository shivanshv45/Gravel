import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CodeChunk:
    chunk_id: str
    file_path: str
    language: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str


class CodeChunker:

    MAX_CHUNK_TOKENS = 512
    OVERLAP_LINES = 3

    FUNCTION_PATTERNS = {
        "python": re.compile(r"^(\s*)(?:async\s+)?def\s+\w+", re.MULTILINE),
        "javascript": re.compile(r"^(\s*)(?:async\s+)?(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)", re.MULTILINE),
        "typescript": re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)", re.MULTILINE),
        "java": re.compile(r"^(\s*)(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*(?:throws\s+\w+(?:\s*,\s*\w+)*)?\s*\{", re.MULTILINE),
        "go": re.compile(r"^(\s*)func\s+", re.MULTILINE),
        "rust": re.compile(r"^(\s*)(?:pub\s+)?(?:async\s+)?fn\s+", re.MULTILINE),
    }

    CLASS_PATTERNS = {
        "python": re.compile(r"^(\s*)class\s+\w+", re.MULTILINE),
        "javascript": re.compile(r"^(\s*)class\s+\w+", re.MULTILINE),
        "typescript": re.compile(r"^(\s*)(?:export\s+)?class\s+\w+", re.MULTILINE),
        "java": re.compile(r"^(\s*)(?:public\s+)?class\s+\w+", re.MULTILINE),
        "go": re.compile(r"^(\s*)type\s+\w+\s+struct", re.MULTILINE),
        "rust": re.compile(r"^(\s*)(?:pub\s+)?struct\s+\w+", re.MULTILINE),
    }

    def chunk_file(self, file_path: str, content: str,
                   language: str) -> List[CodeChunk]:
        lines = content.split("\n")

        boundaries = self._find_boundaries(content, language)

        if not boundaries:
            return self._sliding_window(file_path, lines, language)

        chunks = []
        boundaries.sort()

        for i, start in enumerate(boundaries):
            if i + 1 < len(boundaries):
                end = boundaries[i + 1] - 1
            else:
                end = len(lines) - 1

            chunk_lines = lines[start:end + 1]
            chunk_content = "\n".join(chunk_lines)

            if len(chunk_content.split()) > self.MAX_CHUNK_TOKENS * 2:
                sub_chunks = self._sliding_window(
                    file_path, chunk_lines, language,
                    offset=start, chunk_type="function_split"
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(CodeChunk(
                    chunk_id=f"{file_path}:{start}-{end}",
                    file_path=file_path,
                    language=language,
                    content=chunk_content,
                    start_line=start + 1,
                    end_line=end + 1,
                    chunk_type="ast_boundary",
                ))

        return chunks

    def _find_boundaries(self, content: str, language: str) -> List[int]:
        boundaries = set()

        func_pattern = self.FUNCTION_PATTERNS.get(language)
        if func_pattern:
            for match in func_pattern.finditer(content):
                line_num = content[:match.start()].count("\n")
                boundaries.add(line_num)

        class_pattern = self.CLASS_PATTERNS.get(language)
        if class_pattern:
            for match in class_pattern.finditer(content):
                line_num = content[:match.start()].count("\n")
                boundaries.add(line_num)

        return sorted(boundaries)

    def _sliding_window(self, file_path: str, lines: List[str],
                        language: str, offset: int = 0,
                        chunk_type: str = "sliding_window") -> List[CodeChunk]:
        chunks = []
        window_size = 30
        step = window_size - self.OVERLAP_LINES
        i = 0

        while i < len(lines):
            end = min(i + window_size, len(lines))
            chunk_lines = lines[i:end]
            chunk_content = "\n".join(chunk_lines)

            if chunk_content.strip():
                chunks.append(CodeChunk(
                    chunk_id=f"{file_path}:{offset + i}-{offset + end - 1}",
                    file_path=file_path,
                    language=language,
                    content=chunk_content,
                    start_line=offset + i + 1,
                    end_line=offset + end,
                    chunk_type=chunk_type,
                ))

            if end >= len(lines):
                break
            i += step

        return chunks
