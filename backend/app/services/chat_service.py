"""对话编排服务：校验请求、裁剪历史、驱动 agent 事件流。

路由层只做 HTTP/SSE 适配；本模块不依赖 FastAPI。
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.agents.chat_agent import iter_assistant_events
from app.models.chat_schemas import ChatMessage, ChatStreamRequest


logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20
MAX_MESSAGE_CHARS = 4000


def _sanitize_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    """清洗并截断对话历史。"""
    cleaned: list[ChatMessage] = []
    for item in messages:
        content = (item.content or "").strip()
        if not content:
            continue
        if len(content) > MAX_MESSAGE_CHARS:
            content = content[:MAX_MESSAGE_CHARS]
        if item.role not in ("user", "assistant", "system"):
            continue
        if item.role == "system":
            continue
        cleaned.append(ChatMessage(role=item.role, content=content))

    if not cleaned:
        raise ValueError("消息不能为空。")

    if cleaned[-1].role != "user":
        raise ValueError("最后一条消息必须是用户输入。")

    if len(cleaned) > MAX_HISTORY_MESSAGES:
        cleaned = cleaned[-MAX_HISTORY_MESSAGES:]

    return cleaned


def iter_chat_events(request: ChatStreamRequest) -> Iterator[dict[str, Any]]:
    """校验后流式产出 agent 事件字典。"""
    messages = _sanitize_messages(request.messages)
    logger.info(
        "chat stream start: page=%s history=%s has_itinerary=%s",
        request.context.page,
        len(messages),
        request.context.itinerary is not None,
    )
    yield from iter_assistant_events(messages, request.context)


def iter_chat_token_stream(request: ChatStreamRequest) -> Iterator[str]:
    """兼容旧接口：只产出文本。"""
    for event in iter_chat_events(request):
        if event.get("type") == "token" and event.get("text"):
            yield str(event["text"])
