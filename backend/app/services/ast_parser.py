import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict

DLP_PATTERNS = [
    re.compile(r"(?i)(?:password|secret|key|token|api[_-]?key)[^\w]*(?:=|\:)[^\w]*['\"]?([a-zA-Z0-9_\-\.]{10,})['\"]?"),
    re.compile(r"AKIA[0-9A-Z]{16}")
]

@dataclass
class ParsedFile:
    path: str
    language: str
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    masked_content: str = ""
    token_map: Dict[str, str] = field(default_factory=dict)


PATTERNS = {
    "python": {
        "functions": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE),
        "classes": re.compile(r"^\s*class\s+(\w+)\s*[\(:]", re.MULTILINE),
        "imports": re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+(.+)", re.MULTILINE),
        "comments": re.compile(r"#\s*(.+)", re.MULTILINE),
    },
    "javascript": {
        "functions": re.compile(
            r"(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)",
            re.MULTILINE,
        ),
        "classes": re.compile(r"\bclass\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*import\s+(.+)", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
    "typescript": {
        "functions": re.compile(
            r"(?:(?:export\s+)?(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)",
            re.MULTILINE,
        ),
        "classes": re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*import\s+(.+)", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
    "java": {
        "functions": re.compile(
            r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+(?:\s*,\s*\w+)*)?\s*\{",
            re.MULTILINE,
        ),
        "classes": re.compile(r"(?:public\s+)?class\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*import\s+(.+);", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
    "go": {
        "functions": re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", re.MULTILINE),
        "classes": re.compile(r"^type\s+(\w+)\s+struct\s*\{", re.MULTILINE),
        "imports": re.compile(r"\"([^\"]+)\"", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
    "c": {
        "functions": re.compile(
            r"^[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE
        ),
        "classes": re.compile(r"typedef\s+struct\s*(?:\w+\s*)?\{[^}]*\}\s*(\w+)", re.MULTILINE | re.DOTALL),
        "imports": re.compile(r"#include\s+[<\"]([^>\"]+)[>\"]", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
    "cpp": {
        "functions": re.compile(
            r"^[\w\s\*:&<>]+\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{", re.MULTILINE
        ),
        "classes": re.compile(r"\bclass\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"#include\s+[<\"]([^>\"]+)[>\"]", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
    "rust": {
        "functions": re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE),
        "classes": re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*use\s+(.+);", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
    "ruby": {
        "functions": re.compile(r"^\s*def\s+(\w+)", re.MULTILINE),
        "classes": re.compile(r"^\s*class\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*require\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
        "comments": re.compile(r"#\s*(.+)", re.MULTILINE),
    },
    "php": {
        "functions": re.compile(r"^\s*(?:public|private|protected|static\s+)*function\s+(\w+)", re.MULTILINE),
        "classes": re.compile(r"^\s*class\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*use\s+(.+);", re.MULTILINE),
        "comments": re.compile(r"//\s*(.+)|/\*\s*(.*?)\s*\*/", re.MULTILINE | re.DOTALL),
    },
}

def parse_file(file_path: str, language: str, content: Optional[str] = None) -> ParsedFile:
    
    if content is None:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    for dlp_regex in DLP_PATTERNS:
        if dlp_regex.search(content):
            raise ValueError(f"DLP Violation: Sensitive information detected and blocked in {file_path}")

    patterns = PATTERNS.get(language)
    if patterns is None:
        return ParsedFile(path=file_path, language=language, masked_content=content)

    functions = []
    classes = []
    imports = []
    comments = []
    token_map = {}
    masked_content = content

    for match in patterns["classes"].finditer(content):
        original_name = match.group(1)
        if original_name and original_name not in token_map.values():
            token = f"class_{uuid.uuid4().hex[:8]}"
            token_map[token] = original_name
            classes.append(original_name)
            masked_content = re.sub(r"\b" + re.escape(original_name) + r"\b", token, masked_content)

    for match in patterns["functions"].finditer(content):
        original_name = next((g for g in match.groups() if g is not None), None)
        if original_name and original_name not in token_map.values():
            token = f"func_{uuid.uuid4().hex[:8]}"
            token_map[token] = original_name
            functions.append(original_name)
            masked_content = re.sub(r"\b" + re.escape(original_name) + r"\b", token, masked_content)

    imports = [m.group(1).strip() for m in patterns["imports"].finditer(content)]
    comments = [m.group(1).strip() for m in patterns["comments"].finditer(content)][:50]

    return ParsedFile(
        path=file_path,
        language=language,
        functions=functions,
        classes=classes,
        imports=imports,
        comments=comments,
        masked_content=masked_content,
        token_map=token_map,
    )
