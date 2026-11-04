from collections.abc import Callable
from math import isfinite


def create_local_embedder() -> Callable[[list[str]], list[list[float]]]:
    """Load MiniLM once and return a reusable local embedding function.

    Import the optional dependency only when this adapter is created.
    """
    from fastembed import TextEmbedding

    model = TextEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )

    def embed(texts: list[str]) -> list[list[float]]:
        """Embed nonblank texts and validate the returned vector batch.

        Raises:
            ValueError: If an input text is blank.
            RuntimeError: If the model returns an invalid vector batch.
        """
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("Embedding text must not be blank.")

        vectors = [
            [float(value) for value in vector]
            for vector in model.embed(texts)
        ]

        if len(vectors) != len(texts):
            raise RuntimeError("Embedding count does not match input count.")

        if any(len(vector) != 384 for vector in vectors):
            raise RuntimeError("Unexpected embedding dimensions.")

        if any(
            not isfinite(value)
            for vector in vectors
            for value in vector
        ):
            raise RuntimeError("Embedding contains nonfinite values.")

        return vectors

    return embed
