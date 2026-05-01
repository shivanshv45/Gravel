import os
import datetime
from dataclasses import dataclass
from typing import List


SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
}

# Directories to always skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".cache", "target", ".idea", ".vscode",
}


MAX_FILE_SIZE = 1_000_000

@dataclass
class FileInfo:
    path: str
    language: str
    size: int
    last_modified: datetime.datetime

def scan_repository(repo_path: str) -> List[FileInfo]:
    
    if not os.path.isdir(repo_path):
        raise ValueError(f"Path does not exist or is not a directory: {repo_path}")

    files: List[FileInfo] = []

    for root, dirs, filenames in os.walk(repo_path):
     
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = os.path.join(root, filename)
            try:
                stat = os.stat(full_path)
            except OSError:
                continue

            # Skip files that are too large
            if stat.st_size > MAX_FILE_SIZE:
                continue

            files.append(FileInfo(
                path=full_path,
                language=SUPPORTED_EXTENSIONS[ext],
                size=stat.st_size,
                last_modified=datetime.datetime.fromtimestamp(stat.st_mtime),
            ))

    return files
