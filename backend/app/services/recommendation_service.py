from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.config import REDIS_WEATHER_TTL_SECONDS
from app.services.cache_service import get_cached_json, set_cached_json
from app.services.weather_service import get_weather_forecast


logger = logging.getLogger(__name__)

# 固定优质目的地池：与知识库攻略城市对齐。
# adcode 为高德行政区划码，天气查询直接使用，避免额外 geocode。
DESTINATION_CATALOG: list[dict[str, Any]] = [
    {
        "city": "北京",
        "city_key": "beijing",
        "adcode": "110000",
        "tagline": "古迹与城市风光",
        "suggested_days": 3,
        "default_preferences": ["拍照", "古镇", "美食"],
        "default_pace": "适中",
        "default_budget": 4200,
        "image_path": "/covers/beijing.png",
    },
    {
        "city": "成都",
        "city_key": "chengdu",
        "adcode": "510100",
        "tagline": "美食与慢生活",
        "suggested_days": 3,
        "default_preferences": ["美食", "休闲", "拍照"],
        "default_pace": "轻松",
        "default_budget": 3200,
        "image_path": "/covers/chengdu.png",
    },
    {
        "city": "大理",
        "city_key": "dali",
        "adcode": "532901",
        "tagline": "风花雪月，轻松慢游",
        "suggested_days": 3,
        "default_preferences": ["自然风景", "拍照", "古镇"],
        "default_pace": "轻松",
        "default_budget": 3200,
        "image_path": "/covers/dali.png",
    },
    {
        "city": "三亚",
        "city_key": "sanya",
        "adcode": "460200",
        "tagline": "阳光海岸度假",
        "suggested_days": 4,
        "default_preferences": ["自然风景", "休闲", "拍照"],
        "default_pace": "轻松",
        "default_budget": 4800,
        "image_path": "/covers/sanya.png",
    },
    {
        "city": "厦门",
        "city_key": "xiamen",
        "adcode": "350200",
        "tagline": "文艺海岛与老街",
        "suggested_days": 3,
        "default_preferences": ["拍照", "美食", "休闲"],
        "default_pace": "轻松",
        "default_budget": 3600,
        "image_path": "/covers/xiamen.png",
    },
    {
        "city": "西安",
        "city_key": "xian",
        "adcode": "610100",
        "tagline": "历史厚重，烟火气足",
        "suggested_days": 3,
        "default_preferences": ["古镇", "美食", "拍照"],
        "default_pace": "适中",
        "default_budget": 3500,
        "image_path": "/covers/xian.png",
    },
]

_FORECAST_DAYS = 3
_CACHE_KEY = "recommendations:hot:v2"
# 有界并发：避开高德个人开发者常见 QPS/瞬时并发限制，同时比串行快。
# 6 城场景下 4 已足够；城市变多时也不会无脑打满。
_WEATHER_MAX_WORKERS = 4


def _weather_text_score(text: str | None) -> int:
    """根据天气描述给粗分，越高越适合出行。"""
    value = (text or "").strip()
    if not value:
        return 55

    if any(token in value for token in ("暴雨", "大暴雨", "暴雪", "台风", "冰雹")):
        return 10
    if any(token in value for token in ("大雨", "大雪", "雷阵雨", "雷电")):
        return 25
    if any(token in value for token in ("中雨", "中雪", "雨夹雪")):
        return 35
    if any(token in value for token in ("小雨", "阵雨", "小雪", "雨", "雪")):
        return 45
    if any(token in value for token in ("雾", "霾", "沙尘")):
        return 40
    if "阴" in value:
        return 65
    if any(token in value for token in ("多云", "少云", "晴间多云")):
        return 85
    if "晴" in value:
        return 95
    return 60


