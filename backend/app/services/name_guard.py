"""校验 LLM 产出的景点 / 餐饮 / 住宿名称是否确实出自攻略上下文。

背景：`generate_planner_draft` 解析成功时，景点名与餐饮名直接取自模型输出。
prompt 里虽然写了「必须使用上下文中的真实商户名」，但 prompt 是软约束，
模型仍可能给出攻略里根本不存在的名字。本模块把这条约束落到代码层面：
凡是无法在攻略上下文中找到出处的名称一律丢弃，由调用方决定改用真实候选还是留空。

判定刻意做得宽松，优先避免误杀真实名称；只要能在上下文里找到出处就放行。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.fallback_candidates import extract_fallback_candidates


# 归一化时剔除的字符：空白、各类括号、常见标点与分隔符。
# 目的是让「大理古城 · 南门」与「大理古城·南门」「大理古城（南门）」判为同一个名字。
_NOISE_CHARS_PATTERN = re.compile(
    r"[\s　（）()【】\[\]{}「」『』《》〈〉·・、,，。.:：;；!！?？\-—–_/\\|*#\"'“”‘’]+"
)

# 归一化后短于该长度的名称不参与子串匹配，否则「面」「湖」这类单字几乎必然命中。
MIN_VERIFIABLE_LENGTH = 2

# 候选名被模型扩写时（「喜洲古镇」→「喜洲古镇白族民居」）用于反向匹配的最短长度。
MIN_CANDIDATE_SUBSTRING_LENGTH = 3

KIND_SPOTS = "spots"
KIND_MEALS = "meals"
KIND_HOTELS = "hotels"


def normalize_name(value: str | None) -> str:
    """去掉空白与标点并转小写，用于宽松比对。"""
    return _NOISE_CHARS_PATTERN.sub("", (value or "").strip()).lower()


@dataclass(frozen=True)
class GuardIndex:
    """一次行程生成内可复用的校验索引。

    haystack 是全部攻略上下文归一化后的拼接结果；三个候选集合来自
    `extract_fallback_candidates`，即正则能稳定抽出的「正式」名称。
    """

    haystack: str
    spots: frozenset[str]
    meals: frozenset[str]
    hotels: frozenset[str]

    @property
    def has_context(self) -> bool:
        return bool(self.haystack)

    def pool(self, kind: str) -> frozenset[str]:
        if kind == KIND_SPOTS:
            return self.spots
        if kind == KIND_MEALS:
            return self.meals
        if kind == KIND_HOTELS:
            return self.hotels
        raise ValueError(f"未知的校验类别: {kind}")


def build_guard_index(
    rag_contexts: list[str],
    candidates: dict[str, list[str]] | None = None,
) -> GuardIndex:
    """构建校验索引。

    candidates 可由调用方传入，避免与 `extract_fallback_candidates` 重复计算。
    """
    resolved = candidates if candidates is not None else extract_fallback_candidates(rag_contexts)

    def _normalized_set(key: str) -> frozenset[str]:
        return frozenset(
            normalized
            for normalized in (normalize_name(item) for item in resolved.get(key) or ())
            if normalized
        )

    return GuardIndex(
        haystack=normalize_name("\n".join(rag_contexts or ())),
        spots=_normalized_set(KIND_SPOTS),
        meals=_normalized_set(KIND_MEALS),
        hotels=_normalized_set(KIND_HOTELS),
    )


def verify_name(name: str | None, index: GuardIndex, *, kind: str) -> bool:
    """判断名称是否出自攻略上下文。

    依次尝试三种判定，任一命中即通过：

    1. 归一化后落在该类别的正式候选名单里；
    2. 归一化后作为子串出现在攻略正文中——覆盖候选正则漏抽、但正文确实写了的情况；
    3. 某个正式候选名是该名称的子串——覆盖模型在真实名称后追加修饰语的情况。

    没有任何攻略上下文时一律判为不通过：此时模型只能凭参数化知识作答，
    无法归因到任何来源，与「不伪造」的产品口径冲突。
    """
    normalized = normalize_name(name)
    if len(normalized) < MIN_VERIFIABLE_LENGTH:
        return False
    if not index.has_context:
        return False

    pool = index.pool(kind)
    if normalized in pool:
        return True
    if normalized in index.haystack:
        return True
    return any(
        len(candidate) >= MIN_CANDIDATE_SUBSTRING_LENGTH and candidate in normalized
        for candidate in pool
    )
