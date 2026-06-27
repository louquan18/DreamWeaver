import pytest

from src.models import llm_client


@pytest.mark.asyncio
async def test_llm_stream_with_fallback_tries_next_model_after_empty_stream(monkeypatch):
    calls = []

    async def fake_llm_stream(messages, model, max_tokens, temperature):
        calls.append(model)
        if model == "empty-model":
            if False:
                yield ""
            return
        yield "ok"

    monkeypatch.setattr(llm_client, "llm_stream", fake_llm_stream)

    tokens = [
        token
        async for token in llm_client.llm_stream_with_fallback(
            [],
            models=["empty-model", "working-model"],
        )
    ]

    assert calls == ["empty-model", "working-model"]
    assert tokens == ["ok"]


@pytest.mark.asyncio
async def test_llm_stream_with_fallback_raises_when_all_models_return_empty(monkeypatch):
    async def fake_llm_stream(messages, model, max_tokens, temperature):
        if False:
            yield ""

    monkeypatch.setattr(llm_client, "llm_stream", fake_llm_stream)

    with pytest.raises(RuntimeError, match="returned an empty response"):
        [
            token
            async for token in llm_client.llm_stream_with_fallback(
                [],
                models=["empty-model"],
            )
        ]
