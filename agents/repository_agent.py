from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}

IMPORTANT_FILES = {
    "README.md",
    "README.rst",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    ".gitlab-ci.yml",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
}

CONFIG_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
}

TEST_PATTERNS = (
    "test_",
    "_test.",
    ".test.",
    ".spec.",
)


@dataclass
class RepositoryFile:
    path: str
    extension: str
    size_bytes: int
    category: str


@dataclass
class RepositorySummary:
    repository_name: str
    repository_path: str
    total_files: int
    source_files: int
    test_files: int
    config_files: int
    documentation_files: int
    languages: dict[str, int]
    important_files: list[str]
    files: list[RepositoryFile]


class RepositoryAgent:
    def __init__(self, repository_path: str | Path):
        self.repository_path = Path(repository_path).resolve()

        if not self.repository_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {self.repository_path}"
            )

        if not self.repository_path.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {self.repository_path}"
            )

    def analyze(self) -> RepositorySummary:
        files = self._scan_repository()

        languages: dict[str, int] = {}
        important_files: list[str] = []

        source_files = 0
        test_files = 0
        config_files = 0
        documentation_files = 0

        for file in files:
            if file.category == "source":
                source_files += 1

                if file.extension:
                    languages[file.extension] = languages.get(file.extension, 0) + 1

            elif file.category == "test":
                test_files += 1

            elif file.category == "config":
                config_files += 1

            elif file.category == "documentation":
                documentation_files += 1

            if Path(file.path).name in IMPORTANT_FILES:
                important_files.append(file.path)

        return RepositorySummary(
            repository_name=self.repository_path.name,
            repository_path=str(self.repository_path),
            total_files=len(files),
            source_files=source_files,
            test_files=test_files,
            config_files=config_files,
            documentation_files=documentation_files,
            languages=dict(
                sorted(
                    languages.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ),
            important_files=sorted(important_files),
            files=files,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.analyze())

    def get_tree(self, max_depth: int = 3) -> str:
        lines = [self.repository_path.name + "/"]
        self._build_tree(
            directory=self.repository_path,
            lines=lines,
            prefix="",
            depth=0,
            max_depth=max_depth,
        )
        return "\n".join(lines)

    def _scan_repository(self) -> list[RepositoryFile]:
        repository_files: list[RepositoryFile] = []

        for root, directories, filenames in os.walk(self.repository_path):
            directories[:] = [
                directory
                for directory in directories
                if directory not in IGNORED_DIRECTORIES
            ]

            root_path = Path(root)

            for filename in filenames:
                file_path = root_path / filename

                try:
                    size_bytes = file_path.stat().st_size
                except OSError:
                    continue

                relative_path = file_path.relative_to(self.repository_path)

                repository_files.append(
                    RepositoryFile(
                        path=str(relative_path),
                        extension=file_path.suffix.lower(),
                        size_bytes=size_bytes,
                        category=self._categorize_file(file_path),
                    )
                )

        return sorted(repository_files, key=lambda file: file.path)

    def _categorize_file(self, file_path: Path) -> str:
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()
        path_parts = {part.lower() for part in file_path.parts}

        if self._is_test_file(filename, path_parts):
            return "test"

        if extension in SOURCE_EXTENSIONS:
            return "source"

        if extension in CONFIG_EXTENSIONS or file_path.name in IMPORTANT_FILES:
            return "config"

        if extension in {".md", ".rst", ".txt"}:
            return "documentation"

        return "other"

    @staticmethod
    def _is_test_file(filename: str, path_parts: set[str]) -> bool:
        if "tests" in path_parts or "test" in path_parts:
            return True

        return any(pattern in filename for pattern in TEST_PATTERNS)

    def _build_tree(
        self,
        directory: Path,
        lines: list[str],
        prefix: str,
        depth: int,
        max_depth: int,
    ) -> None:
        if depth >= max_depth:
            return

        try:
            entries = sorted(
                [
                    entry
                    for entry in directory.iterdir()
                    if entry.name not in IGNORED_DIRECTORIES
                ],
                key=lambda entry: (entry.is_file(), entry.name.lower()),
            )
        except PermissionError:
            return

        for index, entry in enumerate(entries):
            is_last = index == len(entries) - 1
            connector = "└── " if is_last else "├── "

            lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "

                self._build_tree(
                    directory=entry,
                    lines=lines,
                    prefix=prefix + extension,
                    depth=depth + 1,
                    max_depth=max_depth,
                )


if __name__ == "__main__":
    agent = RepositoryAgent(".")
    summary = agent.analyze()

    print(agent.get_tree())
    print()
    print(f"Repository: {summary.repository_name}")
    print(f"Total files: {summary.total_files}")
    print(f"Source files: {summary.source_files}")
    print(f"Test files: {summary.test_files}")
    print(f"Configuration files: {summary.config_files}")
    print(f"Documentation files: {summary.documentation_files}")
    print(f"Languages: {summary.languages}")