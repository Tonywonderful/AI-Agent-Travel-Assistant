from pathlib import Path
import sys

import pytest


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.tools import rag_tool  # noqa: E402


class FakeResponse:
    def __init__(self, content: str):
        self.content = content
        self.response_metadata = {
            "token_usage": {"prompt_tokens": 120, "completion_tokens": 30}
        }


class FakeLlm:
    def __init__(self, response: FakeResponse | Exception):
        self.response = response
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_planning_query_rewrite_requires_llm(monkeypatch) -> None:
    monkeypatch.setattr(rag_tool, "_build_query_llm", lambda: None)

    with pytest.raises(RuntimeError, match="required but unavailable"):
        rag_tool.rewrite_planning_queries(destination="厦门")


def test_planning_query_rewrite_returns_three_llm_queries(monkeypatch) -> None:
    llm = FakeLlm(
        FakeResponse(
            """{
                "attraction": "厦门 海边 骑行 轻松",
                "hotel": "厦门 舒适型 住宿 核心区域",
                "restaurant": "厦门 海鲜 少辣 餐厅"
            }"""
        )
    )
    monkeypatch.setattr(rag_tool, "_build_query_llm", lambda: llm)

    queries, usage = rag_tool.rewrite_planning_queries(
        destination="厦门",
        preferences=["自然风景", "城市漫游"],
        pace="轻松",
        special_notes="偏好地铁出行，住在核心区域",
        dietary_preferences=["海鲜", "少辣"],
        hotel_level="舒适型",
        budget_min_per_person=3000,
        budget_max_per_person=8000,
        day_count=3,
    )

    assert queries == rag_tool.PlanningQueries(
        attraction="厦门 海边 骑行 轻松",
        hotel="厦门 舒适型 住宿 核心区域",
        restaurant="厦门 海鲜 少辣 餐厅",
    )
    assert usage == {"prompt_tokens": 120, "completion_tokens": 30}
    assert llm.messages is not None
    assert "饮食偏好：海鲜、少辣" in llm.messages[1][1]
    assert "酒店档次：舒适型" in llm.messages[1][1]
    assert "人均预算：3000-8000 元" in llm.messages[1][1]


def test_planning_query_rewrite_rejects_missing_destination(monkeypatch) -> None:
    llm = FakeLlm(
        FakeResponse(
            """{
                "attraction": "厦门 海边 骑行",
                "hotel": "厦门 舒适型 住宿",
                "restaurant": "海鲜 少辣 餐厅"
            }"""
        )
    )
    monkeypatch.setattr(rag_tool, "_build_query_llm", lambda: llm)

    with pytest.raises(RuntimeError, match="omitted destination.*restaurant"):
        rag_tool.rewrite_planning_queries(destination="厦门")


def test_planning_query_rewrite_does_not_fallback_on_llm_error(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_tool,
        "_build_query_llm",
        lambda: FakeLlm(ConnectionError("model offline")),
    )

    with pytest.raises(RuntimeError, match="LLM Query Rewrite failed"):
        rag_tool.rewrite_planning_queries(destination="厦门")


def test_build_destination_query_uses_llm_attraction_query(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_tool,
        "rewrite_planning_queries",
        lambda **kwargs: (
            rag_tool.PlanningQueries(
                attraction="厦门 海边 骑行",
                hotel="厦门 舒适型 住宿",
                restaurant="厦门 海鲜 餐厅",
            ),
            {"prompt_tokens": 9, "completion_tokens": 3},
        ),
    )

    query, usage = rag_tool.build_destination_query(destination="厦门")

    assert query == "厦门 海边 骑行"
    assert usage == {"prompt_tokens": 9, "completion_tokens": 3}


def test_planning_retrieval_uses_all_three_llm_queries(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        rag_tool,
        "rewrite_planning_queries",
        lambda **kwargs: (
            rag_tool.PlanningQueries(
                attraction="厦门 海边 骑行",
                hotel="厦门 舒适型 核心区域 住宿",
                restaurant="厦门 海鲜 少辣 餐厅",
            ),
            {"prompt_tokens": 100, "completion_tokens": 20},
        ),
    )

    def fake_retrieve_travel_guide(**kwargs):
        calls.append(kwargs)
        return [], {"prompt_tokens": 0, "completion_tokens": 0}, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

    monkeypatch.setattr(rag_tool, "retrieve_travel_guide", fake_retrieve_travel_guide)

    _, rewrite_usage, _, _ = rag_tool.get_destination_guide_context(
        destination="厦门",
        dietary_preferences=["海鲜"],
        hotel_level="舒适型",
        budget_min_per_person=3000,
        budget_max_per_person=8000,
        special_notes="偏好地铁出行，住在核心区域",
    )

    assert rewrite_usage == {"prompt_tokens": 100, "completion_tokens": 20}
    assert len(calls) == 3
    assert all(call["retrieval_scope"] == "planning" for call in calls)
    assert [call["query"] for call in calls] == [
        "厦门 海边 骑行",
        "厦门 舒适型 核心区域 住宿",
        "厦门 海鲜 少辣 餐厅",
    ]
    assert [call["top_k"] for call in calls] == [5, 3, 5]
    assert [call["categories"] for call in calls] == [
        ["attraction"],
        ["hotel"],
        ["restaurant"],
    ]
    assert calls[1]["budget_tier"] == "舒适型（200-500 元/晚）"
    assert calls[2]["budget_tier"] is None
