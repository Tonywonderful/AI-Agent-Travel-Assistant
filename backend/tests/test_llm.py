from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.llm import (  # noqa: E402
    ZEN_FREE_MODELS,
    ZEN_PROVIDER,
    build_chat_llm,
    list_zen_free_models,
    resolve_chat_model_config,
)


def test_all_zen_free_models_resolve_to_public_gateway() -> None:
    for model in ZEN_FREE_MODELS:
        resolved = resolve_chat_model_config(
            provider=ZEN_PROVIDER,
            model=model,
            api_key="existing-key",
            base_url="https://existing.example/v1",
            opencode_api_key="public",
            opencode_base_url="https://opencode.ai/zen/v1/",
        )
        assert resolved == (model, "public", "https://opencode.ai/zen/v1")


def test_existing_openai_compatible_configuration_is_unchanged() -> None:
    resolved = resolve_chat_model_config(
        provider="openai_compatible",
        model="existing-model",
        api_key="existing-key",
        base_url="https://existing.example/v1",
        opencode_api_key="public",
        opencode_base_url="https://opencode.ai/zen/v1",
    )
    assert resolved == (
        "existing-model",
        "existing-key",
        "https://existing.example/v1",
    )


def test_zen_provider_rejects_models_outside_free_allowlist() -> None:
    with pytest.raises(ValueError, match="OpenCode Zen 免费模型不受支持"):
        resolve_chat_model_config(
            provider=ZEN_PROVIDER,
            model="deepseek-v4-pro",
            api_key="",
            base_url="",
            opencode_api_key="public",
            opencode_base_url="https://opencode.ai/zen/v1",
        )


def test_build_chat_llm_uses_resolved_zen_settings(monkeypatch) -> None:
    class FakeChatOpenAI:
        last_options = None

        def __init__(self, **options) -> None:
            FakeChatOpenAI.last_options = options

    fake_module = types.ModuleType("langchain_openai")
    fake_module.ChatOpenAI = FakeChatOpenAI
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)

    result = build_chat_llm(
        provider=ZEN_PROVIDER,
        model="mimo-v2.5-free",
        api_key="existing-key",
        base_url="https://existing.example/v1",
        opencode_api_key="public",
        opencode_base_url="https://opencode.ai/zen/v1",
        temperature=0.2,
        timeout=60,
        max_retries=1,
        streaming=True,
    )

    assert isinstance(result, FakeChatOpenAI)
    assert FakeChatOpenAI.last_options == {
        "model": "mimo-v2.5-free",
        "temperature": 0.2,
        "api_key": "public",
        "base_url": "https://opencode.ai/zen/v1",
        "timeout": 60,
        "max_retries": 1,
        "streaming": True,
    }


def test_model_catalog_contains_only_five_zen_free_models() -> None:
    catalog = list_zen_free_models()
    assert [item["id"] for item in catalog] == list(ZEN_FREE_MODELS)
    assert all(item["provider"] == ZEN_PROVIDER for item in catalog)
    assert all(item["free"] is True for item in catalog)
