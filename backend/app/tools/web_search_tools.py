"""联网搜索工具：复用 OpenCode 同款 Exa MCP 免费端点。

参考：opencode-dev packages/opencode/src/tool/mcp-websearch.ts
默认 POST https://mcp.exa.ai/mcp 调用 web_search_exa，可不配置 API Key。
可选 EXA_API_KEY 提高配额/稳定性。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import (
    EXA_API_KEY,
    EXA_MCP_URL,
    EXA_SEARCH_TIMEOUT_SECONDS,
    WEB_SEARCH_CONTEXT_MAX_CHARS,
    WEB_SEARCH_DEFAULT_NUM_RESULTS,
)
from app.tools.base import ToolResult


logger = logging.getLogger(__name__)

TOOL_NAME = "web_search"
MAX_RESPONSE_BYTES = 256 * 1024


def _exa_url() -> str:
    base = (EXA_MCP_URL or "https://mcp.exa.ai/mcp").strip()
    if not EXA_API_KEY:
        return base
    # 与 OpenCode 一致：可选把 key 挂到 query
    from urllib.parse import quote

    sep = "&" if "?" in base else "?"
    return f"{base}{sep}exaApiKey={quote(EXA_API_KEY, safe='')}"


def _parse_mcp_payload(payload: str) -> str | None:
    text = payload.strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    result = data.get("result")
    if not isinstance(result, dict):
        # 也可能是 error 对象
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or str(err)
            raise RuntimeError(f"Exa MCP error: {msg}")
        return None

    content = result.get("content")
    if not isinstance(content, list):
        return None
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
            return str(item["text"])
        if isinstance(item, dict) and item.get("text"):
            return str(item["text"])
    return None


def _parse_mcp_response_body(body: str) -> str | None:
    """兼容 application/json 与 text/event-stream。"""
    direct = _parse_mcp_payload(body)
    if direct:
        return direct
    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        hit = _parse_mcp_payload(data)
        if hit:
            return hit
    return None


def _call_exa_web_search(
    *,
    query: str,
    num_results: int,
    search_type: str,
    livecrawl: str,
    context_max_characters: int,
) -> str:
    url = _exa_url()
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "web_search_exa",
            "arguments": {
                "query": query,
                "type": search_type,
                "numResults": num_results,
                "livecrawl": livecrawl,
                "contextMaxCharacters": context_max_characters,
            },
        },
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": "zhilv-yuntu/web_search",
    }

    with httpx.Client(timeout=EXA_SEARCH_TIMEOUT_SECONDS) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        body = resp.text

    if len(body.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise RuntimeError("搜索响应过大，已中止解析")

    text = _parse_mcp_response_body(body)
    if not text:
        raise RuntimeError("未解析到搜索结果（MCP 响应格式异常或为空）")
    return text


def tool_web_search(
    query: str,
    num_results: int | None = None,
    search_type: str = "auto",
) -> ToolResult:
    """联网搜索公开网页信息（时效政策、活动、攻略等）。"""
    q = (query or "").strip()
    if not q:
        return ToolResult(
            ok=False,
            name=TOOL_NAME,
            error="query 不能为空",
            summary="缺少搜索关键词",
            source="exa_mcp",
        )

    n = num_results if num_results is not None else WEB_SEARCH_DEFAULT_NUM_RESULTS
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = WEB_SEARCH_DEFAULT_NUM_RESULTS
    n = max(1, min(n, 10))

    st = (search_type or "auto").strip().lower()
    if st not in {"auto", "fast", "deep"}:
        st = "auto"

    try:
        text = _call_exa_web_search(
            query=q,
            num_results=n,
            search_type=st,
            livecrawl="fallback",
            context_max_characters=WEB_SEARCH_CONTEXT_MAX_CHARS,
        )
    except Exception as exc:  # noqa: BLE001 - 工具边界
        logger.warning("web_search failed query=%s: %s", q, exc)
        return ToolResult(
            ok=False,
            name=TOOL_NAME,
            error=str(exc),
            summary=f"联网搜索失败：{exc}",
            source="exa_mcp",
        )

    # 控制回灌长度，避免撑爆上下文
    truncated = text
    max_len = max(1500, WEB_SEARCH_CONTEXT_MAX_CHARS)
    if len(truncated) > max_len:
        truncated = truncated[:max_len] + "…(truncated)"

    summary = f"联网搜索「{q}」完成（{n} 条量级）"
    return ToolResult(
        ok=True,
        name=TOOL_NAME,
        data={"query": q, "num_results": n, "search_type": st, "text": truncated},
        summary=summary,
        source="exa_mcp",
    )
