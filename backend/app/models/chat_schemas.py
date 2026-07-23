"""阶段 1 对话助手请求模型。

与行程 schemas 解耦，后续 Phase 2 增加 tool 事件时只扩展本文件与 chat 链路。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant", "system"]
ChatPage = Literal["planning", "result", "history"]


class ChatMessage(BaseModel):
    """单条对话消息。"""

    role: ChatRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息文本")


class ChatItineraryContext(BaseModel):
    """注入给助手的行程摘要（只读，阶段 1 不提供写工具）。"""

    trip_id: str | None = Field(default=None, description="行程 ID")
    destination: str | None = Field(default=None, description="目的地")
    summary: str | None = Field(default=None, description="行程概述")
    day_count: int | None = Field(default=None, ge=0, description="行程天数")
    estimated_budget: float | None = Field(default=None, ge=0, description="预估预算")
    day_titles: list[str] = Field(
        default_factory=list,
        description="每日一句话摘要，例如「第1天：古城漫步」",
    )


class ChatPlanningContext(BaseModel):
    """规划页表单快照（可选，只读）。"""

    destination: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    travelers: int | None = Field(default=None, ge=1)
    budget: float | None = Field(default=None, ge=0)
    pace: str | None = None
    preferences: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    hotel_level: str | None = None
    special_notes: str | None = None


class ChatContext(BaseModel):
    """前端注入的只读上下文，阶段 1 无工具调用。"""

    page: ChatPage = Field(default="planning", description="当前页面")
    itinerary: ChatItineraryContext | None = Field(
        default=None,
        description="当前结果页行程摘要",
    )
    planning: ChatPlanningContext | None = Field(
        default=None,
        description="规划页表单摘要",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="预留扩展字段，阶段 2 可放 tool 开关等",
    )


class ChatStreamRequest(BaseModel):
    """SSE 流式对话请求体。"""

    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        description="完整对话历史，最后一条应为 user",
    )
    context: ChatContext = Field(
        default_factory=ChatContext,
        description="只读业务上下文",
    )
