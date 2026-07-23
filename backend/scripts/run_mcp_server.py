"""启动旅行工具 MCP Server（stdio）。

用法（在 backend 目录）：

  .venv/Scripts/python scripts/run_mcp_server.py

依赖：pip install mcp
"""

from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    try:
        from app.mcp.server import main as run_server
    except Exception as exc:  # noqa: BLE001
        print(f"无法加载 MCP Server: {exc}", file=sys.stderr)
        print("请确认已安装依赖: pip install mcp", file=sys.stderr)
        return 1
    run_server()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
