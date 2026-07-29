"""行程生成链路上的名称回查校验。

覆盖的是「模型输出解析成功」这条路径——此前这条路径完全信任模型输出，
prompt 里的「只用攻略真实名称」没有任何代码层面的保证。
"""

from pathlib import Path
import sys


# 允许测试文件直接导入 backend/app 下的模块。
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.trip_planner_agent import PlannerDayDraft, PlannerDraft  # noqa: E402
from app.models.schemas import TripRequest  # noqa: E402
import app.services.trip_service as trip_service  # noqa: E402
from app.services.trip_service import generate_trip_itinerary  # noqa: E402


CONTEXTS = [
    "[来源: dali_guide.md | 标题: 2.1 大理古城-南门楼]\n"
    "* **位置**：古城区大理古城一塔路42号\n"
    "* **简介**：适合拍照留念，傍晚人少。",
    "[来源: dali_guide.md | 标题: 经济实惠]\n"
    "* **【大理乐客特色小吃】招牌菜**：过桥米线。人均预算 **25元**。",
    "[来源: dali_guide.md | 标题: 经济型]\n"
    "* **【大理邻步客栈】**：交通便利。酒店预算：**180元/晚**。",
]

EMPTY_USAGE = {"prompt_tokens": 0, "completion_tokens": 0}


def build_trip_request(days: int = 2) -> TripRequest:
    return TripRequest(
        destination="大理",
        start_date="2026-04-10",
        end_date=f"2026-04-{9 + days:02d}",
        travelers=2,
        budget=3200,
        preferences=["自然风景"],
        pace="轻松",
        dietary_preferences=[],
        hotel_level="舒适型",
        special_notes="",
    )


def build_day(day_index: int, spot: str, meal: str) -> PlannerDayDraft:
    return PlannerDayDraft(
        day_index=day_index,
        theme=f"第 {day_index} 天",
        spot_name=spot,
        spot_description="模型给出的景点说明。",
        meal_name=meal,
        meal_notes="模型给出的餐饮说明。",
        daily_note="模型给出的当天备注。",
    )


def patch_pipeline(monkeypatch, draft, contexts=CONTEXTS) -> None:
    monkeypatch.setattr(
        trip_service,
        "collect_trip_context",
        lambda **_: (contexts, EMPTY_USAGE, EMPTY_USAGE, EMPTY_USAGE),
    )
    monkeypatch.setattr(
        trip_service,
        "generate_planner_draft",
        lambda *_: (draft, EMPTY_USAGE),
    )
    monkeypatch.setattr(trip_service, "ENABLE_AMAP_ENRICHMENT", False)


def test_verified_llm_names_are_kept(monkeypatch) -> None:
    """名称能在攻略里找到出处时，模型输出照常采用。"""
    draft = PlannerDraft(
        summary="大理慢游",
        tips=["带薄外套"],
        days=[
            build_day(1, "大理古城-南门楼", "大理乐客特色小吃"),
            build_day(2, "大理古城-南门楼", "过桥米线"),
        ],
    )
    patch_pipeline(monkeypatch, draft)

    itinerary = generate_trip_itinerary(build_trip_request())

    assert itinerary.days[0].spots[0].name == "大理古城-南门楼"
    assert itinerary.days[0].spots[0].description == "模型给出的景点说明。"
    assert itinerary.days[0].meals[0].name == "大理乐客特色小吃"
    assert itinerary.days[1].meals[0].name == "过桥米线"
    assert all("已过滤" not in note for note in itinerary.source_notes)


def test_fabricated_llm_names_fall_back_to_real_candidates(monkeypatch) -> None:
    """攻略里不存在的名称会被丢弃，改用真实候选。"""
    draft = PlannerDraft(
        summary="大理慢游",
        tips=["带薄外套"],
        days=[
            build_day(1, "苍山云海玻璃栈道", "洱海船说主题餐厅"),
            build_day(2, "大理古城-南门楼", "大理乐客特色小吃"),
        ],
    )
    patch_pipeline(monkeypatch, draft)

    itinerary = generate_trip_itinerary(build_trip_request())
    serialized = itinerary.model_dump_json()

    # 编造的名称不能出现在任何位置
    assert "苍山云海玻璃栈道" not in serialized
    assert "洱海船说主题餐厅" not in serialized
    # 第一天退回到攻略里真实存在的候选
    assert itinerary.days[0].spots[0].name == "大理古城-南门楼"
    assert itinerary.days[0].meals[0].name == "大理乐客特色小吃"
    # 第二天的合法名称不受影响
    assert itinerary.days[1].spots[0].name == "大理古城-南门楼"
    assert any("已过滤 2 个" in note for note in itinerary.source_notes)


def test_fabricated_names_become_empty_when_no_candidate_left(monkeypatch) -> None:
    """没有真实候选可退时留空并说明原因，而不是保留编造内容。"""
    draft = PlannerDraft(
        summary="大理慢游",
        tips=[],
        days=[
            build_day(1, "苍山云海玻璃栈道", "洱海船说主题餐厅"),
            build_day(2, "虚构的第二个景点", "虚构的第二家餐厅"),
        ],
    )
    patch_pipeline(monkeypatch, draft)

    itinerary = generate_trip_itinerary(build_trip_request())

    # 候选各只有一个，第二天没有可退的真实名称
    assert itinerary.days[1].spots == []
    assert itinerary.days[1].meals == []
    assert itinerary.days[1].transport == []
    assert any("未从当前攻略检索到景点信息" in note for note in itinerary.days[1].notes)
    assert any("未从当前攻略检索到餐饮信息" in note for note in itinerary.days[1].notes)


def test_empty_rag_context_rejects_all_llm_names(monkeypatch) -> None:
    """完全没有攻略上下文时无法核验任何名称，行程不填充具体条目。"""
    draft = PlannerDraft(
        summary="大理慢游",
        tips=[],
        days=[build_day(1, "大理古城", "某某餐厅"), build_day(2, "洱海", "某某小吃")],
    )
    patch_pipeline(monkeypatch, draft, contexts=[])

    itinerary = generate_trip_itinerary(build_trip_request())

    assert all(day.spots == [] for day in itinerary.days)
    assert all(day.meals == [] for day in itinerary.days)
    assert any("未检索到任何本地攻略上下文" in note for note in itinerary.source_notes)
