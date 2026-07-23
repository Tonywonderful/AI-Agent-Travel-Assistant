from __future__ import annotations

import json
import logging
from typing import Any

from app.config import (
    REDIS_DEFAULT_TTL_SECONDS,
    REDIS_ENABLED,
    REDIS_KEY_PREFIX,
    REDIS_URL,
)

try:
    import redis
except ImportError:  # pragma: no cover - 依赖未安装时优雅降级
    redis = None


logger = logging.getLogger(__name__)
_redis_client: Any | None = None
_redis_unavailable_logged = False


def _build_key(key: str) -> str:
    """为缓存 key 添加统一前缀，避免不同项目之间冲突。"""
    return f"{REDIS_KEY_PREFIX}:{key}"


def _get_redis_client():
    """懒加载 Redis 客户端；不可用时返回 None。"""
    global _redis_client
    global _redis_unavailable_logged

    if not REDIS_ENABLED:
        return None
    if redis is None:
        if not _redis_unavailable_logged:
            logger.warning("Redis 已启用，但当前环境未安装 redis 依赖，缓存功能将被跳过。")
            _redis_unavailable_logged = True
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:  # pragma: no cover - 连接问题时优雅降级
        if not _redis_unavailable_logged:
            logger.warning("Redis 连接失败，缓存功能将被跳过：%s", exc)
            _redis_unavailable_logged = True
        return None


def get_cached_json(key: str) -> Any | None:
    """读取 JSON 缓存；命中失败或 Redis 不可用时返回 None。"""
    client = _get_redis_client()
    if client is None:
        return None

    try:
        raw_value = client.get(_build_key(key))
        if raw_value is None:
            return None
        return json.loads(raw_value)
    except Exception as exc:  # pragma: no cover - 缓存失败不影响主流程
        logger.debug("读取 Redis 缓存失败：%s", exc)
        return None


def set_cached_json(
    key: str,
    value: Any,
    expire_seconds: int | None = None,
) -> None:
    """写入 JSON 缓存；Redis 不可用时直接跳过。"""
    client = _get_redis_client()
    if client is None:
        return

    ttl = expire_seconds or REDIS_DEFAULT_TTL_SECONDS
    try:
        client.set(_build_key(key), json.dumps(value, ensure_ascii=False), ex=ttl)
    except Exception as exc:  # pragma: no cover - 缓存失败不影响主流程
        logger.debug("写入 Redis 缓存失败：%s", exc)


def delete_by_prefix(prefix: str) -> int:
    """
    删除匹配逻辑前缀的缓存 key（会自动加上 REDIS_KEY_PREFIX）。

    例：prefix="rag:guide:" → 删除 trip_planner:rag:guide:*
    Redis 不可用时返回 0。
    """
    client = _get_redis_client()
    if client is None:
        return 0

    pattern = _build_key(f"{prefix}*")
    deleted = 0
    try:
        for key in client.scan_iter(match=pattern, count=200):
            client.delete(key)
            deleted += 1
    except Exception as exc:  # pragma: no cover
        logger.debug("按前缀删除 Redis 缓存失败：%s", exc)
        return deleted
    return deleted


def invalidate_rag_caches() -> dict[str, int]:
    """知识库更新后失效检索相关缓存（RAG 结果 + rerank）。"""
    rag_deleted = delete_by_prefix("rag:guide:")
    rerank_deleted = delete_by_prefix("rerank:")
    total = rag_deleted + rerank_deleted
    if total:
        logger.info(
            "invalidate rag caches: rag=%d rerank=%d total=%d",
            rag_deleted,
            rerank_deleted,
            total,
        )
        print(
            f"[cache] invalidated rag={rag_deleted} rerank={rerank_deleted} total={total}"
        )
    return {
        "rag": rag_deleted,
        "rerank": rerank_deleted,
        "total": total,
    }

