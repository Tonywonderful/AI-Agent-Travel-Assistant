from app.services.recommendation_service import score_forecast_days


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
