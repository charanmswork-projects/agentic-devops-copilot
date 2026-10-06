from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class EmbeddingResult:
    text: str
    vector: list[float]


class EmbeddingModel:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        self._validate_text(text)

        vector = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return vector.astype(float).tolist()

    def embed_documents(
        self,
        documents: Iterable[str],
    ) -> list[EmbeddingResult]:
        texts = [
            text.strip()
            for text in documents
            if isinstance(text, str) and text.strip()
        ]

        if not texts:
            return []

        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return [
            EmbeddingResult(
                text=text,
                vector=vector.astype(float).tolist(),
            )
            for text, vector in zip(texts, vectors)
        ]

    def similarity(
        self,
        first_text: str,
        second_text: str,
    ) -> float:
        first = np.array(
            self.embed_text(first_text),
            dtype=np.float32,
        )

        second = np.array(
            self.embed_text(second_text),
            dtype=np.float32,
        )

        score = np.dot(first, second)

        return round(float(score), 4)

    def get_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    @staticmethod
    def _validate_text(text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("Text must be a string")

        if not text.strip():
            raise ValueError("Text cannot be empty")


if __name__ == "__main__":
    embedding_model = EmbeddingModel()

    sample_text = (
        "The CI pipeline failed because the authentication test "
        "returned an invalid token error."
    )

    vector = embedding_model.embed_text(sample_text)

    print("Model:", embedding_model.model_name)
    print("Embedding dimension:", embedding_model.get_dimension())
    print("Vector length:", len(vector))
    print("First values:", vector[:5])

    similarity = embedding_model.similarity(
        "The login test failed due to an invalid token.",
        "Authentication validation returned a token error.",
    )

    print("Similarity:", similarity)