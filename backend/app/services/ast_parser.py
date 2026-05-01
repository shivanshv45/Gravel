import re
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ParsedFile:
    path: str
    language: str
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)


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
        "comments": re.compile(r"
    },
    "typescript": {
        "functions": re.compile(
            r"(?:(?:export\s+)?(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)",
            re.MULTILINE,
        ),
        "classes": re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*import\s+(.+)", re.MULTILINE),
        "comments": re.compile(r"
    },
    "java": {
        "functions": re.compile(
            r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+(?:\s*,\s*\w+)*)?\s*\{",
            re.MULTILINE,
        ),
        "classes": re.compile(r"(?:public\s+)?class\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*import\s+(.+);", re.MULTILINE),
        "comments": re.compile(r"
    },
    "go": {
        "functions": re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", re.MULTILINE),
        "classes": re.compile(r"^type\s+(\w+)\s+struct\s*\{", re.MULTILINE),
        "imports": re.compile(r"\"([^\"]+)\"", re.MULTILINE),
        "comments": re.compile(r"
    },
    "c": {
        "functions": re.compile(
            r"^[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE
        ),
        "classes": re.compile(r"typedef\s+struct\s*(?:\w+\s*)?\{[^}]*\}\s*(\w+)", re.MULTILINE | re.DOTALL),
        "imports": re.compile(r"#include\s+[<\"]([^>\"]+)[>\"]", re.MULTILINE),
        "comments": re.compile(r"
    },
    "cpp": {
        "functions": re.compile(
            r"^[\w\s\*:&<>]+\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{", re.MULTILINE
        ),
        "classes": re.compile(r"\bclass\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"#include\s+[<\"]([^>\"]+)[>\"]", re.MULTILINE),
        "comments": re.compile(r"
    },
    "rust": {
        "functions": re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE),
        "classes": re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)", re.MULTILINE),
        "imports": re.compile(r"^\s*use\s+(.+);", re.MULTILINE),
        "comments": re.compile(r"
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
        "comments": re.compile(r"
    },
}

def parse_file(file_path: str, language: str, content: Optional[str] = None) -> ParsedFile:
    
    if content is None:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    patterns = PATTERNS.get(language)
    if patterns is None:
        
        return ParsedFile(path=file_path, language=language)


    functions = []
    for match in patterns["functions"].finditer(content):
        name = next((g for g in match.groups() if g is not None), None)
        if name:
            functions.append(name)
    classes = [m.group(1) for m in patterns["classes"].finditer(content)]

    
    imports = [m.group(1).strip() for m in patterns["imports"].finditer(content)]

    
    comments = [m.group(1).strip() for m in patterns["comments"].finditer(content)][:50]

    return ParsedFile(
        path=file_path,
        language=language,
        functions=functions,
        classes=classes,
        imports=imports,
        comments=comments,
    )
