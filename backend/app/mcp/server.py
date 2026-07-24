"""基于官方 MCP Python SDK（FastMCP）暴露旅行工具。

启动（在 backend 目录、已安装 mcp 包）：

  python -m app.mcp.server

或：

  python scripts/run_mcp_server.py

Chat 主路径默认直调 app.tools.registry（同内核），不强制经本进程；
本 Server 用于标准 MCP 客户端接入与简历/演示。
"""

from __future__ import annotations

import json
import logging
from typing import Any


logger = logging.getLogger(__name__)


def _result_to_text(result: Any) -> str:
    from app.tools.base import ToolResult

    if isinstance(result, ToolResult):
        return json.dumps(result.to_public_dict(), ensure_ascii=False, default=str)
    return json.dumps(result, ensure_ascii=False, default=str)


def build_mcp_server():
    """创建 FastMCP 实例并注册旅行工具。"""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "未安装 mcp 包。请执行: pip install mcp"
        ) from exc

    from app.tools.knowledge_tools import tool_search_travel_guide
    from app.tools.map_tools import (
        tool_estimate_route,
        tool_geocode_place,
        tool_search_poi,
    )
    from app.tools.weather_tools import tool_get_weather_forecast
    from app.tools.web_search_tools import tool_web_search

    mcp = FastMCP(
        name="travel-tools",
        instructions=(
            "旅行工具：本地攻略检索、天气、地理编码、POI 搜索、路线估算、联网搜索。"
            "底层复用项目 RAG / weather_service / map_service / Exa MCP。"
        ),
    )

    @mcp.tool(
        name="get_weather_forecast",
        description="查询指定城市未来天气预报。参数 city 为城市名。",
    )
    def get_weather_forecast(city: str) -> str:
        return _result_to_text(tool_get_weather_forecast(city=city))

    @mcp.tool(
        name="geocode_place",
        description="将地址或地点名解析为坐标。参数 address 必填，city 可选。",
    )
    def geocode_place(address: str, city: str = "") -> str:
        return _result_to_text(
            tool_geocode_place(address=address, city=city or None)
        )

    @mcp.tool(
        name="search_poi",
        description="按关键词搜索 POI。参数 keyword 必填，city 可选，page_size 默认 5。",
    )
    def search_poi(keyword: str, city: str = "", page_size: int = 5) -> str:
        return _result_to_text(
            tool_search_poi(
                keyword=keyword,
                city=city or None,
                page_size=page_size,
            )
        )

    @mcp.tool(
        name="estimate_route",
        description="估算两地驾车距离与时间。参数 origin、destination 必填，city 可选。",
    )
    def estimate_route(origin: str, destination: str, city: str = "") -> str:
        return _result_to_text(
            tool_estimate_route(
                origin=origin,
                destination=destination,
                city=city or None,
            )
        )

    @mcp.tool(
        name="web_search",
        description=(
            "联网搜索公开网页（门票预约、活动、攻略等）。"
            "参数 query 必填；num_results 默认 5；search_type=auto|fast|deep。"
        ),
    )
    def web_search(
        query: str,
        num_results: int = 5,
        search_type: str = "auto",
    ) -> str:
        return _result_to_text(
            tool_web_search(
                query=query,
                num_results=num_results,
                search_type=search_type,
            )
        )

    @mcp.tool(
        name="search_travel_guide",
        description=(
            "检索本地旅行攻略知识库。参数 question 必填；destination 可选（建议传入）。"
            "内部固定返回少量高相关片段。"
        ),
    )
    def search_travel_guide(question: str, destination: str = "") -> str:
        return _result_to_text(
            tool_search_travel_guide(
                question=question,
                destination=destination or None,
            )
        )

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    server = build_mcp_server()
    # stdio 传输，供 MCP Host 拉起
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
