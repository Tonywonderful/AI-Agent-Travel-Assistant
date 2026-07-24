"""工具注册表：Chat tool-calling 与 MCP 共用同一批实现。"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from app.tools.base import ToolResult
from app.tools.knowledge_tools import tool_search_travel_guide
from app.tools.map_tools import tool_estimate_route, tool_geocode_place, tool_search_poi
from app.tools.weather_tools import tool_get_weather_forecast
from app.tools.web_search_tools import tool_web_search


logger = logging.getLogger(__name__)

ToolHandler = Callable[..., ToolResult]


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_weather_forecast": tool_get_weather_forecast,
    "geocode_place": tool_geocode_place,
    "search_poi": tool_search_poi,
    "estimate_route": tool_estimate_route,
    "web_search": tool_web_search,
    "search_travel_guide": tool_search_travel_guide,
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "get_weather_forecast",
        "description": (
            "查询指定城市的未来天气预报（气温、晴雨等）。"
            "当用户询问是否下雨、冷不冷、是否适合户外/看日落、是否需要带伞时使用。"
            "不要用此工具推荐景点。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名，例如 大理、成都。可从对话上下文目的地推断。",
                },
            },
            "required": ["city"],
        },
    },
    {
        "name": "geocode_place",
        "description": (
            "将地址或地点名称解析为经纬度与标准地址。"
            "当用户问某地在哪、需要坐标或规范化地址时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "地址或地点名，例如 大理古城、双廊古镇",
                },
                "city": {
                    "type": "string",
                    "description": "可选，限定城市以提高准确度",
                },
            },
            "required": ["address"],
        },
    },
    {
        "name": "search_poi",
        "description": (
            "按关键词搜索兴趣点（景点、餐厅、酒店等），返回名称、地址与坐标。"
            "当用户问附近有什么、某类地点推荐列表时使用。"
            "若用户提到具体片区（如大理古城、双廊），keyword 应带上片区，例如「大理古城 餐厅」。"
            "通常调用 1 次即可；拿到结果后直接整理成中文回答，不要反复换词搜索。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，优先含片区+品类，例如 大理古城 餐厅、双廊 咖啡",
                },
                "city": {
                    "type": "string",
                    "description": "可选城市，例如 大理",
                },
                "page_size": {
                    "type": "integer",
                    "description": "返回条数，默认 5，最大 10",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "estimate_route",
        "description": (
            "估算两点之间的驾车距离与时间。入参使用地点名称即可。"
            "当用户问多久、多远、一天行程会不会太赶时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "起点名称，例如 大理古城",
                },
                "destination": {
                    "type": "string",
                    "description": "终点名称，例如 双廊古镇",
                },
                "city": {
                    "type": "string",
                    "description": "可选，起终点所在城市",
                },
            },
            "required": ["origin", "destination"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "联网搜索公开网页信息，用于时效性内容："
            "景区预约/门票政策、开放时间变更、近期活动节庆、攻略避坑、交通公告等。"
            "不要用此工具查天气预报、精确驾车距离/时间、或结构化周边 POI 列表"
            "（那些应分别用 get_weather_forecast / estimate_route / search_poi）。"
            "也不要用此工具替代本地攻略库 search_travel_guide。"
            "搜索词尽量具体，可带城市与年份。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，例如「大理 崇圣寺 门票 预约 2026」",
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回结果条数量级，默认 5，最大 10",
                },
                "search_type": {
                    "type": "string",
                    "description": "auto（默认）| fast | deep",
                    "enum": ["auto", "fast", "deep"],
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_travel_guide",
        "description": (
            "检索项目本地旅行攻略知识库（策展过的玩法、避坑、节奏、景点/餐饮/住宿说明）。"
            "适合：怎么玩、和行程匹配的建议、本地攻略口径、避坑与体验要点。"
            "不适合：附近 POI 大全列表、精确坐标/距离、实时门票预约政策"
            "（那些用 search_poi / estimate_route / web_search）。"
            "必须能确定目的地城市：优先从对话上下文推断并传入 destination；"
            "若用户问题里已含城市名也可只传 question。"
            "城市未知时不要盲调；先向用户确认城市。"
            "工具内部会改写检索词并固定返回少量高相关片段。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "用户的问题或检索意图，例如「双廊看日落有什么要注意的」"
                        "「三天轻松怎么排」「古城附近住哪儿更合适」。"
                    ),
                },
                "destination": {
                    "type": "string",
                    "description": "目的地城市，例如 大理、成都。可从当前行程/规划上下文推断。",
                },
            },
            "required": ["question"],
        },
    },
]


def list_tool_names() -> list[str]:
    return list(TOOL_HANDLERS.keys())


def get_tool_specs() -> list[dict[str, Any]]:
    return TOOL_SPECS


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
    """按名称执行工具；未知工具返回失败结果。"""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return ToolResult(
            ok=False,
            name=name or "unknown",
            error=f"未知工具: {name}",
            summary=f"未知工具: {name}",
        )

    args = arguments or {}
    if not isinstance(args, dict):
        return ToolResult(
            ok=False,
            name=name,
            error="工具参数必须是对象",
            summary="工具参数格式错误",
        )

    try:
        result = handler(**args)
    except TypeError as exc:
        logger.warning("tool %s bad args %s: %s", name, args, exc)
        return ToolResult(
            ok=False,
            name=name,
            error=f"参数错误: {exc}",
            summary=f"{name} 参数错误",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("tool %s failed", name)
        return ToolResult(
            ok=False,
            name=name,
            error=str(exc),
            summary=f"{name} 执行失败: {exc}",
        )

    if not isinstance(result, ToolResult):
        return ToolResult(ok=True, name=name, data=result, summary=str(result)[:200])
    return result


def parse_tool_arguments(raw: Any) -> dict[str, Any]:
    """兼容模型返回的 dict / JSON 字符串参数。"""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    return {}
