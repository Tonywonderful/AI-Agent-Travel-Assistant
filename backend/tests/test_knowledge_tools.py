"""对话侧本地攻略工具单元测试（mock 检索与 rewrite）。"""

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


def test_rewrite_rule_fallback_when_no_llm(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.knowledge_tools._build_chat_llm", lambda: None)
    query, source = rewrite_chat_query("双廊看日落要注意什么", "大理")
    assert source == "rule"
    assert "大理" in query
    assert "日落" in query


def test_search_travel_guide_requires_question() -> None:
    result = tool_search_travel_guide(question="")
    assert result.ok is False
    assert "question" in (result.error or "")


def test_search_travel_guide_requires_destination() -> None:
    result = tool_search_travel_guide(question="看日落哪里比较出片")
    assert result.ok is False
    assert result.data and result.data.get("need_destination") is True


def test_search_travel_guide_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.knowledge_tools.rewrite_chat_query",
        lambda question, destination: (f"{destination} 日落 洱海", "rule"),
    )
    monkeypatch.setattr(
        "app.tools.knowledge_tools.retrieve_travel_guide",
        lambda query, top_k, destination=None: (
            [
                "[来源: dali_guide.md | 标题: 洱海日落]\n傍晚适合在洱海边看日落，注意保暖。",
                "[来源: dali_guide.md | 标题: 拍照建议]\n逆光剪影容易出片。",
            ],
            {"prompt_tokens": 0, "completion_tokens": 0},
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )

    result = tool_search_travel_guide(question="看日落要注意什么", destination="大理")
    assert result.ok is True
    assert result.source == "local_rag"
    assert result.data["top_k"] == 3
    assert result.data["destination"] == "大理"
    assert result.data["query"] == "大理 日落 洱海"
    assert len(result.data["snippets"]) == 2
    assert result.data["snippets"][0]["title"] == "洱海日落"
    assert "本地攻略" in result.summary


def test_search_travel_guide_empty_hits(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.tools.knowledge_tools.rewrite_chat_query",
        lambda question, destination: (f"{destination} 测试", "rule"),
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
        lambda question, destination: (f"{destination} 美食", "rule"),
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
