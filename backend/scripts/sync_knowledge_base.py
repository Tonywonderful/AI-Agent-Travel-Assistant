"""
知识库同步脚本：轮询变更并应用。

  新增 → 切割 + embedding + 入库
  修改 → 先删旧 chunk，再整篇重建
  删除 → 清理相关 chunk + 清单

用法：
  # 只看变更，不写入
  python scripts/sync_knowledge_base.py --dry-run

  # 扫描并应用一次
  python scripts/sync_knowledge_base.py

  # 每 60 秒自动同步
  python scripts/sync_knowledge_base.py --interval 60

  # 应用时跳过删除（只处理新增/修改）
  python scripts/sync_knowledge_base.py --skip-removed
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.knowledge_poller import (  # noqa: E402
    apply_knowledge_changes,
    format_apply_report,
    format_changes_report,
    scan_knowledge_changes,
    summarize_changes,
)


def run_once(*, dry_run: bool, apply_removed: bool) -> dict[str, object]:
    changes = scan_knowledge_changes()
    print(format_changes_report(changes), end="")

    if dry_run:
        print("（dry-run：仅感知，未写入向量库）")
        return {"dry_run": True, "summary": summarize_changes(changes)}

    results = apply_knowledge_changes(changes, apply_removed=apply_removed)
    print(format_apply_report(results), end="")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="同步本地知识库文档变更到向量库")
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="同步间隔秒数；0 表示只执行一次（默认）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只扫描报告变更，不写入/删除",
    )
    parser.add_argument(
        "--skip-removed",
        action="store_true",
        help="不处理 removed（不删向量、不删清单）",
    )
    args = parser.parse_args()

    if args.interval < 0:
        print("interval 不能为负数", file=sys.stderr)
        return 2

    apply_removed = not args.skip_removed

    if args.interval == 0:
        results = run_once(dry_run=args.dry_run, apply_removed=apply_removed)
        if args.dry_run:
            summary = results.get("summary") or {}
            return 1 if summary.get("has_changes") else 0
        summary = results.get("summary") or {}
        if summary.get("errors", 0):
            return 2
        applied = (
            summary.get("added", 0)
            + summary.get("modified", 0)
            + summary.get("removed", 0)
        )
        return 0 if applied >= 0 else 1

    mode = "dry-run" if args.dry_run else "apply"
    print(
        f"开始定时同步（{mode}）：每 {args.interval} 秒一次（Ctrl+C 结束）"
    )
    try:
        while True:
            print(f"\n--- sync at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            run_once(dry_run=args.dry_run, apply_removed=apply_removed)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止同步")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
