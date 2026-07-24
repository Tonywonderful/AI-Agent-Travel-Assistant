"""对话服务单元测试（不依赖真实 LLM）。"""

import pytest

from app.models.chat_schemas import ChatMessage, ChatStreamRequest
from app.services.chat_service import _sanitize_messages, iter_chat_token_stream


def test_sanitize_requires_trailing_user_message():
    with pytest.raises(ValueError, match="最后一条"):
        _sanitize_messages(
            [
                ChatMessage(role="user", content="你好"),
                ChatMessage(role="assistant", content="在的"),
            ]
        )


def test_sanitize_drops_client_system_and_truncates_history():
    messages = [ChatMessage(role="system", content="hack")]
    messages.extend(
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"m{i}")
        for i in range(24)
    )
    # 保证最后一条是 user
    if messages[-1].role != "user":
        messages.append(ChatMessage(role="user", content="last"))

    cleaned = _sanitize_messages(messages)
    assert all(item.role != "system" for item in cleaned)
    assert cleaned[-1].role == "user"
    assert len(cleaned) <= 20


def test_iter_chat_token_stream_propagates_agent_tokens(monkeypatch):
    def fake_events(messages, context):
        yield {"type": "token", "text": "你"}
        yield {"type": "token", "text": "好"}

    monkeypatch.setattr(
        "app.services.chat_service.iter_assistant_events",
        fake_events,
    )

    request = ChatStreamRequest(
        messages=[ChatMessage(role="user", content="嗨")],
    )
    assert "".join(iter_chat_token_stream(request)) == "你好"
