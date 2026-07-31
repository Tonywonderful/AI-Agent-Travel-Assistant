"""测试环境隔离：避免本机 .env 触发真实模型、地图或缓存调用。"""

from __future__ import annotations

import os


os.environ["LLM_PROVIDER"] = "openai_compatible"
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_MODEL"] = "test-model"
os.environ["LLM_BASE_URL"] = ""
os.environ["EMBEDDING_PROVIDER"] = "ollama"
os.environ["RERANK_API_KEY"] = ""
os.environ["REDIS_ENABLED"] = "false"
os.environ["ENABLE_AMAP_ENRICHMENT"] = "false"
