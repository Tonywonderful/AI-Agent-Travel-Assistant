from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.recommendation_service import get_hot_destination_recommendations


class RecommendationForecastDay(BaseModel):
    date: str | None = None
    week: str | None = None
    day_weather: str | None = None
    night_weather: str | None = None
    day_temp: str | None = None
    night_temp: str | None = None
    day_wind: str | None = None
    night_wind: str | None = None


class DestinationRecommendationItem(BaseModel):
    city: str
    city_key: str
    tagline: str
    suggested_days: int
    default_preferences: list[str] = Field(default_factory=list)
    default_pace: str | None = None
    default_budget: int | None = None
    image_path: str
    weather_score: int
    weather_label: str
    weather_available: bool = True
    forecast_days: list[RecommendationForecastDay] = Field(default_factory=list)


class HotDestinationRecommendationResponse(BaseModel):
    items: list[DestinationRecommendationItem] = Field(default_factory=list)
    source: str
    forecast_days: int = 3


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/hot", response_model=HotDestinationRecommendationResponse)
def get_hot_recommendations() -> HotDestinationRecommendationResponse:
    """返回固定目的地池中按未来天气排序的热门推荐。"""
    try:
        payload = get_hot_destination_recommendations()
        return HotDestinationRecommendationResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
