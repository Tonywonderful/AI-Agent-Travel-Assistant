from pathlib import Path
import sys
from types import SimpleNamespace


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag import knowledge_poller  # noqa: E402
from app.rag.document_registry import compute_content_hash  # noqa: E402


def test_scan_detects_added_modified_unchanged_removed(monkeypatch) -> None:
    """轮询应正确区分新增 / 修改 / 未变 / 缺失。"""
    disk_docs = [
        {
            "document_id": "beijing_guide.md",
            "source_path": "data/beijing_guide.md",
            "content_hash": "hash_beijing_new",
            "last_modified": 20.0,
            "destination": "北京",
        },
        {
            "document_id": "chengdu_guide.md",
            "source_path": "data/chengdu_guide.md",
            "content_hash": "hash_chengdu_same",
            "last_modified": 10.0,
            "destination": "成都",
        },
        {
            "document_id": "dali_guide.md",
            "source_path": "data/dali_guide.md",
            "content_hash": "hash_dali_new_file",
            "last_modified": 30.0,
            "destination": "大理",
        },
    ]
    registry = [
        SimpleNamespace(
            document_id="beijing_guide.md",
            source_path="data/beijing_guide.md",
            content_hash="hash_beijing_old",
            last_modified=10.0,
            destination="北京",
        ),
        SimpleNamespace(
            document_id="chengdu_guide.md",
            source_path="data/chengdu_guide.md",
            content_hash="hash_chengdu_same",
            last_modified=10.0,
            destination="成都",
        ),
        SimpleNamespace(
            document_id="xian_guide.md",
            source_path="data/xian_guide.md",
            content_hash="hash_xian_gone",
            last_modified=5.0,
            destination="西安",
        ),
    ]

    monkeypatch.setattr(knowledge_poller, "_scan_disk_documents", lambda: disk_docs)
    monkeypatch.setattr(knowledge_poller, "list_documents", lambda status=None: registry)

    changes = knowledge_poller.scan_knowledge_changes()

    assert [item["document_id"] for item in changes["added"]] == ["dali_guide.md"]
    assert [item["document_id"] for item in changes["modified"]] == ["beijing_guide.md"]
    assert [item["document_id"] for item in changes["unchanged"]] == ["chengdu_guide.md"]
    assert [item["document_id"] for item in changes["removed"]] == ["xian_guide.md"]

    summary = knowledge_poller.summarize_changes(changes)
    assert summary == {
        "added": 1,
        "modified": 1,
        "unchanged": 1,
        "removed": 1,
        "has_changes": True,
    }


def test_scan_all_unchanged_has_no_changes(monkeypatch) -> None:
    """全部 hash 一致时 has_changes 为 False。"""
    content_hash = compute_content_hash("same body")
    disk_docs = [
        {
            "document_id": "beijing_guide.md",
            "source_path": "data/beijing_guide.md",
            "content_hash": content_hash,
            "last_modified": 1.0,
            "destination": "北京",
        }
    ]
    registry = [
        SimpleNamespace(
            document_id="beijing_guide.md",
            source_path="data/beijing_guide.md",
            content_hash=content_hash,
            last_modified=1.0,
            destination="北京",
        )
    ]
    monkeypatch.setattr(knowledge_poller, "_scan_disk_documents", lambda: disk_docs)
    monkeypatch.setattr(knowledge_poller, "list_documents", lambda status=None: registry)

    changes = knowledge_poller.scan_knowledge_changes()
    assert knowledge_poller.summarize_changes(changes)["has_changes"] is False
    assert changes["unchanged"][0]["document_id"] == "beijing_guide.md"


def test_format_changes_report_contains_sections() -> None:
    report = knowledge_poller.format_changes_report(
        {
            "added": [
                {
                    "document_id": "a.md",
                    "content_hash": "a" * 64,
                }
            ],
            "modified": [],
            "unchanged": [],
            "removed": [],
        }
    )
    assert "知识库轮询结果" in report
    assert "新增 added" in report
    assert "a.md" in report
