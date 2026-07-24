"""工具注册表单元测试（不打真实高德/Exa，mock service）。"""

from app.tools.registry import execute_tool, list_tool_names, parse_tool_arguments


def test_list_tools_includes_web_search():
    names = list_tool_names()
    assert set(names) == {
        "get_weather_forecast",
        "geocode_place",
        "search_poi",
        "estimate_route",
        "web_search",
        "search_travel_guide",
    }


def test_unknown_tool():
    result = execute_tool("not_exist", {})
    assert result.ok is False
    assert "未知" in (result.error or "")


def test_parse_tool_arguments():
    assert parse_tool_arguments('{"city":"大理"}') == {"city": "大理"}
    assert parse_tool_arguments({"city": "大理"}) == {"city": "大理"}
    assert parse_tool_arguments("not-json") == {}


def test_weather_tool_success(monkeypatch):
    monkeypatch.setattr(
        "app.tools.weather_tools.get_weather_forecast",
        lambda city: {
            "city": city,
            "days": [
                {
                    "date": "2026-07-23",
                    "day_weather": "晴",
                    "night_weather": "多云",
                    "day_temp": "28",
                    "night_temp": "18",
                }
            ],
        },
    )
    result = execute_tool("get_weather_forecast", {"city": "大理"})
    assert result.ok is True
    assert "大理" in result.summary
    assert result.data["city"] == "大理"


def test_geocode_empty_address():
    result = execute_tool("geocode_place", {"address": ""})
    assert result.ok is False


def test_web_search_empty_query():
    result = execute_tool("web_search", {"query": ""})
    assert result.ok is False


def test_web_search_success(monkeypatch):
    monkeypatch.setattr(
        "app.tools.web_search_tools._call_exa_web_search",
        lambda **kwargs: "Title: 大理攻略\n崇圣寺需提前预约门票。",
    )
    result = execute_tool("web_search", {"query": "大理 崇圣寺 门票 预约"})
    assert result.ok is True
    assert result.source == "exa_mcp"
    assert "崇圣寺" in result.data["text"]