def _parse_temp(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if match is None:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _temperature_adjustment(day_temp: str | None, night_temp: str | None) -> int:
    """极端气温扣分，舒适区间轻微加分。"""
    day = _parse_temp(day_temp)
    night = _parse_temp(night_temp)
    temps = [t for t in (day, night) if t is not None]
    if not temps:
        return 0

    avg = sum(temps) / len(temps)
    if avg >= 36 or avg <= 0:
        return -20
    if avg >= 33 or avg <= 5:
        return -10
    if 18 <= avg <= 28:
        return 5
    return 0


def score_forecast_days(days: list[dict[str, Any]], limit: int = _FORECAST_DAYS) -> tuple[int, str]:
    """综合未来若干天天气，返回 0-100 分和短标签。"""
    selected = list(days or [])[:limit]
    if not selected:
        return 50, "天气暂缺"

    day_scores: list[int] = []
    labels: list[str] = []
    for day in selected:
        day_weather = day.get("day_weather")
        night_weather = day.get("night_weather")
        base = int(
            round(
                (
                    _weather_text_score(day_weather) * 0.7
                    + _weather_text_score(night_weather) * 0.3
                )
            )
        )
        base += _temperature_adjustment(day.get("day_temp"), day.get("night_temp"))
        day_scores.append(max(0, min(100, base)))
        if day_weather:
            labels.append(str(day_weather))

    score = int(round(sum(day_scores) / len(day_scores))) if day_scores else 50
    label = _build_weather_label(labels, score)
    return score, label


def _build_weather_label(weather_names: list[str], score: int) -> str:
    if not weather_names:
        return "天气暂缺"

    # 取出现最多的白天天气作为主描述。
    counts: dict[str, int] = {}
    for name in weather_names:
        counts[name] = counts.get(name, 0) + 1
    primary = max(counts.items(), key=lambda item: item[1])[0]

    if score >= 80:
        return f"未来{_FORECAST_DAYS}天多{primary}，适合出行"
    if score >= 60:
        return f"未来{_FORECAST_DAYS}天以{primary}为主"
    if score >= 40:
        return f"未来{_FORECAST_DAYS}天有{primary}，出行注意安排"
    return f"未来{_FORECAST_DAYS}天天气一般（{primary}）"


def _summarize_city(city_meta: dict[str, Any]) -> dict[str, Any]:
    city = city_meta["city"]
    adcode = city_meta.get("adcode")
    try:
        forecast = get_weather_forecast(city, adcode=adcode)
        score, label = score_forecast_days(forecast.get("days") or [])
        days = (forecast.get("days") or [])[:_FORECAST_DAYS]
        return {
            "city": city,
            "city_key": city_meta["city_key"],
            "tagline": city_meta["tagline"],
            "suggested_days": city_meta["suggested_days"],
            "default_preferences": list(city_meta["default_preferences"]),
            "default_pace": city_meta["default_pace"],
            "default_budget": city_meta["default_budget"],
            "image_path": city_meta["image_path"],
            "weather_score": score,
            "weather_label": label,
            "forecast_days": days,
            "weather_available": True,
        }
    except Exception as exc:
        logger.warning("获取 %s 天气失败，使用兜底推荐：%s", city, exc)
        return {
            "city": city,
            "city_key": city_meta["city_key"],
            "tagline": city_meta["tagline"],
            "suggested_days": city_meta["suggested_days"],
            "default_preferences": list(city_meta["default_preferences"]),
            "default_pace": city_meta["default_pace"],
            "default_budget": city_meta["default_budget"],
            "image_path": city_meta["image_path"],
            "weather_score": 50,
            "weather_label": "天气暂不可用，仍可规划",
            "forecast_days": [],
            "weather_available": False,
        }


def _summarize_cities_parallel(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """有界并发拉取各城市天气并汇总。"""
    if not catalog:
        return []
    if len(catalog) == 1:
        return [_summarize_city(catalog[0])]

    workers = max(1, min(_WEATHER_MAX_WORKERS, len(catalog)))
    items: list[dict[str, Any] | None] = [None] * len(catalog)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(_summarize_city, meta): index
            for index, meta in enumerate(catalog)
        }
        for future in as_completed(future_map):
            index = future_map[future]
            items[index] = future.result()
    return [item for item in items if item is not None]


def get_hot_destination_recommendations() -> dict[str, Any]:
    """返回按天气排序的热门目的地推荐。"""
    cached = get_cached_json(_CACHE_KEY)
    if cached is not None:
        return cached

    items = _summarize_cities_parallel(DESTINATION_CATALOG)
    items.sort(key=lambda item: (-int(item.get("weather_score") or 0), item["city"]))

    result = {
        "items": items,
        "source": "guide_destinations+weather",
        "forecast_days": _FORECAST_DAYS,
    }
    # 与天气缓存同级即可，避免推荐结果比天气更“新鲜”。
    set_cached_json(_CACHE_KEY, result, expire_seconds=REDIS_WEATHER_TTL_SECONDS)
    return result
