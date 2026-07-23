"""
知识库定时轮询脚本：扫描 data/*.md，对比 kb_documents，感知变更。

用法：
  # 扫一次
  python scripts/poll_knowledge_base.py

  # 每 60 秒扫一次（前台循环，Ctrl+C 结束）
  python scripts/poll_knowledge_base.py --interval 60
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
    format_changes_report,
    scan_knowledge_changes,
    summarize_changes,
)


def run_once() -> dict[str, int]:
    changes = scan_knowledge_changes()
    print(format_changes_report(changes), end="")
    return summarize_changes(changes)


def main() -> int:
    parser = argparse.ArgumentParser(description="轮询本地知识库文档变更")
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="轮询间隔秒数；0 表示只扫一次（默认）",
    )
    args = parser.parse_args()

    if args.interval < 0:
        print("interval 不能为负数", file=sys.stderr)
        return 2

    if args.interval == 0:
        summary = run_once()
        # 有变更时退出码 1，方便外部脚本判断；无变更退出 0
        return 1 if summary["has_changes"] else 0

    print(f"开始定时轮询：每 {args.interval} 秒扫描一次（Ctrl+C 结束）")
    try:
        while True:
            print(f"\n--- poll at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            run_once()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止轮询")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
