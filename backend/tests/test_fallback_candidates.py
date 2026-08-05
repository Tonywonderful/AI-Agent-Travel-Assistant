from app.services.fallback_candidates import (
    extract_fallback_candidates,
    extract_hotel_candidates,
)


def test_extracts_entities_from_new_chunk_titles() -> None:
    contexts = [
        "[来源: chengdu_guide.md | 标题: 餐饮：芳香景]\n"
        "- **人均预算**：500 元以上\n"
        "- **推荐菜品**：现代川菜\n"
        "- **相关描述**：需提前预约。",
        "[来源: chengdu_guide.md | 标题: 成都华尔道夫酒店]\n"
        "- **住宿档次**：豪华型（500 元/晚以上）\n"
        "- **参考价格**：500 元/晚以上\n"
        "- **所在区域**：金融城片区\n"
        "- **相关描述**：适合商务行程。",
    ]

    candidates = extract_fallback_candidates(contexts)

    assert candidates["meals"] == ["芳香景"]
    assert candidates["hotels"] == ["成都华尔道夫酒店"]

    hotel = extract_hotel_candidates(contexts)[0]
    assert hotel == {
        "name": "成都华尔道夫酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "500 元/晚以上",
        "location": "金融城片区",
        "source": "chengdu_guide.md",
    }


def test_does_not_mix_dishes_or_accommodation_advice_into_entity_pools() -> None:
    contexts = [
        "[来源: xiamen_guide.md | 标题: 菜品：沙茶面]\n基础小份约 15-25 元。",
        "[来源: beijing_guide.md | 标题: 住宿提示：汉庭酒店北京核心区门店]\n"
        "- **参考预算**：200-500 元/晚\n"
        "- **选择建议**：预订时核对具体门店。",
    ]

    candidates = extract_fallback_candidates(contexts)

    assert candidates["meals"] == []
    assert candidates["hotels"] == []
