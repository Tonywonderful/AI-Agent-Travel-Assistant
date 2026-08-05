"""对话侧本地攻略工具单元测试（mock 检索与 rewrite）。"""

import pytest

from app.tools.knowledge_tools import (
    resolve_destination,
    rewrite_chat_query,
    tool_search_travel_guide,
)
from app.tools.registry import execute_tool, list_tool_names


def test_resolve_destination_prefers_explicit() -> None:
    assert resolve_destination("看日落", "大理") == "大理"
    assert resolve_destination("随便问问", "大理市") == "大理"


def test_resolve_destination_from_question() -> None:
    assert resolve_destination("厦门鼓浪屿怎么玩", None) == "厦门"
    assert resolve_destination("看日落哪里出片", None) is None


def test_rewrite_requires_llm(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.knowledge_tools._build_chat_llm", lambda: None)

    with pytest.raises(RuntimeError, match="required but unavailable"):
        rewrite_chat_query("双廊看日落要注意什么", "大理")


def test_rewrite_does_not_fallback_when_llm_fails(monkeypatch) -> None:
    class FailingLlm:
        def invoke(self, messages):
            raise ConnectionError("model offline")

    monkeypatch.setattr(
        "app.tools.knowledge_tools._build_chat_llm",
        lambda: FailingLlm(),
    )

    with pytest.raises(RuntimeError, match="LLM Query Rewrite failed"):
        rewrite_chat_query("双廊看日落要注意什么", "大理")


def test_rewrite_rejects_empty_llm_output(monkeypatch) -> None:
    class EmptyResponse:
        content = ""

    class EmptyLlm:
        def invoke(self, messages):
            return EmptyResponse()

    monkeypatch.setattr(
        "app.tools.knowledge_tools._build_chat_llm",
        lambda: EmptyLlm(),
    )

    with pytest.raises(RuntimeError, match="empty query"):
        rewrite_chat_query("双廊看日落要注意什么", "大理")


def test_search_travel_guide_requires_question() -> None:
    result = tool_search_travel_guide(question="")
    assert result.ok is False
    assert "question" in (result.error or "")


def test_search_travel_guide_requires_destination() -> None:
    result = tool_search_travel_guide(question="看日落哪里比较出片")
    assert result.ok is False
    assert result.data and result.data.get("need_destination") is True


def test_search_travel_guide_stops_when_rewrite_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.knowledge_tools.rewrite_chat_query",
        lambda question, destination: (_ for _ in ()).throw(
            RuntimeError("LLM Query Rewrite failed")
        ),
    )

    def fail_if_retrieved(**kwargs):
        raise AssertionError("rewrite 失败后不得执行检索")

    monkeypatch.setattr(
        "app.tools.knowledge_tools.retrieve_travel_guide",
        fail_if_retrieved,
    )

    result = tool_search_travel_guide(question="看日落要注意什么", destination="大理")

    assert result.ok is False
    assert result.error == "LLM Query Rewrite failed"


def test_search_travel_guide_success(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "app.tools.knowledge_tools.rewrite_chat_query",
        lambda question, destination: (f"{destination} 日落 洱海", "llm"),
    )

    def fake_retrieve(query, top_k, destination=None, retrieval_scope=None):
        captured["retrieval_scope"] = retrieval_scope
        return (
            [
                "[来源: dali_guide.md | 标题: 洱海日落]\n傍晚适合在洱海边看日落，注意保暖。",
                "[来源: dali_guide.md | 标题: 拍照建议]\n逆光剪影容易出片。",
            ],
            {"prompt_tokens": 0, "completion_tokens": 0},
            {"prompt_tokens": 0, "completion_tokens": 0},
        )

    monkeypatch.setattr(
        "app.tools.knowledge_tools.retrieve_travel_guide",
        fake_retrieve,
    )

    result = tool_search_travel_guide(question="看日落要注意什么", destination="大理")
    assert result.ok is True
    assert result.source == "local_rag"
    assert result.data["top_k"] == 3
    assert result.data["destination"] == "大理"
    assert result.data["query"] == "大理 日落 洱海"
    assert len(result.data["snippets"]) == 2
    assert result.data["snippets"][0]["title"] == "洱海日落"
    assert captured["retrieval_scope"] is None
    assert "本地攻略" in result.summary


def test_search_travel_guide_empty_hits(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.knowledge_tools.rewrite_chat_query",
        lambda question, destination: (f"{destination} 测试", "llm"),
    )
    monkeypatch.setattr(
        "app.tools.knowledge_tools.retrieve_travel_guide",
        lambda query, top_k, destination=None: (
            [],
            {"prompt_tokens": 0, "completion_tokens": 0},
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )
    result = tool_search_travel_guide(question="有没有地下城", destination="大理")
    assert result.ok is True
    assert result.data["snippets"] == []
    assert "暂无" in result.summary


def test_execute_tool_search_travel_guide(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.knowledge_tools.rewrite_chat_query",
        lambda question, destination: (f"{destination} 美食", "llm"),
    )
    monkeypatch.setattr(
        "app.tools.knowledge_tools.retrieve_travel_guide",
        lambda query, top_k, destination=None: (
            ["[来源: dali_guide.md | 标题: 餐饮]\n推荐本地菜。"],
            {"prompt_tokens": 0, "completion_tokens": 0},
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )
    result = execute_tool(
        "search_travel_guide",
        {"question": "吃什么", "destination": "大理"},
    )
    assert result.ok is True
    assert "search_travel_guide" in list_tool_names()
