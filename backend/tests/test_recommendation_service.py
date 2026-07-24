from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app.services.recommendation_service import (
    DESTINATION_CATALOG,
    get_hot_destination_recommendations,
    score_forecast_days,
)


def test_score_forecast_days_prefers_sunny_over_rainy() -> None:
    sunny_score, sunny_label = score_forecast_days(
        [
            {"day_weather": "晴", "night_weather": "晴", "day_temp": "26", "night_temp": "18"},
            {"day_weather": "多云", "night_weather": "晴", "day_temp": "25", "night_temp": "17"},
            {"day_weather": "晴", "night_weather": "多云", "day_temp": "27", "night_temp": "19"},
        ]
    )
    rainy_score, rainy_label = score_forecast_days(
        [
            {"day_weather": "中雨", "night_weather": "小雨", "day_temp": "22", "night_temp": "18"},
            {"day_weather": "大雨", "night_weather": "中雨", "day_temp": "21", "night_temp": "17"},
            {"day_weather": "暴雨", "night_weather": "大雨", "day_temp": "20", "night_temp": "16"},
        ]
    )

    assert sunny_score > rainy_score
    assert "适合出行" in sunny_label or "晴" in sunny_label
    assert "雨" in rainy_label or "一般" in rainy_label


def test_score_forecast_days_handles_empty() -> None:
    score, label = score_forecast_days([])
    assert score == 50
    assert "暂缺" in label


def test_extreme_heat_reduces_score() -> None:
    mild_score, _ = score_forecast_days(
        [{"day_weather": "晴", "night_weather": "晴", "day_temp": "26", "night_temp": "18"}]
    )
    hot_score, _ = score_forecast_days(
        [{"day_weather": "晴", "night_weather": "晴", "day_temp": "38", "night_temp": "30"}]
    )
    assert mild_score > hot_score


def test_destination_catalog_has_adcode() -> None:
    assert DESTINATION_CATALOG
    for item in DESTINATION_CATALOG:
        assert item.get("adcode")
        assert str(item["adcode"]).isdigit()


def test_get_hot_destination_recommendations_uses_adcode_and_parallel() -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_forecast(city: str, adcode: str | None = None):
        calls.append((city, adcode))
        score_temp = "26" if city == "成都" else "38"
        weather = "晴" if city == "成都" else "中雨"
        return {
            "city": city,
            "days": [
                {
                    "date": "2026-07-25",
                    "week": "6",
                    "day_weather": weather,
                    "night_weather": weather,
                    "day_temp": score_temp,
                    "night_temp": "20",
                }
            ]
            * 3,
        }

    with (
        patch("app.services.recommendation_service.get_cached_json", return_value=None),
        patch("app.services.recommendation_service.set_cached_json"),
        patch("app.services.recommendation_service.get_weather_forecast", side_effect=fake_forecast),
        patch(
            "app.services.recommendation_service.ThreadPoolExecutor",
            wraps=ThreadPoolExecutor,
        ) as executor_cls,
    ):
        result = get_hot_destination_recommendations()

    assert len(result["items"]) == len(DESTINATION_CATALOG)
    assert {city for city, _ in calls} == {item["city"] for item in DESTINATION_CATALOG}
    assert all(adcode for _, adcode in calls)
    # 有界并发：worker 数不超过城市数，且不超过配置上限 4。
    assert executor_cls.call_args.kwargs["max_workers"] == min(4, len(DESTINATION_CATALOG))
    assert result["items"][0]["city"] == "成都"
