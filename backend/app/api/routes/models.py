"""大模型目录接口：只暴露模型元数据，不暴露密钥或网关配置。"""

from fastapi import APIRouter

from app.config import LLM_MODEL, LLM_PROVIDER
from app.llm import list_zen_free_models


router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models() -> dict:
    """返回当前模型与已接入的 OpenCode Zen 免费模型。"""
    return {
        "current": {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
        },
        "models": list_zen_free_models(),
    }
