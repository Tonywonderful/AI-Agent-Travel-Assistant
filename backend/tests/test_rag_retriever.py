from pathlib import Path
import sys


# 允许测试文件直接导入 backend/app 下的模块。
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.rag.retriever as retriever  # noqa: E402
from app.config import RAG_TOP_K  # noqa: E402


def test_retrieve_travel_guide_formats_chunks_as_text(monkeypatch) -> None:
    """测试 retriever 会把检索结果格式化成可直接引用的文本片段。"""

    def fake_search_guide_chunks_with_usage(
        query: str, top_k: int = RAG_TOP_K
    ) -> tuple[list[dict[str, str]], dict[str, int]]:
        assert query == "大理 古城 美食"
        assert top_k == 6
        return [
            {
                "source": "dali_guide.md",
                "title": "大理古城",
                "text": "大理古城适合慢游和拍照。",
            }
        ], {"prompt_tokens": 0, "completion_tokens": 0}

    monkeypatch.setattr(retriever, "search_guide_chunks_with_usage", fake_search_guide_chunks_with_usage)
    monkeypatch.setattr(
        retriever,
        "rerank_guide_chunks",
        lambda query, matched_chunks, top_k, destination=None: (
            matched_chunks[:top_k],
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )

    results, _, _ = retriever.retrieve_travel_guide("大理 古城 美食", top_k=2)

    assert results == ["[来源: dali_guide.md | 标题: 大理古城]\n大理古城适合慢游和拍照。"]


def test_retrieve_travel_guide_returns_empty_when_no_chunks(monkeypatch) -> None:
    """测试没有召回任何片段时，会返回空列表。"""

    def fake_search_guide_chunks_with_usage(
        query: str, top_k: int = RAG_TOP_K
    ) -> tuple[list[dict[str, str]], dict[str, int]]:
        assert query == "火星 沙漠 极地科考"
        assert top_k == 6
        return [], {"prompt_tokens": 0, "completion_tokens": 0}

    monkeypatch.setattr(retriever, "search_guide_chunks_with_usage", fake_search_guide_chunks_with_usage)
    monkeypatch.setattr(
        retriever,
        "rerank_guide_chunks",
        lambda query, matched_chunks, top_k, destination=None: (
            matched_chunks[:top_k],
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )

    results, _, _ = retriever.retrieve_travel_guide("火星 沙漠 极地科考", top_k=2)

    assert results == []


def test_openrouter_rerank_sends_expected_payload_and_maps_indices(monkeypatch) -> None:
    """OpenRouter 请求应使用对象文档，并把过滤后的索引映射回原候选。"""
    captured: dict = {}

    class FakeResponse:
        is_success = True
        status_code = 200
        text = ""

        @staticmethod
        def json() -> dict:
            return {
                "results": [
                    {"index": 1, "relevance_score": 0.92},
                    {"index": 0, "relevance_score": 0.41},
                ],
                "usage": {"prompt_tokens": 17, "completion_tokens": 0},
            }

    class FakeClient:
        def __init__(self, timeout: float):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @staticmethod
        def post(url: str, json: dict, headers: dict[str, str]):
            captured.update({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr(retriever, "RERANK_API_KEY", "test-key")
    monkeypatch.setattr(retriever, "RERANK_API_URL", "https://openrouter.ai/api/v1/rerank")
    monkeypatch.setattr(
        retriever,
        "RERANK_MODEL",
        "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
    )
    monkeypatch.setattr(retriever, "RERANK_HTTP_REFERER", "http://localhost:5173")
    monkeypatch.setattr(retriever, "RERANK_APP_TITLE", "TravelPlanAssistant")
    monkeypatch.setattr(retriever, "RERANK_TIMEOUT_SECONDS", 12.5)
    monkeypatch.setattr(retriever.httpx, "Client", FakeClient)

    chunks = [
        {"title": "文档开头", "text": "噪声"},
        {"title": "大理古城", "text": "适合慢游"},
        {"title": "洱海", "text": "适合骑行看日落"},
    ]
    scored, usage = retriever._rerank_with_openrouter("大理 日落 骑行", chunks, 2)

    assert scored == [(0.92, 2), (0.41, 1)]
    assert usage == {"prompt_tokens": 17, "completion_tokens": 0}
    assert captured["url"] == "https://openrouter.ai/api/v1/rerank"
    assert captured["timeout"] == 12.5
    assert captured["json"] == {
        "model": "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
        "query": "大理 日落 骑行",
        "documents": [
            {"text": "大理古城\n适合慢游"},
            {"text": "洱海\n适合骑行看日落"},
        ],
        "top_n": 2,
    }
    assert captured["headers"] == {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-OpenRouter-Title": "TravelPlanAssistant",
    }


def test_rerank_cache_key_changes_with_model(monkeypatch) -> None:
    """切换模型后不应继续复用旧模型产生的重排缓存。"""
    chunks = [{"source": "dali.md", "title": "洱海", "text": "骑行"}]

    monkeypatch.setattr(retriever, "RERANK_MODEL", "old-rerank-model")
    old_key = retriever._build_rerank_cache_key("大理骑行", chunks)
    monkeypatch.setattr(retriever, "RERANK_MODEL", "new-rerank-model")
    new_key = retriever._build_rerank_cache_key("大理骑行", chunks)

    assert old_key != new_key
    assert old_key.startswith("rerank:")
    assert new_key.startswith("rerank:")


def test_rerank_falls_back_to_rule_scoring_when_openrouter_is_unavailable(
    monkeypatch,
) -> None:
    """OpenRouter 不可用时应继续使用本地规则重排，而不是中断检索。"""
    monkeypatch.setattr(retriever, "get_cached_json", lambda key: None)
    monkeypatch.setattr(
        retriever,
        "_rerank_with_openrouter",
        lambda query, chunks, top_k: (
            None,
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )

    chunks = [
        {"source": "dali.md", "title": "目的地简介", "text": "大理概览"},
        {"source": "dali.md", "title": "洱海骑行", "text": "洱海适合骑行"},
    ]
    ranked, usage = retriever.rerank_guide_chunks(
        "洱海 骑行",
        chunks,
        top_k=1,
        destination="大理",
    )

    assert ranked[0]["title"] == "洱海骑行"
    assert ranked[0]["rerank_reasons"]
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0}
