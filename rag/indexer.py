from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rag.embeddings import EmbeddingModel


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

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".md",
    ".rst",
    ".txt",
}

SPECIAL_FILES = {
    "Dockerfile",
    "Makefile",
    "requirements.txt",
    "docker-compose.yml",
    "docker-compose.yaml",
}


@dataclass
class DocumentChunk:
    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    embedding: list[float]


@dataclass
class RepositoryIndex:
    repository_path: str
    total_files: int
    total_chunks: int
    embedding_model: str
    embedding_dimension: int
    chunks: list[DocumentChunk]


class RepositoryIndexer:
    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        chunk_size: int = 80,
        chunk_overlap: int = 15,
        max_file_size: int = 500_000,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )

        self.embedding_model = (
            embedding_model or EmbeddingModel()
        )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_file_size = max_file_size

    def build_index(
        self,
        repository_path: str | Path,
    ) -> RepositoryIndex:
        repo_path = self._validate_repository(repository_path)

        files = self._find_supported_files(repo_path)

        raw_chunks: list[dict[str, Any]] = []

        for file_path in files:
            content = self._read_file(file_path)

            if content is None:
                continue

            relative_path = str(
                file_path.relative_to(repo_path)
            )

            raw_chunks.extend(
                self._chunk_file(
                    file_path=relative_path,
                    content=content,
                )
            )

        embeddings = self.embedding_model.embed_documents(
            chunk["content"]
            for chunk in raw_chunks
        )

        chunks: list[DocumentChunk] = []

        for raw_chunk, embedding_result in zip(
            raw_chunks,
            embeddings,
        ):
            chunks.append(
                DocumentChunk(
                    chunk_id=raw_chunk["chunk_id"],
                    file_path=raw_chunk["file_path"],
                    content=raw_chunk["content"],
                    start_line=raw_chunk["start_line"],
                    end_line=raw_chunk["end_line"],
                    embedding=embedding_result.vector,
                )
            )

        return RepositoryIndex(
            repository_path=str(repo_path),
            total_files=len(files),
            total_chunks=len(chunks),
            embedding_model=self.embedding_model.model_name,
            embedding_dimension=self.embedding_model.get_dimension(),
            chunks=chunks,
        )

    def save_index(
        self,
        index: RepositoryIndex,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                asdict(index),
                file,
                ensure_ascii=False,
            )

        return path.resolve()

    def load_index(
        self,
        index_path: str | Path,
    ) -> RepositoryIndex:
        path = Path(index_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Index file not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        chunks = [
            DocumentChunk(**chunk)
            for chunk in data["chunks"]
        ]

        return RepositoryIndex(
            repository_path=data["repository_path"],
            total_files=data["total_files"],
            total_chunks=data["total_chunks"],
            embedding_model=data["embedding_model"],
            embedding_dimension=data["embedding_dimension"],
            chunks=chunks,
        )

    def _find_supported_files(
        self,
        repository_path: Path,
    ) -> list[Path]:
        files: list[Path] = []

        for path in repository_path.rglob("*"):
            if not path.is_file():
                continue

            if any(
                part in IGNORED_DIRECTORIES
                for part in path.parts
            ):
                continue

            if path.stat().st_size > self.max_file_size:
                continue

            if not self._is_supported_file(path):
                continue

            files.append(path)

        return sorted(files)

    def _chunk_file(
        self,
        file_path: str,
        content: str,
    ) -> list[dict[str, Any]]:
        lines = content.splitlines()

        if not lines:
            return []

        chunks = []
        start = 0
        chunk_number = 0

        while start < len(lines):
            end = min(
                start + self.chunk_size,
                len(lines),
            )

            chunk_lines = lines[start:end]

            chunk_content = "\n".join(
                chunk_lines
            ).strip()

            if chunk_content:
                chunks.append(
                    {
                        "chunk_id": (
                            f"{file_path}:"
                            f"{chunk_number}"
                        ),
                        "file_path": file_path,
                        "content": chunk_content,
                        "start_line": start + 1,
                        "end_line": end,
                    }
                )

                chunk_number += 1

            if end == len(lines):
                break

            start = end - self.chunk_overlap

        return chunks

    @staticmethod
    def _read_file(
        file_path: Path,
    ) -> str | None:
        try:
            return file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            return None

    @staticmethod
    def _is_supported_file(
        file_path: Path,
    ) -> bool:
        if file_path.name in SPECIAL_FILES:
            return True

        return (
            file_path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )

    @staticmethod
    def _validate_repository(
        repository_path: str | Path,
    ) -> Path:
        path = Path(repository_path).resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"Repository not found: {path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {path}"
            )

        return path


if __name__ == "__main__":
    indexer = RepositoryIndexer()

    repository_index = indexer.build_index(".")

    output = indexer.save_index(
        repository_index,
        "data/repository_index.json",
    )

    print("Repository:", repository_index.repository_path)
    print("Files indexed:", repository_index.total_files)
    print("Chunks:", repository_index.total_chunks)
    print(
        "Embedding dimension:",
        repository_index.embedding_dimension,
    )
    print("Index saved to:", output)