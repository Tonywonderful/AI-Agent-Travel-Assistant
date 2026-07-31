import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


# 数据库配置
DB_DIR = BACKEND_DIR / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = DB_DIR / "app.db"
DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 大模型配置
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compatible").strip().lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "public")
OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")


# RAG / 向量库配置
_chroma_db_dir_raw = Path(os.getenv("CHROMA_DB_DIR", "db/chroma_db"))
CHROMA_DB_DIR = (
    _chroma_db_dir_raw
    if _chroma_db_dir_raw.is_absolute()
    else BACKEND_DIR / _chroma_db_dir_raw
)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "travel_guides")
# embedding: openai_compatible（云端）或 ollama（本地）
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai_compatible").strip().lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
# 本地 Ollama embedding；仅 EMBEDDING_PROVIDER=ollama 时使用
OLLAMA_EMBED_URL = os.getenv(
    "OLLAMA_EMBED_URL",
    "http://127.0.0.1:11434/api/embeddings",
).rstrip("/")
# 可选：embedding 单独走不同网关；普通兼容 Provider 未配置时回退到 LLM 配置。
# Zen 免费接口只提供 Chat Completion，不能把 public 凭据误用于 Embedding / Rerank。
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "") or (
    LLM_API_KEY if LLM_PROVIDER != "opencode_zen" else ""
)
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "") or (
    LLM_BASE_URL if LLM_PROVIDER != "opencode_zen" else ""
)
RERANK_API_URL = os.getenv(
    "RERANK_API_URL",
    "https://openrouter.ai/api/v1/rerank",
).strip()
RERANK_MODEL = os.getenv(
    "RERANK_MODEL",
    "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
).strip()
RERANK_API_KEY = os.getenv("RERANK_API_KEY", "").strip()
RERANK_HTTP_REFERER = os.getenv("RERANK_HTTP_REFERER", "").strip()
RERANK_APP_TITLE = os.getenv("RERANK_APP_TITLE", "").strip()
RERANK_TIMEOUT_SECONDS = float(os.getenv("RERANK_TIMEOUT_SECONDS", "30"))
# 最终返回的攻略片段数；向量召回候选数为 max(RAG_TOP_K * 2, 6)
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))


# Redis / 缓存配置
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "trip_planner")
REDIS_DEFAULT_TTL_SECONDS = int(os.getenv("REDIS_DEFAULT_TTL_SECONDS", "1800"))
REDIS_WEATHER_TTL_SECONDS = int(os.getenv("REDIS_WEATHER_TTL_SECONDS", "1800"))
REDIS_MAP_TTL_SECONDS = int(os.getenv("REDIS_MAP_TTL_SECONDS", "86400"))
REDIS_RAG_TTL_SECONDS = int(os.getenv("REDIS_RAG_TTL_SECONDS", "21600"))
REDIS_RERANK_TTL_SECONDS = int(os.getenv("REDIS_RERANK_TTL_SECONDS", "21600"))


# 高德地图配置
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
AMAP_BASE_URL = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com/v3")
AMAP_DEFAULT_CITY = os.getenv("AMAP_DEFAULT_CITY", "")
AMAP_TIMEOUT_SECONDS = int(os.getenv("AMAP_TIMEOUT_SECONDS", "20"))
ENABLE_AMAP_ENRICHMENT = os.getenv("ENABLE_AMAP_ENRICHMENT", "false").lower() == "true"


# 联网搜索（Exa MCP，与 OpenCode websearch 同源；默认可不配 key）
EXA_MCP_URL = os.getenv("EXA_MCP_URL", "https://mcp.exa.ai/mcp").strip()
EXA_API_KEY = os.getenv("EXA_API_KEY", "").strip()
EXA_SEARCH_TIMEOUT_SECONDS = int(os.getenv("EXA_SEARCH_TIMEOUT_SECONDS", "25"))
WEB_SEARCH_DEFAULT_NUM_RESULTS = int(os.getenv("WEB_SEARCH_DEFAULT_NUM_RESULTS", "5"))
WEB_SEARCH_CONTEXT_MAX_CHARS = int(os.getenv("WEB_SEARCH_CONTEXT_MAX_CHARS", "8000"))
