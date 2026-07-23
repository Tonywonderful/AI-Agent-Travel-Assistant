from pathlib import Path
import sys
from types import SimpleNamespace


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag import knowledge_poller  # noqa: E402


def test_apply_knowledge_changes_routes_add_modify_remove(monkeypatch) -> None:
    """added→入库，modified→先删后增，removed→清理 chunk；成功后清 RAG 缓存。"""
    calls: list[tuple[str, str]] = []
    invalidate_calls: list[int] = []

    monkeypatch.setattr(
        knowledge_poller,
        "ingest_single_document_to_chroma",
        lambda document_id: calls.append(("add", document_id)) or 3,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "replace_document_in_chroma",
        lambda document_id: calls.append(("replace", document_id)) or 4,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "remove_document_from_chroma",
        lambda document_id: calls.append(("remove", document_id)) or 2,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "invalidate_rag_caches",
        lambda: invalidate_calls.append(1)
        or {"rag": 2, "rerank": 1, "total": 3},
    )

    changes = {
        "added": [{"document_id": "dali_guide.md"}],
        "modified": [{"document_id": "beijing_guide.md"}],
        "removed": [{"document_id": "xian_guide.md"}],
        "unchanged": [{"document_id": "chengdu_guide.md"}],
    }

    results = knowledge_poller.apply_knowledge_changes(changes)

    assert calls == [
        ("add", "dali_guide.md"),
        ("replace", "beijing_guide.md"),
        ("remove", "xian_guide.md"),
    ]
    assert invalidate_calls == [1]
    assert results["summary"] == {
        "added": 1,
        "modified": 1,
        "removed": 1,
        "unchanged": 1,
        "errors": 0,
        "cache_invalidated": 3,
    }
    assert results["cache_invalidation"]["total"] == 3
    assert results["added"][0]["written_chunks"] == 3
    assert results["modified"][0]["written_chunks"] == 4
    assert results["removed"][0]["deleted_chunks"] == 2


def test_apply_can_skip_removed(monkeypatch) -> None:
    """apply_removed=False 时不清理删除文档。"""
    calls: list[str] = []
    invalidate_calls: list[int] = []
    monkeypatch.setattr(
        knowledge_poller,
        "ingest_single_document_to_chroma",
        lambda document_id: 1,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "replace_document_in_chroma",
        lambda document_id: 1,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "remove_document_from_chroma",
        lambda document_id: calls.append(document_id) or 1,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "invalidate_rag_caches",
        lambda: invalidate_calls.append(1) or {"rag": 0, "rerank": 0, "total": 0},
    )

    results = knowledge_poller.apply_knowledge_changes(
        {
            "added": [],
            "modified": [],
            "removed": [{"document_id": "gone.md"}],
            "unchanged": [],
        },
        apply_removed=False,
    )

    assert calls == []
    assert results["summary"]["removed"] == 0
    # 没有成功应用任何变更时，不应清缓存
    assert invalidate_calls == []


def test_apply_records_errors_without_raising(monkeypatch) -> None:
    """单篇失败不中断其他文档；有成功变更仍清缓存。"""

    def boom(document_id: str) -> int:
        raise RuntimeError("embed failed")

    invalidate_calls: list[int] = []
    monkeypatch.setattr(knowledge_poller, "ingest_single_document_to_chroma", boom)
    monkeypatch.setattr(
        knowledge_poller,
        "replace_document_in_chroma",
        lambda document_id: 2,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "remove_document_from_chroma",
        lambda document_id: 1,
    )
    monkeypatch.setattr(
        knowledge_poller,
        "invalidate_rag_caches",
        lambda: invalidate_calls.append(1) or {"rag": 1, "rerank": 0, "total": 1},
    )

    results = knowledge_poller.apply_knowledge_changes(
        {
            "added": [{"document_id": "bad.md"}],
            "modified": [{"document_id": "ok.md"}],
            "removed": [],
            "unchanged": [],
        }
    )

    assert results["summary"]["added"] == 0
    assert results["summary"]["modified"] == 1
    assert results["summary"]["errors"] == 1
    assert results["errors"][0]["document_id"] == "bad.md"
    assert invalidate_calls == [1]


def test_invalidate_rag_caches_deletes_rag_and_rerank_prefixes(monkeypatch) -> None:
    """invalidate_rag_caches 应清理 rag:guide: 与 rerank: 前缀。"""
    from app.services import cache_service

    deleted_prefixes: list[str] = []

    def fake_delete_by_prefix(prefix: str) -> int:
        deleted_prefixes.append(prefix)
        return 2 if prefix.startswith("rag") else 1

    monkeypatch.setattr(cache_service, "delete_by_prefix", fake_delete_by_prefix)
    result = cache_service.invalidate_rag_caches()

    assert deleted_prefixes == ["rag:guide:", "rerank:"]
    assert result == {"rag": 2, "rerank": 1, "total": 3}


def test_delete_chunks_by_document_id_dedupes_ids(monkeypatch) -> None:
    """document_id 与 source 命中同一批 id 时只删一次。"""
    from app.rag import vector_db

    deleted_ids: list[list[str]] = []

    class FakeCollection:
        def get(self, where=None, include=None):
            return {"ids": ["a", "b"]}

        def delete(self, ids=None):
            deleted_ids.append(list(ids or []))

    monkeypatch.setattr(vector_db, "_get_chroma_collection", lambda: FakeCollection())
    count = vector_db.delete_chunks_by_document_id("beijing_guide.md")
    assert count == 2
    assert len(deleted_ids) == 1
    assert set(deleted_ids[0]) == {"a", "b"}
