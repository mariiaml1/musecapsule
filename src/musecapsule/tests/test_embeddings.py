import sys
from types import SimpleNamespace

import pytest

from musecapsule.embeddings import create_local_embedder


def test_local_embedder_reuses_model_and_preserves_batch_order(monkeypatch):
    initializations = []
    calls = []

    class FakeModel:
        def __init__(self, *, model_name):
            initializations.append(model_name)

        def embed(self, texts):
            calls.append(list(texts))
            return [
                [float(index + 1)] * 384
                for index in range(len(texts))
            ]

    monkeypatch.setitem(
        sys.modules,
        "fastembed",
        SimpleNamespace(TextEmbedding=FakeModel),
    )

    embed = create_local_embedder()

    vectors = embed(["Retries need limits.", "SQLite stores snapshots."])
    embed(["Another request."])

    assert len(initializations) == 1
    assert len(calls) == 2
    assert vectors == [[1.0] * 384, [2.0] * 384]

    assert embed([]) == []
    assert len(calls) == 2

    with pytest.raises(ValueError, match="must not be blank"):
        embed(["Valid text", " "])

    assert len(calls) == 2


@pytest.mark.parametrize(
    "output",
    [
        [],
        [[1.0] * 383],
        [[float("nan")] * 384],
        [[float("inf")] * 384],
    ],
)
def test_local_embedder_rejects_invalid_output(monkeypatch, output):
    monkeypatch.setitem(
        sys.modules,
        "fastembed",
        SimpleNamespace(
            TextEmbedding=lambda **kwargs: SimpleNamespace(
                embed=lambda texts: output,
            ),
        ),
    )

    embed = create_local_embedder()

    with pytest.raises(RuntimeError):
        embed(["Retries need limits."])
