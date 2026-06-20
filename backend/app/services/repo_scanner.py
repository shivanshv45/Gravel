import os
import datetime
import fnmatch
import logging
from dataclasses import dataclass
from typing import List, Set

logger = logging.getLogger("gravel.scanner")

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

# Directories to always skip regardless of .gitignore
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".cache", "target", ".idea", ".vscode",
    ".pytest_cache", ".mypy_cache", ".tox", ".eggs", "egg-info",
    ".gradle", ".maven", "vendor", "bower_components",
    ".nuxt", ".output", ".vercel", ".netlify", ".serverless",
    "coverage", ".nyc_output", "htmlcov",
    ".terraform", ".docker", ".vagrant",
    "bin", "obj",  # C#/.NET build output
    ".cargo",  # Rust build cache
    ".bundle",  # Ruby bundler
}

# File patterns to always skip
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", "Cargo.lock",
    "go.sum", "Gemfile.lock", "composer.lock",
    ".DS_Store", "Thumbs.db",
    ".env", ".env.local", ".env.production",
}

# Extensions to always skip (binary / generated / non-code)
SKIP_EXTENSIONS = {
    ".min.js", ".min.css", ".map",
    ".pyc", ".pyo", ".class", ".o", ".obj",
    ".dll", ".so", ".dylib", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".db", ".sqlite", ".sqlite3",
}

MAX_FILE_SIZE = 500_000  # 500KB (down from 1MB to skip huge generated files)


@dataclass
class FileInfo:
    path: str
    language: str
    size: int
    last_modified: datetime.datetime


def _parse_gitignore(repo_path: str) -> List[str]:
    """Parse .gitignore file and return a list of patterns."""
    gitignore_path = os.path.join(repo_path, ".gitignore")
    patterns = []
    if not os.path.isfile(gitignore_path):
        return patterns

    try:
        with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    except OSError:
        pass

    return patterns


def _is_gitignored(rel_path: str, patterns: List[str]) -> bool:
    """Check if a relative path matches any .gitignore pattern."""
    # Normalize to forward slashes for matching
    rel_path_fwd = rel_path.replace("\\", "/")

    for pattern in patterns:
        pattern = pattern.rstrip("/")

        # Direct filename match
        basename = os.path.basename(rel_path_fwd)
        if fnmatch.fnmatch(basename, pattern):
            return True

        # Path match
        if fnmatch.fnmatch(rel_path_fwd, pattern):
            return True

        # Match with wildcard prefix (e.g. "*.log" should match "dir/foo.log")
        if fnmatch.fnmatch(rel_path_fwd, f"**/{pattern}"):
            return True

        # Directory prefix match (e.g. "logs/" should match "logs/foo.txt")
        if rel_path_fwd.startswith(pattern + "/") or rel_path_fwd.startswith(pattern):
            return True

        # Check each path component
        parts = rel_path_fwd.split("/")
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True

    return False


def scan_repository(repo_path: str) -> List[FileInfo]:
    if not os.path.isdir(repo_path):
        raise ValueError(f"Path does not exist or is not a directory: {repo_path}")

    # Parse .gitignore
    gitignore_patterns = _parse_gitignore(repo_path)
    if gitignore_patterns:
        logger.info(f"  Loaded {len(gitignore_patterns)} .gitignore patterns")

    files: List[FileInfo] = []
    skipped_dirs = 0
    skipped_files = 0

    for root, dirs, filenames in os.walk(repo_path):
        # Prune hardcoded skip dirs
        original_dir_count = len(dirs)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        # Prune .gitignore'd dirs
        if gitignore_patterns:
            kept_dirs = []
            for d in dirs:
                rel_dir = os.path.relpath(os.path.join(root, d), repo_path)
                if _is_gitignored(rel_dir, gitignore_patterns):
                    skipped_dirs += 1
                else:
                    kept_dirs.append(d)
            dirs[:] = kept_dirs

        skipped_dirs += (original_dir_count - len(dirs))

        for filename in filenames:
            # Skip known non-code files
            if filename in SKIP_FILES:
                skipped_files += 1
                continue

            ext = os.path.splitext(filename)[1].lower()

            # Skip known binary / generated extensions
            if ext in SKIP_EXTENSIONS:
                skipped_files += 1
                continue

            # Only process supported source code extensions
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, repo_path)

            # Check .gitignore
            if gitignore_patterns and _is_gitignored(rel_path, gitignore_patterns):
                skipped_files += 1
                continue

            try:
                stat = os.stat(full_path)
            except OSError:
                continue

            # Skip files that are too large
            if stat.st_size > MAX_FILE_SIZE:
                skipped_files += 1
                logger.debug(f"  Skipped (too large): {rel_path} ({stat.st_size} bytes)")
                continue

            # Skip empty files
            if stat.st_size == 0:
                continue

            files.append(FileInfo(
                path=full_path,
                language=SUPPORTED_EXTENSIONS[ext],
                size=stat.st_size,
                last_modified=datetime.datetime.fromtimestamp(stat.st_mtime),
            ))

    logger.info(
        f"  Scan complete: {len(files)} files found, "
        f"{skipped_dirs} dirs skipped, {skipped_files} files skipped"
    )
    return files
