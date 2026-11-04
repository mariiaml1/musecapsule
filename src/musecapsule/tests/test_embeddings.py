import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from musecapsule.embeddings import (
    _create_token_counter as original_token_counter,
)
from musecapsule.embeddings import create_local_embedder


@pytest.fixture(autouse=True)
def fake_token_counter(monkeypatch):
    monkeypatch.setattr(
        "musecapsule.embeddings._create_token_counter",
        lambda model: (lambda text: 3, 256),
    )


@pytest.mark.parametrize(
    ("word_count", "accepted"),
    [(254, True), (255, False)],
)
def test_local_embedder_checks_token_limit_before_inference(
    monkeypatch, word_count, accepted
):
    inference = Mock(return_value=[[1.0] * 384, [1.0] * 384])

    monkeypatch.setitem(
        sys.modules,
        "fastembed",
        SimpleNamespace(
            TextEmbedding=lambda **kwargs: SimpleNamespace(
                embed=inference,
            ),
        ),
    )
    monkeypatch.setattr(
        "musecapsule.embeddings._create_token_counter",
        lambda model: (
            lambda text: len(text.split()) + 2,
            256,
        ),
    )

    embed = create_local_embedder()
    texts = ["Short input.", "token " * word_count]

    if accepted:
        assert len(embed(texts)) == 2
        inference.assert_called_once_with(texts)
    else:
        with pytest.raises(ValueError, match="256-token limit"):
            embed(texts)

        inference.assert_not_called()


def test_local_embedder_reuses_model_and_preserves_batch_order(monkeypatch):
    initializations = []
    calls = []

    class FakeModel:
        def __init__(self, *, model_name):
            initializations.append(model_name)

        def embed(self, texts):
            calls.append(list(texts))
            return [[float(index + 1)] * 384 for index in range(len(texts))]

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


def test_token_counter_counts_without_truncation_or_padding():
    tokenizers = pytest.importorskip("tokenizers")

    tokenizer = tokenizers.Tokenizer(
        tokenizers.models.WordLevel(
            {
                "[UNK]": 0,
                "[CLS]": 1,
                "[SEP]": 2,
                "hello": 3,
            },
            unk_token="[UNK]",
        )
    )
    tokenizer.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()
    tokenizer.post_processor = tokenizers.processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        special_tokens=[("[CLS]", 1), ("[SEP]", 2)],
    )
    tokenizer.enable_truncation(max_length=4)
    tokenizer.enable_padding(length=6)
    original_settings = tokenizer.to_str()

    model = SimpleNamespace(
        model=SimpleNamespace(tokenizer=tokenizer),
    )

    count_tokens, limit = original_token_counter(model)

    assert limit == 4
    assert count_tokens("hello") == 3
    assert count_tokens("hello hello hello hello hello") == 7
    assert tokenizer.to_str() == original_settings
