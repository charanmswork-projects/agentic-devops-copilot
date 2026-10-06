from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rag.embeddings import EmbeddingModel
from rag.indexer import RepositoryIndex, RepositoryIndexer


@dataclass
class RetrievedChunk:
    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    score: float


class RepositoryRetriever:
    def __init__(
        self,
        index: RepositoryIndex,
        embedding_model: EmbeddingModel | None = None,
    ):
        self.index = index
        self.embedding_model = embedding_model or EmbeddingModel(
            index.embedding_model
        )

        self._chunk_matrix = self._build_chunk_matrix()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            raise ValueError("Query cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        if not self.index.chunks:
            return []

        query_vector = np.array(
            self.embedding_model.embed_text(query),
            dtype=np.float32,
        )

        scores = self._chunk_matrix @ query_vector

        ranked_indices = np.argsort(scores)[::-1]

        results: list[RetrievedChunk] = []

        for index in ranked_indices:
            score = float(scores[index])

            if score < min_score:
                continue

            chunk = self.index.chunks[index]

            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    file_path=chunk.file_path,
                    content=chunk.content,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    score=round(score, 4),
                )
            )

            if len(results) >= top_k:
                break

        return results

    def retrieve_for_error(
        self,
        error_message: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        query = (
            "Find source code, configuration, or tests related "
            f"to this error:\n{error_message}"
        )

        return self.retrieve(
            query=query,
            top_k=top_k,
        )

    def retrieve_for_failed_test(
        self,
        test_name: str,
        failure_output: str = "",
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        query = (
            f"Find code related to the failing test {test_name}."
        )

        if failure_output:
            query += f"\nFailure details:\n{failure_output}"

        return self.retrieve(
            query=query,
            top_k=top_k,
        )

    def retrieve_from_file(
        self,
        file_path: str,
        limit: int = 10,
    ) -> list[RetrievedChunk]:
        results = []

        for chunk in self.index.chunks:
            if chunk.file_path == file_path:
                results.append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        file_path=chunk.file_path,
                        content=chunk.content,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        score=1.0,
                    )
                )

            if len(results) >= limit:
                break

        return results

    def _build_chunk_matrix(self) -> np.ndarray:
        if not self.index.chunks:
            return np.empty(
                (
                    0,
                    self.index.embedding_dimension,
                ),
                dtype=np.float32,
            )

        matrix = np.array(
            [
                chunk.embedding
                for chunk in self.index.chunks
            ],
            dtype=np.float32,
        )

        return matrix


def load_retriever(
    index_path: str | Path,
) -> RepositoryRetriever:
    indexer = RepositoryIndexer()

    index = indexer.load_index(index_path)

    return RepositoryRetriever(index=index)


if __name__ == "__main__":
    retriever = load_retriever(
        "data/repository_index.json"
    )

    query = (
        "Where is pytest execution handled "
        "and how are test failures captured?"
    )

    results = retriever.retrieve(
        query=query,
        top_k=5,
    )

    print(f"Query: {query}")
    print()

    for position, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"{position}. {result.file_path} "
            f"(lines {result.start_line}-{result.end_line})"
        )
        print(f"Score: {result.score}")
        print(result.content[:500])
        print("-" * 60)