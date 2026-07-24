"""对话 SSE 路由。

事件协议：
  event: status       data: {"status":"thinking"|"streaming"|"tool"}
  event: tool_start   data: {"name":"...","args":{...}}
  event: tool_result  data: {"name":"...","ok":true,"summary":"...","error":null}
  event: token        data: {"text":"..."}
  event: error        data: {"message":"..."}
  event: done         data: {"ok":true}
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.chat_schemas import ChatStreamRequest
from app.services.chat_service import iter_chat_events
from app.tools.registry import list_tool_names


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _stream_chat_events(request: ChatStreamRequest) -> Iterator[str]:
    yield _sse("status", {"status": "thinking"})
    try:
        saw_token = False
        for event in iter_chat_events(request):
            event_type = event.get("type")
            if event_type == "tool_start":
                yield _sse("status", {"status": "tool"})
                yield _sse(
                    "tool_start",
                    {
                        "name": event.get("name"),
                        "args": event.get("args") or {},
                    },
                )
            elif event_type == "tool_result":
                yield _sse(
                    "tool_result",
                    {
                        "name": event.get("name"),
                        "ok": bool(event.get("ok")),
                        "summary": event.get("summary") or "",
                        "error": event.get("error"),
                    },
                )
            elif event_type == "token":
                text = event.get("text")
                if not text:
                    continue
                if not saw_token:
                    yield _sse("status", {"status": "streaming"})
                    saw_token = True
                yield _sse("token", {"text": text})
        yield _sse("done", {"ok": True})
    except ValueError as exc:
        logger.warning("chat stream validation/business error: %s", exc)
        yield _sse("error", {"message": str(exc)})
        yield _sse("done", {"ok": False})
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat stream failed")
        yield _sse("error", {"message": f"对话生成失败：{exc}"})
        yield _sse("done", {"ok": False})


@router.post("/stream")
def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    """流式对话接口（SSE），支持 tool_start / tool_result。"""
    return StreamingResponse(
        _stream_chat_events(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
def chat_health() -> dict:
    """对话模块存活检查。"""
    return {
        "status": "ok",
        "module": "chat",
        "tools": list_tool_names(),
    }


@router.get("/tools")
def chat_tools() -> dict:
    """列出助手可用工具（便于联调，非 MCP 协议本身）。"""
    from app.tools.registry import get_tool_specs

    return {"tools": get_tool_specs()}
