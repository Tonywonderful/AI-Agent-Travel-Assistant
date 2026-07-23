"""工具统一返回结构，供 Chat Host 与 MCP 共用。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """原子工具执行结果。"""

    ok: bool = Field(..., description="是否成功")
    name: str = Field(..., description="工具名")
    data: Any = Field(default=None, description="结构化结果")
    error: str | None = Field(default=None, description="失败原因")
    summary: str = Field(default="", description="给模型/前端看的短摘要")
    source: str = Field(default="service", description="数据来源标记")

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "name": self.name,
            "summary": self.summary,
            "error": self.error,
            "source": self.source,
            "data": self.data,
        }

    def to_llm_content(self) -> str:
        """回灌给模型的紧凑文本，避免超长 JSON。"""
        import json

        payload = {
            "ok": self.ok,
            "tool": self.name,
            "summary": self.summary,
            "error": self.error,
            "data": self.data,
        }
        text = json.dumps(payload, ensure_ascii=False, default=str)
        if len(text) > 3500:
            text = text[:3500] + "…(truncated)"
        return text
