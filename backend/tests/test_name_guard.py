"""name_guard 的单元测试：名称能否被判定为「出自攻略上下文」。"""

from pathlib import Path
import sys


# 允许测试文件直接导入 backend/app 下的模块。
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.name_guard import (  # noqa: E402
    KIND_HOTELS,
    KIND_MEALS,
    KIND_SPOTS,
    build_guard_index,
    normalize_name,
    verify_name,
)


CONTEXTS = [
    "[来源: dali_guide.md | 标题: 2.1 大理古城-南门楼]\n"
    "* **位置**：古城区大理古城一塔路42号\n"
    "* **简介**：适合拍照留念，傍晚人少。",
    "[来源: dali_guide.md | 标题: 经济实惠]\n"
    "* **【大理乐客特色小吃】招牌菜**：过桥米线。人均预算 **25元**。",
    "[来源: dali_guide.md | 标题: 经济型]\n"
    "* **【大理邻步客栈】**：交通便利。酒店预算：**180元/晚**。",
]


def test_normalize_name_strips_punctuation_and_spaces() -> None:
    """归一化会去掉空白与标点，使不同写法能对上。"""
    assert normalize_name(" 大理古城 · 南门 ") == normalize_name("大理古城（南门）")
    assert normalize_name(None) == ""


def test_verify_name_accepts_official_candidate() -> None:
    """命中 extract_fallback_candidates 抽出的正式候选名单。"""
    index = build_guard_index(CONTEXTS)

    assert verify_name("大理古城-南门楼", index, kind=KIND_SPOTS) is True
    assert verify_name("大理乐客特色小吃", index, kind=KIND_MEALS) is True
    assert verify_name("大理邻步客栈", index, kind=KIND_HOTELS) is True


def test_verify_name_rejects_non_entity_occurrence_in_context() -> None:
    """正文里的菜名不是餐厅实体，不能作为餐厅名称放行。"""
    index = build_guard_index(CONTEXTS)

    # 「过桥米线」只出现在正文里，不是任何一类的正式候选。
    assert verify_name("过桥米线", index, kind=KIND_MEALS) is False


def test_verify_name_rejects_cross_category_entity() -> None:
    index = build_guard_index(CONTEXTS)

    assert verify_name("大理邻步客栈", index, kind=KIND_SPOTS) is False
    assert verify_name("大理乐客特色小吃", index, kind=KIND_SPOTS) is False


def test_verify_name_accepts_candidate_with_extra_wording() -> None:
    """模型在真实名称后追加修饰语时不算编造。"""
    index = build_guard_index(CONTEXTS)

    assert verify_name("大理古城-南门楼 观景台", index, kind=KIND_SPOTS) is True


def test_verify_name_rejects_fabricated_name() -> None:
    """攻略里根本没有的名称必须被拒绝。"""
    index = build_guard_index(CONTEXTS)

    assert verify_name("苍山云海玻璃栈道", index, kind=KIND_SPOTS) is False
    assert verify_name("洱海船说主题餐厅", index, kind=KIND_MEALS) is False


def test_verify_name_rejects_too_short_name() -> None:
    """单字名称不参与子串匹配，否则几乎必然误判为命中。"""
    index = build_guard_index(CONTEXTS)

    assert verify_name("城", index, kind=KIND_SPOTS) is False
    assert verify_name("", index, kind=KIND_SPOTS) is False
    assert verify_name(None, index, kind=KIND_SPOTS) is False


def test_verify_name_rejects_everything_without_context() -> None:
    """没有任何攻略上下文时无法归因，一律不通过。"""
    index = build_guard_index([])

    assert index.has_context is False
    assert verify_name("大理古城", index, kind=KIND_SPOTS) is False


def test_build_guard_index_accepts_precomputed_candidates() -> None:
    """允许复用调用方已经算好的候选，避免重复抽取。"""
    index = build_guard_index(
        CONTEXTS,
        {"spots": ["自定义景点"], "meals": [], "hotels": []},
    )

    assert normalize_name("自定义景点") in index.spots
    assert index.meals == frozenset()
