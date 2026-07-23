"""天气相关工具内核。"""

from __future__ import annotations

from app.services.weather_service import get_weather_forecast
from app.tools.base import ToolResult


def tool_get_weather_forecast(city: str) -> ToolResult:
    """查询城市未来天气预报。"""
    name = "get_weather_forecast"
    city_text = (city or "").strip()
    if not city_text:
        return ToolResult(ok=False, name=name, error="city 不能为空", summary="缺少城市参数")

    try:
        result = get_weather_forecast(city_text)
    except Exception as exc:  # noqa: BLE001 - 工具边界吞掉外部异常
        return ToolResult(
            ok=False,
            name=name,
            error=str(exc),
            summary=f"天气查询失败：{exc}",
            source="amap_weather",
        )

    days = result.get("days") or []
    day_bits: list[str] = []
    for day in days[:5]:
        date = day.get("date") or "?"
        day_w = day.get("day_weather") or "?"
        night_w = day.get("night_weather") or "?"
        day_t = day.get("day_temp")
        night_t = day.get("night_temp")
        day_bits.append(f"{date} 白天{day_w}/{day_t}° 夜间{night_w}/{night_t}°")

    city_name = result.get("city") or city_text
    summary = f"{city_name}未来天气：" + ("；".join(day_bits) if day_bits else "暂无预报明细")
    return ToolResult(
        ok=True,
        name=name,
        data=result,
        summary=summary,
        source="amap_weather",
    )
