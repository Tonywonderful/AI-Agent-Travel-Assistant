from collections import Counter

from app.rag.vector_db import DATA_DIR, _split_markdown_into_chunks


_GUIDE_FILES = (
    "beijing_guide.md",
    "chengdu_guide.md",
    "dali_guide.md",
    "sanya_guide.md",
    "xiamen_guide.md",
    "xian_guide.md",
)
_VALID_HOTEL_TIERS = {
    "经济型（200 元/晚以下）",
    "舒适型（200-500 元/晚）",
    "豪华型（500 元/晚以上）",
}


def test_restaurant_heading_creates_single_typed_chunk() -> None:
    markdown = """
## 3. 特色餐饮与预算参考

### 餐饮：南溪小馆

- **人均预算**：25-45 元
- **推荐菜品**：云岚米线、豆花
- **相关描述**：适合简餐。
"""

    chunks = _split_markdown_into_chunks(markdown, "sample.md")

    assert len(chunks) == 1
    assert chunks[0]["title"] == "餐饮：南溪小馆"
    assert chunks[0]["category"] == "restaurant"
    assert chunks[0]["entity_name"] == "南溪小馆"
    assert chunks[0]["budget_tier"] == ""


def test_hotel_heading_creates_single_typed_chunk_with_tier() -> None:
    markdown = """
## 4. 住宿区域建议

### 成都华尔道夫酒店

- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：500 元/晚以上
- **所在区域**：金融城片区
- **相关描述**：适合商务行程。
"""

    chunks = _split_markdown_into_chunks(markdown, "sample.md")

    assert len(chunks) == 1
    assert chunks[0]["title"] == "成都华尔道夫酒店"
    assert chunks[0]["category"] == "hotel"
    assert chunks[0]["entity_name"] == "成都华尔道夫酒店"
    assert chunks[0]["budget_tier"] == "豪华型（500 元/晚以上）"


def test_non_entity_dining_and_accommodation_headings_stay_isolated() -> None:
    markdown = """
## 3. 特色餐饮与预算参考

### 菜品：沙茶面

基础小份约 15-25 元。

### 餐饮街区：八市

海鲜和本地小吃集中。

### 餐饮提示：海鲜点餐计价

点单前确认计价单位。

## 4. 住宿区域建议

### 住宿提示：品牌门店集合

- **参考预算**：200-500 元/晚
- **选择建议**：预订时核对具体门店。
"""

    chunks = _split_markdown_into_chunks(markdown, "sample.md")

    assert [chunk["category"] for chunk in chunks] == [
        "dish",
        "food_district",
        "dining_advice",
        "accommodation_advice",
    ]
    assert all(chunk["entity_name"] == "" for chunk in chunks[1:])


def test_attraction_heading_gets_a_dedicated_category() -> None:
    markdown = """
## 2. 核心景点详解

### 2.1 示例景点

- **位置**：示例区域
- **简介**：示例说明。
"""

    chunks = _split_markdown_into_chunks(markdown, "sample.md")

    assert len(chunks) == 1
    assert chunks[0]["title"] == "2.1 示例景点"
    assert chunks[0]["category"] == "attraction"
    assert chunks[0]["entity_name"] == "示例景点"


def test_all_six_guides_follow_entity_chunk_contract() -> None:
    expected_fields = {
        "restaurant": {"人均预算", "推荐菜品", "相关描述"},
        "hotel": {"住宿档次", "参考价格", "所在区域", "相关描述"},
    }

    for source_name in _GUIDE_FILES:
        markdown = (DATA_DIR / source_name).read_text(encoding="utf-8")
        chunks = _split_markdown_into_chunks(markdown, source_name)
        entity_chunks = [
            chunk for chunk in chunks if chunk["category"] in expected_fields
        ]
        assert entity_chunks, source_name

        titles = [chunk["title"] for chunk in entity_chunks]
        assert not [
            title for title, count in Counter(titles).items() if count > 1
        ], source_name

        for chunk in entity_chunks:
            fields = {
                line.split("**：", 1)[0].removeprefix("- **")
                for line in chunk["text"].splitlines()
                if line.startswith("- **") and "**：" in line
            }
            assert fields == expected_fields[chunk["category"]], (
                source_name,
                chunk["title"],
                fields,
            )
            assert chunk["entity_name"], (source_name, chunk["title"])
            if chunk["category"] == "hotel":
                assert chunk["budget_tier"] in _VALID_HOTEL_TIERS, (
                    source_name,
                    chunk["title"],
                    chunk["budget_tier"],
                )


def test_old_budget_tier_headings_are_not_used_as_chunks() -> None:
    for source_name in _GUIDE_FILES:
        markdown = (DATA_DIR / source_name).read_text(encoding="utf-8")
        chunks = _split_markdown_into_chunks(markdown, source_name)
        assert not _VALID_HOTEL_TIERS.intersection(
            chunk["title"] for chunk in chunks
        ), source_name
