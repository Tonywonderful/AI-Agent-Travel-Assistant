from __future__ import annotations

import re
from typing import TypedDict


_RAG_CONTEXT_TITLE_PATTERN = re.compile(
    r"^\[来源:\s*(?P<source>.+?)\s*\|\s*标题:\s*(?P<title>.+?)\]$"
)
_MARKDOWN_HEADING_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)*\s+")
_RESTAURANT_TITLE_PREFIX = "餐饮："
_HOTEL_REQUIRED_FIELDS = ("**住宿档次**", "**参考价格**", "**所在区域**", "**相关描述**")
_LEGACY_MEAL_NAME_PATTERN = re.compile(r"【(?P<name>[^】]+)】招牌菜")
_LEGACY_HOTEL_NAME_PATTERN = re.compile(r"【(?P<name>[^】]+)】[^\n]*酒店预算")
_FIELD_PATTERN_TEMPLATE = r"^- \*\*{label}\*\*：(?P<value>.+)$"


class HotelCandidate(TypedDict):
    name: str
    level: str
    reference_price: str
    location: str
    source: str


class RestaurantCandidate(TypedDict):
    name: str
    per_person_budget: str
    recommended_dishes: str
    source: str


def _append_unique(candidates: list[str], value: str | None) -> None:
    normalized = (value or "").strip()
    if normalized and normalized not in candidates:
        candidates.append(normalized)


def _extract_spot_names(rag_contexts: list[str]) -> list[str]:
    candidates: list[str] = []
    for context in rag_contexts:
        header, separator, body = context.partition("\n")
        if not separator or "**位置**" not in body:
            continue

        match = _RAG_CONTEXT_TITLE_PATTERN.match(header.strip())
        if match is None:
            continue
        _append_unique(
            candidates,
            _MARKDOWN_HEADING_NUMBER_PATTERN.sub("", match.group("title")).strip(),
        )
    return candidates


def _field_value(body: str, label: str) -> str:
    pattern = re.compile(
        _FIELD_PATTERN_TEMPLATE.format(label=re.escape(label)),
        re.MULTILINE,
    )
    match = pattern.search(body)
    return match.group("value").strip() if match else ""


def extract_restaurant_candidates(rag_contexts: list[str]) -> list[RestaurantCandidate]:
    candidates: list[RestaurantCandidate] = []
    seen: set[str] = set()
    for context in rag_contexts:
        header, separator, body = context.partition("\n")
        if not separator:
            continue
        match = _RAG_CONTEXT_TITLE_PATTERN.match(header.strip())
        if match is None:
            continue
        title = match.group("title").strip()
        if title.startswith(_RESTAURANT_TITLE_PREFIX):
            name = title.removeprefix(_RESTAURANT_TITLE_PREFIX).strip()
            if name and name not in seen:
                seen.add(name)
                candidates.append(
                    {
                        "name": name,
                        "per_person_budget": _field_value(body, "人均预算"),
                        "recommended_dishes": _field_value(body, "推荐菜品"),
                        "source": match.group("source").strip(),
                    }
                )
            continue
        for legacy_match in _LEGACY_MEAL_NAME_PATTERN.finditer(body):
            name = legacy_match.group("name").strip()
            if name and name not in seen:
                seen.add(name)
                candidates.append(
                    {
                        "name": name,
                        "per_person_budget": "",
                        "recommended_dishes": "",
                        "source": match.group("source").strip(),
                    }
                )
    return candidates


def extract_hotel_candidates(rag_contexts: list[str]) -> list[HotelCandidate]:
    candidates: list[HotelCandidate] = []
    seen: set[str] = set()
    for context in rag_contexts:
        header, separator, body = context.partition("\n")
        if not separator:
            continue
        match = _RAG_CONTEXT_TITLE_PATTERN.match(header.strip())
        if match is None:
            continue
        if all(field in body for field in _HOTEL_REQUIRED_FIELDS):
            name = match.group("title").strip()
            if name and name not in seen:
                seen.add(name)
                candidates.append(
                    {
                        "name": name,
                        "level": _field_value(body, "住宿档次"),
                        "reference_price": _field_value(body, "参考价格"),
                        "location": _field_value(body, "所在区域"),
                        "source": match.group("source").strip(),
                    }
                )
            continue
        for legacy_match in _LEGACY_HOTEL_NAME_PATTERN.finditer(body):
            name = legacy_match.group("name").strip()
            if name and name not in seen:
                seen.add(name)
                candidates.append(
                    {
                        "name": name,
                        "level": "",
                        "reference_price": "",
                        "location": "",
                        "source": match.group("source").strip(),
                    }
                )
    return candidates


def extract_fallback_candidates(rag_contexts: list[str]) -> dict[str, list[str]]:
    """按行程 fallback 的正式规则提取真实景点、餐饮和住宿候选。"""
    return {
        "spots": _extract_spot_names(rag_contexts),
        "meals": [item["name"] for item in extract_restaurant_candidates(rag_contexts)],
        "hotels": [item["name"] for item in extract_hotel_candidates(rag_contexts)],
    }
