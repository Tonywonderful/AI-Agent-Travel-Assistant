"""知识库定时轮询：扫描本地文档，对比清单，感知并应用变更。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.config import BACKEND_DIR
from app.rag.document_registry import (
    compute_content_hash,
    list_documents,
)
from app.rag.guide_catalog import destination_for_guide
from app.rag.vector_db import (
    ingest_single_document_to_chroma,
    remove_document_from_chroma,
    replace_document_in_chroma,
)
from app.services.cache_service import invalidate_rag_caches


DATA_DIR = BACKEND_DIR / "data"

ChangeType = Literal["added", "modified", "unchanged", "removed"]


def _scan_disk_documents() -> list[dict[str, object]]:
    """只读磁盘：document_id + content_hash + last_modified（不切 chunk）。"""
    documents: list[dict[str, object]] = []
    if not DATA_DIR.exists():
        return documents

    for guide_file in sorted(DATA_DIR.glob("*.md*")):
        if not guide_file.is_file():
            continue
        document_id = guide_file.name
        destination = destination_for_guide(document_id)
        if destination is None:
            raise ValueError(
                f"攻略文件缺少 destination 映射：{document_id}。"
                "请先在 app/rag/guide_catalog.py 中登记该文件。"
            )
        text = guide_file.read_text(encoding="utf-8")
        documents.append(
            {
                "document_id": document_id,
                "source_path": str(guide_file.relative_to(BACKEND_DIR)).replace("\\", "/"),
                "content_hash": compute_content_hash(text),
                "last_modified": guide_file.stat().st_mtime,
                "destination": destination,
            }
        )
    return documents


def scan_knowledge_changes() -> dict[str, list[dict[str, object]]]:
    """
    定时轮询用的变更感知：对比磁盘文件与 kb_documents 清单。

    返回四类结果：
    - added: 磁盘有、清单无
    - modified: 两边都有，但 content_hash 不同
    - unchanged: 两边都有，且 content_hash 相同
    - removed: 清单有、磁盘无（仅感知，不执行删除）
    """
    disk_docs = _scan_disk_documents()
    registry_docs = list_documents(status=None)
    registry_by_id = {record.document_id: record for record in registry_docs}

    added: list[dict[str, object]] = []
    modified: list[dict[str, object]] = []
    unchanged: list[dict[str, object]] = []

    for doc in disk_docs:
        document_id = str(doc["document_id"])
        record = registry_by_id.pop(document_id, None)
        item = {
            "document_id": document_id,
            "source_path": doc["source_path"],
            "content_hash": doc["content_hash"],
            "last_modified": doc["last_modified"],
            "destination": doc["destination"],
            "change": "added",
        }

        if record is None:
            item["change"] = "added"
            added.append(item)
            continue

        item["previous_content_hash"] = record.content_hash
        item["previous_last_modified"] = record.last_modified

        # 时间初筛：mtime 与 hash 都一致 → 未变；hash 不同 → 已修改
        if record.content_hash == doc["content_hash"]:
            item["change"] = "unchanged"
            unchanged.append(item)
        else:
            item["change"] = "modified"
            modified.append(item)

    # 清单里剩下的 = 磁盘上已经找不到的文档
    removed: list[dict[str, object]] = []
    for document_id, record in sorted(registry_by_id.items()):
        removed.append(
            {
                "document_id": document_id,
                "source_path": record.source_path,
                "content_hash": record.content_hash,
                "last_modified": record.last_modified,
                "destination": record.destination,
                "change": "removed",
            }
        )

    return {
        "added": added,
        "modified": modified,
        "unchanged": unchanged,
        "removed": removed,
    }


def summarize_changes(changes: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    """统计各类变更数量。"""
    return {
        "added": len(changes.get("added", [])),
        "modified": len(changes.get("modified", [])),
        "unchanged": len(changes.get("unchanged", [])),
        "removed": len(changes.get("removed", [])),
        "has_changes": bool(
            changes.get("added") or changes.get("modified") or changes.get("removed")
        ),
    }


def format_changes_report(changes: dict[str, list[dict[str, object]]]) -> str:
    """生成人类可读的轮询报告。"""
    summary = summarize_changes(changes)
    lines = [
        "=== 知识库轮询结果 ===",
        (
            f"added={summary['added']}  modified={summary['modified']}  "
            f"unchanged={summary['unchanged']}  removed={summary['removed']}"
        ),
        "",
    ]

    def _append_section(title: str, items: list[dict[str, object]]) -> None:
        lines.append(f"[{title}] ({len(items)})")
        if not items:
            lines.append("  (无)")
            lines.append("")
            return
        for item in items:
            document_id = item["document_id"]
            content_hash = str(item.get("content_hash", ""))[:12]
            extra = ""
            if item.get("previous_content_hash"):
                prev = str(item["previous_content_hash"])[:12]
                extra = f"  prev_hash={prev}..."
            lines.append(f"  - {document_id}  hash={content_hash}...{extra}")
        lines.append("")

    _append_section("新增 added", changes.get("added", []))
    _append_section("修改 modified", changes.get("modified", []))
    _append_section("未变 unchanged", changes.get("unchanged", []))
    _append_section("缺失 removed", changes.get("removed", []))
    return "\n".join(lines).rstrip() + "\n"


def apply_knowledge_changes(
    changes: dict[str, list[dict[str, object]]] | None = None,
    *,
    apply_removed: bool = True,
) -> dict[str, object]:
    """
    应用轮询结果：
    - added: 整篇切割 + embedding + 入库
    - modified: 先按 document_id 删旧 chunk，再整篇重建
    - removed: 清理相关 chunk + 移除清单（可用 apply_removed=False 跳过）
    - unchanged: 跳过
    """
    if changes is None:
        changes = scan_knowledge_changes()

    results: dict[str, object] = {
        "added": [],
        "modified": [],
        "removed": [],
        "unchanged": len(changes.get("unchanged", [])),
        "errors": [],
    }

    for item in changes.get("added", []):
        document_id = str(item["document_id"])
        try:
            written = ingest_single_document_to_chroma(document_id)
            results["added"].append(
                {"document_id": document_id, "written_chunks": written}
            )
            print(f"[kb] added {document_id}: written_chunks={written}")
        except Exception as exc:
            results["errors"].append(
                {"document_id": document_id, "action": "added", "error": str(exc)}
            )
            print(f"[kb] added failed {document_id}: {exc}")

    for item in changes.get("modified", []):
        document_id = str(item["document_id"])
        try:
            written = replace_document_in_chroma(document_id)
            results["modified"].append(
                {"document_id": document_id, "written_chunks": written}
            )
        except Exception as exc:
            results["errors"].append(
                {"document_id": document_id, "action": "modified", "error": str(exc)}
            )
            print(f"[kb] modified failed {document_id}: {exc}")

    if apply_removed:
        for item in changes.get("removed", []):
            document_id = str(item["document_id"])
            try:
                deleted = remove_document_from_chroma(document_id)
                results["removed"].append(
                    {"document_id": document_id, "deleted_chunks": deleted}
                )
            except Exception as exc:
                results["errors"].append(
                    {
                        "document_id": document_id,
                        "action": "removed",
                        "error": str(exc),
                    }
                )
                print(f"[kb] removed failed {document_id}: {exc}")

    applied_count = (
        len(results["added"])  # type: ignore[arg-type]
        + len(results["modified"])  # type: ignore[arg-type]
        + len(results["removed"])  # type: ignore[arg-type]
    )
    # 只要成功应用了变更，就清掉检索缓存，避免用户继续命中旧结果
    cache_invalidation = (
        invalidate_rag_caches() if applied_count > 0 else {"rag": 0, "rerank": 0, "total": 0}
    )

    results["cache_invalidation"] = cache_invalidation
    results["summary"] = {
        "added": len(results["added"]),  # type: ignore[arg-type]
        "modified": len(results["modified"]),  # type: ignore[arg-type]
        "removed": len(results["removed"]),  # type: ignore[arg-type]
        "unchanged": results["unchanged"],
        "errors": len(results["errors"]),  # type: ignore[arg-type]
        "cache_invalidated": cache_invalidation.get("total", 0),
    }
    return results


def format_apply_report(results: dict[str, object]) -> str:
    """格式化应用变更后的结果。"""
    summary = results.get("summary") or {}
    lines = [
        "=== 知识库变更已应用 ===",
        (
            f"added={summary.get('added', 0)}  modified={summary.get('modified', 0)}  "
            f"removed={summary.get('removed', 0)}  unchanged={summary.get('unchanged', 0)}  "
            f"errors={summary.get('errors', 0)}  "
            f"cache_invalidated={summary.get('cache_invalidated', 0)}"
        ),
        "",
    ]
    for action in ("added", "modified", "removed"):
        items = results.get(action) or []
        lines.append(f"[{action}] ({len(items)})")  # type: ignore[arg-type]
        if not items:
            lines.append("  (无)")
        else:
            for item in items:  # type: ignore[assignment]
                if action == "removed":
                    lines.append(
                        f"  - {item['document_id']}: deleted_chunks={item.get('deleted_chunks', 0)}"
                    )
                else:
                    lines.append(
                        f"  - {item['document_id']}: written_chunks={item.get('written_chunks', 0)}"
                    )
        lines.append("")

    errors = results.get("errors") or []
    if errors:
        lines.append(f"[errors] ({len(errors)})")  # type: ignore[arg-type]
        for err in errors:  # type: ignore[assignment]
            lines.append(
                f"  - {err.get('action')} {err.get('document_id')}: {err.get('error')}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
