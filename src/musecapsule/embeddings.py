from collections.abc import Callable
from math import isfinite
from typing import Any

from fastembed import TextEmbedding

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingInputTooLongError(ValueError):
    """An input exceeds the embedding model's token budget."""


def _create_token_counter(
    model: Any,
) -> tuple[Callable[[str], int], int]:
    """Clone the FastEmbed tokenizer to count complete input sequences.

    Access to the backend tokenizer is specific to FastEmbed 0.9.1.
    Preserve the tokenizer used for inference.
    """

    from tokenizers import Tokenizer

    source = model.model.tokenizer

    if source is None:
        raise RuntimeError("Embedding tokenizer is unavailable.")

    max_tokens = 256

    if source.truncation is not None:
        max_tokens = min(
            max_tokens,
            source.truncation["max_length"],
        )

    if max_tokens <= 0:
        raise RuntimeError("Embedding token limit must be positive.")

    tokenizer = Tokenizer.from_str(source.to_str())
    tokenizer.no_truncation()
    tokenizer.no_padding()

    def count_tokens(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=True).ids)

    return count_tokens, max_tokens


def create_local_embedder() -> Callable[[list[str]], list[list[float]]]:
    """Load MiniLM once and return a reusable local embedding function.

    Import the optional dependency only when this adapter is created.
    """
    from fastembed import TextEmbedding

    model = TextEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )

    count_tokens, max_tokens = _create_token_counter(model)

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

        for index, text in enumerate(texts):
            token_count = count_tokens(text)

            if token_count > max_tokens:
                raise EmbeddingInputTooLongError(
                    f"Embedding input {index} exceeds " f"the {max_tokens}-token limit."
                )

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
