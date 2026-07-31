"""Chat LLM 工厂：统一 OpenAI-compatible 与 OpenCode Zen 配置边界。"""

from __future__ import annotations

from typing import Any


ZEN_PROVIDER = "opencode_zen"
ZEN_FREE_MODELS = (
    "big-pickle",
    "deepseek-v4-flash-free",
    "mimo-v2.5-free",
    "north-mini-code-free",
    "nemotron-3-ultra-free",
)


def resolve_chat_model_config(
    *,
    provider: str,
    model: str,
    api_key: str,
    base_url: str,
    opencode_api_key: str,
    opencode_base_url: str,
) -> tuple[str, str, str | None]:
    """根据 Provider 解析实际发送给 ChatOpenAI 的模型、密钥与网关。"""
    normalized_provider = provider.strip().lower()
    if normalized_provider != ZEN_PROVIDER:
        return model, api_key, base_url or None

    if model not in ZEN_FREE_MODELS:
        supported = ", ".join(ZEN_FREE_MODELS)
        raise ValueError(f"OpenCode Zen 免费模型不受支持：{model}。可选值：{supported}")

    return model, opencode_api_key or "public", opencode_base_url.rstrip("/")


def build_chat_llm(
    *,
    provider: str,
    model: str,
    api_key: str,
    base_url: str,
    opencode_api_key: str,
    opencode_base_url: str,
    temperature: float,
    timeout: int,
    max_retries: int,
    streaming: bool | None = None,
) -> Any | None:
    """创建统一的 ChatOpenAI 客户端；依赖或凭据缺失时返回 None。"""
    resolved_model, resolved_api_key, resolved_base_url = resolve_chat_model_config(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        opencode_api_key=opencode_api_key,
        opencode_base_url=opencode_base_url,
    )
    if not resolved_api_key:
        return None

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None

    options: dict[str, Any] = {
        "model": resolved_model,
        "temperature": temperature,
        "api_key": resolved_api_key,
        "base_url": resolved_base_url,
        "timeout": timeout,
        "max_retries": max_retries,
    }
    if streaming is not None:
        options["streaming"] = streaming
    return ChatOpenAI(**options)


def list_zen_free_models() -> list[dict[str, str | bool]]:
    """返回可供 API 与前端发现的 Zen 限时免费模型目录。"""
    return [
        {
            "id": model,
            "provider": ZEN_PROVIDER,
            "free": True,
            "availability": "limited_time",
        }
        for model in ZEN_FREE_MODELS
    ]
