"""地图相关工具内核：地理编码 / POI / 路线。"""

from __future__ import annotations

from typing import Any

from app.services.map_service import estimate_route, geocode_address, search_places
from app.tools.base import ToolResult


def tool_geocode_place(address: str, city: str | None = None) -> ToolResult:
    """将地址或地点名解析为坐标。"""
    name = "geocode_place"
    address_text = (address or "").strip()
    if not address_text:
        return ToolResult(ok=False, name=name, error="address 不能为空", summary="缺少地址参数")

    try:
        result = geocode_address(address_text, city=(city or None))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            name=name,
            error=str(exc),
            summary=f"地理编码失败：{exc}",
            source="amap_map",
        )

    if not result:
        return ToolResult(
            ok=False,
            name=name,
            error="未找到匹配地址",
            summary=f"未解析到「{address_text}」的坐标",
            source="amap_map",
        )

    summary = (
        f"{result.get('formatted_address') or address_text} → "
        f"({result.get('longitude')}, {result.get('latitude')})"
    )
    return ToolResult(ok=True, name=name, data=result, summary=summary, source="amap_map")


def tool_search_poi(
    keyword: str,
    city: str | None = None,
    page_size: int = 5,
) -> ToolResult:
    """按关键词搜索 POI。"""
    name = "search_poi"
    keyword_text = (keyword or "").strip()
    if not keyword_text:
        return ToolResult(ok=False, name=name, error="keyword 不能为空", summary="缺少关键词")

    size = max(1, min(int(page_size or 5), 10))
    try:
        results = search_places(keyword=keyword_text, city=(city or None), page_size=size)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            name=name,
            error=str(exc),
            summary=f"POI 搜索失败：{exc}",
            source="amap_map",
        )

    if not results:
        return ToolResult(
            ok=False,
            name=name,
            error="无搜索结果",
            summary=f"未找到与「{keyword_text}」相关的地点",
            source="amap_map",
            data=[],
        )

    compact: list[dict[str, Any]] = []
    for item in results[:size]:
        compact.append(
            {
                "name": item.get("name"),
                "address": item.get("address"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "type": item.get("type"),
                "poi_id": item.get("poi_id"),
            }
        )

    names = "、".join(str(x.get("name") or "") for x in compact[:5] if x.get("name"))
    city_hint = f"{city} " if city else ""
    summary = f"{city_hint}「{keyword_text}」相关地点：{names or '（无名称）'}"
    return ToolResult(ok=True, name=name, data=compact, summary=summary, source="amap_map")


def _resolve_point(place: str, city: str | None) -> dict[str, Any] | None:
    """优先地理编码，失败再走 POI 首条。"""
    geo = geocode_address(place, city=city)
    if geo and geo.get("longitude") is not None and geo.get("latitude") is not None:
        return {
            "name": geo.get("formatted_address") or place,
            "longitude": geo.get("longitude"),
            "latitude": geo.get("latitude"),
            "via": "geocode",
        }

    pois = search_places(keyword=place, city=city, page_size=1)
    if pois:
        first = pois[0]
        if first.get("longitude") is not None and first.get("latitude") is not None:
            return {
                "name": first.get("name") or place,
                "longitude": first.get("longitude"),
                "latitude": first.get("latitude"),
                "via": "poi",
            }
    return None


def tool_estimate_route(
    origin: str,
    destination: str,
    city: str | None = None,
) -> ToolResult:
    """估算两地驾车距离与耗时；入参用地名，内部解析坐标。"""
    name = "estimate_route"
    origin_text = (origin or "").strip()
    dest_text = (destination or "").strip()
    if not origin_text or not dest_text:
        return ToolResult(
            ok=False,
            name=name,
            error="origin/destination 不能为空",
            summary="缺少起点或终点",
        )

    try:
        origin_point = _resolve_point(origin_text, city)
        dest_point = _resolve_point(dest_text, city)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            name=name,
            error=str(exc),
            summary=f"解析起终点失败：{exc}",
            source="amap_map",
        )

    if origin_point is None:
        return ToolResult(
            ok=False,
            name=name,
            error=f"无法解析起点：{origin_text}",
            summary=f"无法解析起点「{origin_text}」",
            source="amap_map",
        )
    if dest_point is None:
        return ToolResult(
            ok=False,
            name=name,
            error=f"无法解析终点：{dest_text}",
            summary=f"无法解析终点「{dest_text}」",
            source="amap_map",
        )

    try:
        route = estimate_route(
            origin_longitude=float(origin_point["longitude"]),
            origin_latitude=float(origin_point["latitude"]),
            destination_longitude=float(dest_point["longitude"]),
            destination_latitude=float(dest_point["latitude"]),
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            name=name,
            error=str(exc),
            summary=f"路线估算失败：{exc}",
            source="amap_map",
        )

    if not route:
        return ToolResult(
            ok=False,
            name=name,
            error="无路线结果",
            summary=f"未能估算 {origin_text} → {dest_text} 的路线",
            source="amap_map",
        )

    data = {
        "origin": origin_point,
        "destination": dest_point,
        "route": route,
    }
    summary = (
        f"{origin_point.get('name')} → {dest_point.get('name')}："
        f"约 {route.get('distance_km')} km / {route.get('estimated_minutes')} 分钟（驾车估算）"
    )
    return ToolResult(ok=True, name=name, data=data, summary=summary, source="amap_map")
