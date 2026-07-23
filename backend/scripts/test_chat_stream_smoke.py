"""本地冒烟：验证 /chat/stream SSE 事件形状（需要后端已启动且配置 LLM）。

用法（项目 backend 目录或仓库根目录均可，注意 API 地址）：

  python backend/scripts/test_chat_stream_smoke.py
  python backend/scripts/test_chat_stream_smoke.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Chat SSE smoke test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/chat/stream"
    payload = {
        "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
        "context": {"page": "planning"},
    }

    print(f"POST {url}")
    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", url, json=payload) as response:
            print(f"status={response.status_code}")
            if response.status_code != 200:
                print(response.read().decode("utf-8", errors="replace"))
                return 1

            buffer = ""
            token_count = 0
            for chunk in response.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    block, buffer = buffer.split("\n\n", 1)
                    event = "message"
                    data_raw = ""
                    for line in block.splitlines():
                        if line.startswith("event:"):
                            event = line[6:].strip()
                        elif line.startswith("data:"):
                            data_raw = line[5:].strip()
                    if not data_raw:
                        continue
                    data = json.loads(data_raw)
                    if event == "token":
                        token_count += 1
                        sys.stdout.write(str(data.get("text", "")))
                        sys.stdout.flush()
                    elif event in {"status", "error", "done"}:
                        print(f"\n[{event}] {data}")

            print(f"\ntoken_events={token_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
