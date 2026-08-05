from pathlib import Path
import sys


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag import vector_db  # noqa: E402
from app.rag.vector_db import (  # noqa: E402
    RETRIEVAL_SCOPE_ASSISTANT_ONLY,
    RETRIEVAL_SCOPE_PLANNING,
)


def test_loaded_guide_chunks_have_known_destinations() -> None:
    """每个当前攻略 Chunk 都必须带可识别的 destination。"""
    chunks = vector_db.load_guide_chunks()

    assert chunks
    assert {chunk["destination"] for chunk in chunks} == {
        "北京", "成都", "大理", "三亚", "厦门", "西安"
    }
    assert all(chunk["destination"] for chunk in chunks)
    assert all(chunk.get("document_id") for chunk in chunks)
    assert all(chunk.get("content_hash") for chunk in chunks)
    assert all(
        chunk.get("retrieval_scope")
        in {RETRIEVAL_SCOPE_PLANNING, RETRIEVAL_SCOPE_ASSISTANT_ONLY}
        for chunk in chunks
    )


def test_auxiliary_chunks_are_tagged_assistant_only() -> None:
    markdown = """
# 示例攻略

开头说明。

## 1. 目的地简介

城市概览。

## 2. 核心景点推荐

### 示例景点

景点正文。

## 5. 预约、交通、价格与安全提示

### 交通距离与行程组织

通用组织说明。
"""

    chunks = vector_db._split_markdown_into_chunks(markdown, "sample.md")
    scopes_by_title = {
        chunk["title"]: chunk["retrieval_scope"] for chunk in chunks
    }

    assert scopes_by_title["文档开头"] == RETRIEVAL_SCOPE_ASSISTANT_ONLY
    assert scopes_by_title["1. 目的地简介"] == RETRIEVAL_SCOPE_ASSISTANT_ONLY
    assert scopes_by_title["示例景点"] == RETRIEVAL_SCOPE_PLANNING
    assert (
        scopes_by_title["交通距离与行程组织"]
        == RETRIEVAL_SCOPE_ASSISTANT_ONLY
    )


def test_keyword_fallback_filters_chunks_by_destination(monkeypatch) -> None:
    """Chroma 不可用时，关键词 fallback 仍不能召回其他目的地的 Chunk。"""
    chunks = [
        {"title": "故宫", "text": "历史建筑", "source": "beijing_guide.md", "destination": "北京"},
        {"title": "大理古城", "text": "历史建筑", "source": "dali_guide.md", "destination": "大理"},
    ]
    monkeypatch.setattr(vector_db, "load_guide_chunks", lambda: chunks)

    results = vector_db._search_guide_chunks_by_keywords(
        query="历史 建筑", top_k=3, destination="北京"
    )

    assert results == [chunks[0]]


def test_keyword_fallback_hard_filters_category_and_hotel_tier(monkeypatch) -> None:
    chunks = [
        {
            "title": "舒适酒店",
            "text": "地铁附近",
            "source": "chengdu_guide.md",
            "destination": "成都",
            "retrieval_scope": RETRIEVAL_SCOPE_PLANNING,
            "category": "hotel",
            "budget_tier": "舒适型（200-500 元/晚）",
        },
        {
            "title": "豪华酒店",
            "text": "地铁附近",
            "source": "chengdu_guide.md",
            "destination": "成都",
            "retrieval_scope": RETRIEVAL_SCOPE_PLANNING,
            "category": "hotel",
            "budget_tier": "豪华型（500 元/晚以上）",
        },
        {
            "title": "住宿建议",
            "text": "地铁附近",
            "source": "chengdu_guide.md",
            "destination": "成都",
            "retrieval_scope": RETRIEVAL_SCOPE_PLANNING,
            "category": "accommodation_advice",
            "budget_tier": "",
        },
    ]
    monkeypatch.setattr(vector_db, "load_guide_chunks", lambda: chunks)

    results = vector_db._search_guide_chunks_by_keywords(
        query="地铁",
        top_k=3,
        destination="成都",
        retrieval_scope=RETRIEVAL_SCOPE_PLANNING,
        categories=["hotel"],
        budget_tier="舒适型（200-500 元/晚）",
    )

    assert results == [chunks[0]]


def test_chroma_search_filters_by_destination_metadata(monkeypatch) -> None:
    """助手检索不传 scope 时，Chroma 只按 destination 过滤。"""
    captured: dict[str, object] = {}

    class FakeCollection:
        def count(self) -> int:
            return 1

        def query(self, **kwargs):
            captured.update(kwargs)
            return {
                "documents": [["# 故宫\n明清皇家宫殿建筑群。"]],
                "metadatas": [[
                    {
                        "source": "beijing_guide.md",
                        "document_id": "beijing_guide.md",
                        "content_hash": "a" * 64,
                        "title": "故宫",
                        "destination": "北京",
                    }
                ]],
            }

    monkeypatch.setattr(vector_db, "_get_chroma_collection", lambda: FakeCollection())
    monkeypatch.setattr(
        vector_db,
        "_embed_query_with_usage",
        lambda _: ([0.1, 0.2], {"prompt_tokens": 0, "completion_tokens": 0}),
    )

    results, _ = vector_db._search_guide_chunks_by_chroma(
        query="北京历史建筑",
        top_k=3,
        destination="北京",
    )

    assert captured["where"] == {"destination": "北京"}
    assert results[0]["destination"] == "北京"
    assert results[0]["document_id"] == "beijing_guide.md"
    assert results[0]["content_hash"] == "a" * 64


def test_chroma_planning_search_combines_destination_and_scope(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeCollection:
        def count(self) -> int:
            return 1

        def query(self, **kwargs):
            captured.update(kwargs)
            return {
                "documents": [["示例景点\n适合行程规划。"]],
                "metadatas": [[
                    {
                        "source": "xiamen_guide.md",
                        "document_id": "xiamen_guide.md",
                        "content_hash": "b" * 64,
                        "title": "示例景点",
                        "destination": "厦门",
                        "retrieval_scope": RETRIEVAL_SCOPE_PLANNING,
                    }
                ]],
            }

    monkeypatch.setattr(vector_db, "_get_chroma_collection", lambda: FakeCollection())
    monkeypatch.setattr(
        vector_db,
        "_embed_query_with_usage",
        lambda _: ([0.1, 0.2], {"prompt_tokens": 0, "completion_tokens": 0}),
    )

    results, _ = vector_db._search_guide_chunks_by_chroma(
        query="厦门海边骑行",
        top_k=3,
        destination="厦门",
        retrieval_scope=RETRIEVAL_SCOPE_PLANNING,
    )

    assert captured["where"] == {
        "$and": [
            {"destination": "厦门"},
            {"retrieval_scope": RETRIEVAL_SCOPE_PLANNING},
        ]
    }
    assert results[0]["retrieval_scope"] == RETRIEVAL_SCOPE_PLANNING


def test_chroma_where_combines_entity_category_and_budget_tier() -> None:
    where = vector_db._build_chroma_where(
        "成都",
        RETRIEVAL_SCOPE_PLANNING,
        categories=["hotel"],
        budget_tier="舒适型（200-500 元/晚）",
    )

    assert where == {
        "$and": [
            {"destination": "成都"},
            {"retrieval_scope": RETRIEVAL_SCOPE_PLANNING},
            {"category": "hotel"},
            {"budget_tier": "舒适型（200-500 元/晚）"},
        ]
    }
