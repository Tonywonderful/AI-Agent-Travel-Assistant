from __future__ import annotations

import re
from hashlib import md5
from pathlib import Path

import httpx

from app.config import (
    BACKEND_DIR,
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_DIR,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    OLLAMA_EMBED_URL,
    RAG_TOP_K,
)
from app.rag.document_registry import (
    compute_content_hash,
    upsert_document,
)
from app.rag.guide_catalog import destination_for_guide


DATA_DIR = BACKEND_DIR / "data"


_DINING_SECTION_KEYWORD = "特色餐饮与预算参考"
_ACCOMMODATION_SECTION_KEYWORD = "住宿区域建议"
_ATTRACTION_SECTION_KEYWORD = "核心景点"
_RESTAURANT_TITLE_PREFIX = "餐饮："
_DISH_TITLE_PREFIX = "菜品："
_FOOD_DISTRICT_TITLE_PREFIX = "餐饮街区："
_DINING_ADVICE_TITLE_PREFIX = "餐饮提示："
_ACCOMMODATION_ADVICE_TITLE_PREFIX = "住宿提示："
_HOTEL_TIER_PATTERN = re.compile(r"^- \*\*住宿档次\*\*：(?P<tier>.+)$", re.MULTILINE)
_MARKDOWN_HEADING_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)*\s+")

RETRIEVAL_SCOPE_PLANNING = "planning"
RETRIEVAL_SCOPE_ASSISTANT_ONLY = "assistant_only"
_VALID_RETRIEVAL_SCOPES = {
    RETRIEVAL_SCOPE_PLANNING,
    RETRIEVAL_SCOPE_ASSISTANT_ONLY,
}
_ASSISTANT_ONLY_TITLE_MARKERS = {
    "交通距离与行程组织",
    "专项通用安全说明",
    "通用安全说明",
}


def _classify_retrieval_scope(section: str, title: str) -> str:
    """标记仅供问答使用的辅助知识，其余 Chunk 可参与规划。"""
    if title == "文档开头":
        return RETRIEVAL_SCOPE_ASSISTANT_ONLY
    if "目的地简介" in section or "目的地简介" in title:
        return RETRIEVAL_SCOPE_ASSISTANT_ONLY
    if re.match(r"^5[.．、\s]", section):
        return RETRIEVAL_SCOPE_ASSISTANT_ONLY
    if any(marker in section or marker in title for marker in _ASSISTANT_ONLY_TITLE_MARKERS):
        return RETRIEVAL_SCOPE_ASSISTANT_ONLY
    return RETRIEVAL_SCOPE_PLANNING


def _validate_retrieval_scope(retrieval_scope: str | None) -> None:
    if retrieval_scope is not None and retrieval_scope not in _VALID_RETRIEVAL_SCOPES:
        raise ValueError(f"未知 retrieval_scope：{retrieval_scope}")


def _build_chroma_where(
    destination: str | None,
    retrieval_scope: str | None,
    categories: list[str] | None = None,
    budget_tier: str | None = None,
) -> dict[str, object] | None:
    """构造兼容 Chroma 的用途、目的地和实体类型联合过滤条件。"""
    _validate_retrieval_scope(retrieval_scope)
    filters: list[dict[str, object]] = []
    if destination:
        filters.append({"destination": destination})
    if retrieval_scope:
        filters.append({"retrieval_scope": retrieval_scope})
    normalized_categories = list(dict.fromkeys(categories or []))
    if len(normalized_categories) == 1:
        filters.append({"category": normalized_categories[0]})
    elif normalized_categories:
        filters.append({"category": {"$in": normalized_categories}})
    if budget_tier:
        filters.append({"budget_tier": budget_tier})
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def _classify_heading(section: str, title: str, text: str) -> tuple[str, str, str]:
    """按新知识库标题规范识别类别、实体名和酒店档次。"""
    if _DINING_SECTION_KEYWORD in section:
        if title.startswith(_RESTAURANT_TITLE_PREFIX):
            return "restaurant", title.removeprefix(_RESTAURANT_TITLE_PREFIX).strip(), ""
        if title.startswith(_DISH_TITLE_PREFIX):
            return "dish", title.removeprefix(_DISH_TITLE_PREFIX).strip(), ""
        if title.startswith(_FOOD_DISTRICT_TITLE_PREFIX):
            return "food_district", "", ""
        if title.startswith(_DINING_ADVICE_TITLE_PREFIX):
            return "dining_advice", "", ""
        return "dining_knowledge", "", ""

    if _ACCOMMODATION_SECTION_KEYWORD in section:
        if title == section or title.startswith(_ACCOMMODATION_ADVICE_TITLE_PREFIX):
            return "accommodation_advice", "", ""
        tier_match = _HOTEL_TIER_PATTERN.search(text)
        budget_tier = tier_match.group("tier").strip() if tier_match else ""
        return "hotel", title, budget_tier

    if _ATTRACTION_SECTION_KEYWORD in section and title != section:
        entity_name = _MARKDOWN_HEADING_NUMBER_PATTERN.sub("", title).strip()
        return "attraction", entity_name, ""

    return "guide", "", ""


def _split_markdown_into_chunks(markdown_text: str, source_name: str) -> list[dict[str, str]]:
    """按二级、三级标题切分 Markdown；每个餐厅和酒店三级标题即独立 Chunk。"""
    chunks: list[dict[str, str]] = []
    current_title = "文档开头"
    current_section = ""
    current_lines: list[str] = []

    def flush_current_chunk() -> None:
        nonlocal current_lines
        text = "\n".join(current_lines).strip()
        if not text:
            current_lines = []
            return

        category, entity_name, budget_tier = _classify_heading(
            current_section, current_title, text
        )
        chunks.append(
            {
                "title": current_title,
                "text": text,
                "source": source_name,
                "category": category,
                "entity_name": entity_name,
                "section": current_section,
                "subsection": current_title if current_title != current_section else "",
                "budget_tier": budget_tier,
                "retrieval_scope": _classify_retrieval_scope(
                    current_section, current_title
                ),
            }
        )
        current_lines = []

    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            flush_current_chunk()
            current_section = stripped.removeprefix("## ").strip()
            current_title = current_section
            continue
        if stripped.startswith("### "):
            flush_current_chunk()
            current_title = stripped.removeprefix("### ").strip()
            continue
        if stripped:
            current_lines.append(stripped)

    flush_current_chunk()
    return chunks


def _build_chunk_id(source: str, title: str, text: str) -> str:
    """基于 source、title 和 text 生成稳定片段 ID。"""
    digest = md5(f"{source}|{title}|{text}".encode("utf-8")).hexdigest()
    return f"{source}_{digest}"


def _build_document_text(chunk: dict[str, str]) -> str:
    """把标题和正文拼成送入向量库的文档文本。"""
    return f"{chunk['title']}\n{chunk['text']}"


def load_guide_chunks() -> list[dict[str, str]]:
    """读取 backend/data 下的攻略文件，并切分成可检索片段。

    每个 chunk 携带：
    - document_id: 正式文档编号（= 文件名）
    - source: 兼容旧字段，与 document_id 相同
    - content_hash: 所属文档的全文指纹（同一文档下各 chunk 相同）
    """
    chunks: list[dict[str, str]] = []
    for guide_file in sorted(DATA_DIR.glob("*.md*")):
        document_id = guide_file.name
        destination = destination_for_guide(document_id)
        if destination is None:
            raise ValueError(
                f"攻略文件缺少 destination 映射：{document_id}。"
                "请先在 app/rag/guide_catalog.py 中登记该文件。"
            )
        text = guide_file.read_text(encoding="utf-8")
        content_hash = compute_content_hash(text)
        raw_chunks = _split_markdown_into_chunks(text, document_id)
        for chunk in raw_chunks:
            chunks.append(
                {
                    "id": _build_chunk_id(document_id, chunk["title"], chunk["text"]),
                    "title": chunk["title"],
                    "text": chunk["text"],
                    "source": document_id,
                    "document_id": document_id,
                    "content_hash": content_hash,
                    "destination": destination,
                    "category": chunk.get("category", "guide"),
                    "entity_name": chunk.get("entity_name", ""),
                    "section": chunk.get("section", ""),
                    "subsection": chunk.get("subsection", ""),
                    "budget_tier": chunk.get("budget_tier", ""),
                    "retrieval_scope": chunk.get(
                        "retrieval_scope", RETRIEVAL_SCOPE_PLANNING
                    ),
                }
            )
    return chunks


def load_guide_documents() -> list[dict[str, object]]:
    """按文档粒度读取 data 目录：document_id + content_hash + chunks。"""
    documents: list[dict[str, object]] = []
    for guide_file in sorted(DATA_DIR.glob("*.md*")):
        document_id = guide_file.name
        destination = destination_for_guide(document_id)
        if destination is None:
            raise ValueError(
                f"攻略文件缺少 destination 映射：{document_id}。"
                "请先在 app/rag/guide_catalog.py 中登记该文件。"
            )
        text = guide_file.read_text(encoding="utf-8")
        content_hash = compute_content_hash(text)
        raw_chunks = _split_markdown_into_chunks(text, document_id)
        chunks: list[dict[str, str]] = []
        for chunk in raw_chunks:
            chunks.append(
                {
                    "id": _build_chunk_id(document_id, chunk["title"], chunk["text"]),
                    "title": chunk["title"],
                    "text": chunk["text"],
                    "source": document_id,
                    "document_id": document_id,
                    "content_hash": content_hash,
                    "destination": destination,
                    "category": chunk.get("category", "guide"),
                    "entity_name": chunk.get("entity_name", ""),
                    "section": chunk.get("section", ""),
                    "subsection": chunk.get("subsection", ""),
                    "budget_tier": chunk.get("budget_tier", ""),
                    "retrieval_scope": chunk.get(
                        "retrieval_scope", RETRIEVAL_SCOPE_PLANNING
                    ),
                }
            )
        documents.append(
            {
                "document_id": document_id,
                "source_path": str(guide_file.relative_to(BACKEND_DIR)).replace("\\", "/"),
                "content_hash": content_hash,
                "last_modified": guide_file.stat().st_mtime,
                "destination": destination,
                "chunks": chunks,
            }
        )
    return documents


def _extract_keywords(query: str) -> list[str]:
    """把查询语句切成简单关键词，用于回退匹配。"""
    raw_keywords = re.split(r"[\s,，。；;、]+", query)
    return [keyword.strip() for keyword in raw_keywords if keyword.strip()]


def _score_chunk(query: str, chunk_text: str) -> int:
    """按关键词出现次数给片段打分。"""
    keywords = _extract_keywords(query)
    return sum(1 for keyword in keywords if keyword in chunk_text)


def _search_guide_chunks_by_keywords(
    query: str,
    top_k: int = RAG_TOP_K,
    destination: str | None = None,
    retrieval_scope: str | None = None,
    categories: list[str] | None = None,
    budget_tier: str | None = None,
) -> list[dict[str, str]]:
    """回退方案：使用关键词匹配本地攻略片段。"""
    _validate_retrieval_scope(retrieval_scope)
    scored_chunks: list[tuple[int, dict[str, str]]] = []
    for chunk in load_guide_chunks():
        if destination and chunk.get("destination") != destination:
            continue
        if retrieval_scope and chunk.get("retrieval_scope") != retrieval_scope:
            continue
        if categories and chunk.get("category") not in categories:
            continue
        if budget_tier and chunk.get("budget_tier") != budget_tier:
            continue
        score = _score_chunk(query, _build_document_text(chunk))
        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored_chunks[:top_k]]


class OllamaEmbeddings:
    """本地 Ollama embedding 适配器，接口对齐 LangChain 的 embed_* 方法。"""

    def __init__(
        self,
        model: str,
        url: str = OLLAMA_EMBED_URL,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _embed_one(self, text: str) -> list[float]:
        # trust_env=False：避免系统代理劫持 127.0.0.1
        with httpx.Client(timeout=self.timeout, trust_env=False) as client:
            response = client.post(
                self.url,
                json={"model": self.model, "prompt": text},
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama embedding 失败: {response.status_code} {response.text[:300]}"
            )
        embedding = response.json().get("embedding")
        if not embedding:
            raise RuntimeError("Ollama 未返回 embedding")
        return embedding

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]


def _build_embeddings():
    if EMBEDDING_PROVIDER == "ollama":
        print(
            f"[embedding] provider=ollama model={EMBEDDING_MODEL} url={OLLAMA_EMBED_URL}"
        )
        return OllamaEmbeddings(model=EMBEDDING_MODEL, url=OLLAMA_EMBED_URL)

    if not EMBEDDING_API_KEY:
        return None

    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError:
        return None

    try:
        return OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=EMBEDDING_API_KEY,
            base_url=EMBEDDING_BASE_URL or None,
            chunk_size=EMBEDDING_BATCH_SIZE,
            check_embedding_ctx_length=False,
        )
    except TypeError:
        return OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=EMBEDDING_API_KEY,
            openai_api_base=EMBEDDING_BASE_URL or None,
            chunk_size=EMBEDDING_BATCH_SIZE,
            check_embedding_ctx_length=False,
        )


def _extract_embedding_token_usage(response_data: dict) -> dict[str, int]:
    """读取 embeddings 接口返回的官方 usage；没有 usage 时保持 0。"""
    usage = response_data.get("usage") or {}
    prompt_tokens = (
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("input_token_count")
        or usage.get("total_tokens")
        or usage.get("total_token_count")
        or 0
    )
    return {
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": 0,
    }


def _embed_query_with_usage(query: str) -> tuple[list[float] | None, dict[str, int]]:
    """query embedding：本地 Ollama 或云端 OpenAI-compatible。"""
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    if EMBEDDING_PROVIDER == "ollama":
        try:
            embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, url=OLLAMA_EMBED_URL)
            vector = embeddings.embed_query(query)
            print(
                f"[embedding] provider=ollama model={EMBEDDING_MODEL} dim={len(vector)}"
            )
            return vector, empty_usage
        except Exception as exc:
            print(f"[embedding] ollama failed: {type(exc).__name__}: {exc}")
            return None, empty_usage

    if not EMBEDDING_API_KEY:
        return None, empty_usage

    base_url = (EMBEDDING_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    endpoint = f"{base_url}/embeddings"
    payload = {
        "model": EMBEDDING_MODEL,
        "input": query,
    }
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(endpoint, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            items = data.get("data") or []
            if items and "embedding" in items[0]:
                usage = _extract_embedding_token_usage(data)
                print(
                    "[embedding] query embedding token: "
                    f"prompt={usage['prompt_tokens']}, completion=0, source=api"
                )
                return items[0]["embedding"], usage
            print(f"[embedding] embeddings response missing vector: {response.text[:500]}")
        else:
            print(
                "[embedding] embeddings API failed: "
                f"status_code={response.status_code}, response={response.text[:500]}"
            )
    except Exception as exc:
        print(f"[embedding] embeddings API failed: {type(exc).__name__}: {exc}")

    embeddings = _build_embeddings()
    if embeddings is None:
        return None, empty_usage
    print("[embedding] fallback to LangChain embed_query; official token usage unavailable")
    return embeddings.embed_query(query), empty_usage


def _get_chroma_collection():
    try:
        import chromadb
    except ImportError:
        return None

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def delete_chunks_by_document_id(document_id: str) -> int:
    """按 document_id 删除向量库中该文档的全部 chunk，返回删除的数量。"""
    collection = _get_chroma_collection()
    if collection is None:
        raise RuntimeError("当前环境缺少 chromadb，无法删除 chunk。")

    # 兼容旧数据：早期只写了 source，没有 document_id
    id_set: set[str] = set()
    for where in (
        {"document_id": document_id},
        {"source": document_id},
    ):
        try:
            existing = collection.get(where=where)
        except Exception:
            existing = {"ids": []}
        for chunk_id in existing.get("ids") or []:
            id_set.add(chunk_id)

    if not id_set:
        return 0
    ids = list(id_set)
    collection.delete(ids=ids)
    return len(ids)


def load_guide_document(document_id: str) -> dict[str, object] | None:
    """读取并切分单篇文档；文件不存在返回 None。"""
    guide_file = DATA_DIR / document_id
    if not guide_file.is_file():
        return None

    destination = destination_for_guide(document_id)
    if destination is None:
        raise ValueError(
            f"攻略文件缺少 destination 映射：{document_id}。"
            "请先在 app/rag/guide_catalog.py 中登记该文件。"
        )

    text = guide_file.read_text(encoding="utf-8")
    content_hash = compute_content_hash(text)
    raw_chunks = _split_markdown_into_chunks(text, document_id)
    chunks: list[dict[str, str]] = []
    for chunk in raw_chunks:
        chunks.append(
            {
                "id": _build_chunk_id(document_id, chunk["title"], chunk["text"]),
                "title": chunk["title"],
                "text": chunk["text"],
                "source": document_id,
                "document_id": document_id,
                "content_hash": content_hash,
                "destination": destination,
                "category": chunk.get("category", "guide"),
                "entity_name": chunk.get("entity_name", ""),
                "section": chunk.get("section", ""),
                "subsection": chunk.get("subsection", ""),
                "budget_tier": chunk.get("budget_tier", ""),
                "retrieval_scope": chunk.get(
                    "retrieval_scope", RETRIEVAL_SCOPE_PLANNING
                ),
            }
        )
    return {
        "document_id": document_id,
        "source_path": str(guide_file.relative_to(BACKEND_DIR)).replace("\\", "/"),
        "content_hash": content_hash,
        "last_modified": guide_file.stat().st_mtime,
        "destination": destination,
        "chunks": chunks,
    }


def _upsert_chunks_to_collection(collection, embeddings, chunks: list[dict[str, str]]) -> int:
    """把一组 chunk 向量化后写入 Chroma。"""
    if not chunks:
        return 0
    documents = [_build_document_text(chunk) for chunk in chunks]
    vectors = embeddings.embed_documents(documents)
    ids = [chunk["id"] for chunk in chunks]
    metadatas = [
        {
            "title": chunk["title"],
            "source": chunk["source"],
            "document_id": chunk["document_id"],
            "content_hash": chunk["content_hash"],
            "destination": chunk["destination"],
            "category": chunk.get("category", "guide"),
            "entity_name": chunk.get("entity_name", ""),
            "section": chunk.get("section", ""),
            "subsection": chunk.get("subsection", ""),
            "budget_tier": chunk.get("budget_tier", ""),
            "retrieval_scope": chunk.get(
                "retrieval_scope", RETRIEVAL_SCOPE_PLANNING
            ),
        }
        for chunk in chunks
    ]
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=vectors,
    )
    return len(chunks)


def ingest_single_document_to_chroma(document_id: str) -> int:
    """
    单篇文档入库（新增用）：切割 → embedding → 写入 → 更新清单。
    不删除旧 chunk；修改场景请先调用 delete_chunks_by_document_id。
    """
    guide_document = load_guide_document(document_id)
    if guide_document is None:
        raise FileNotFoundError(f"文档不存在，无法入库：{document_id}")

    embeddings = _build_embeddings()
    collection = _get_chroma_collection()
    if embeddings is None:
        raise RuntimeError("当前环境缺少 embedding 能力，无法写入 Chroma。")
    if collection is None:
        raise RuntimeError("当前环境缺少 chromadb，无法写入 Chroma。")

    chunks: list[dict[str, str]] = list(guide_document["chunks"])  # type: ignore[arg-type]
    written = _upsert_chunks_to_collection(collection, embeddings, chunks)
    upsert_document(
        document_id=str(guide_document["document_id"]),
        source_path=str(guide_document["source_path"]),
        content_hash=str(guide_document["content_hash"]),
        last_modified=float(guide_document["last_modified"]),
        chunk_count=written,
        destination=str(guide_document["destination"]),
        status="active",
    )
    return written


def replace_document_in_chroma(document_id: str) -> int:
    """修改用：先按 document_id 删光旧 chunk，再整篇重切入库。"""
    deleted = delete_chunks_by_document_id(document_id)
    written = ingest_single_document_to_chroma(document_id)
    print(
        f"[kb] replace document_id={document_id}: deleted_chunks={deleted}, written_chunks={written}"
    )
    return written


def remove_document_from_chroma(document_id: str) -> int:
    """删除用：清掉该文档全部 chunk，并移除清单记录。"""
    from app.rag.document_registry import remove_document

    deleted = delete_chunks_by_document_id(document_id)
    remove_document(document_id)
    print(f"[kb] remove document_id={document_id}: deleted_chunks={deleted}")
    return deleted


def ingest_guide_chunks_to_chroma() -> int:
    """
    把本地攻略片段写入 Chroma，并同步维护文档清单。

    流程是：
    1. 创建 embedding 模型
    2. 获取 Chroma collection
    3. 按文档读取并切分本地攻略（带 document_id / content_hash）
    4. 生成向量
    5. 把向量、文本和 metadata 一起写入 Chroma
    6. 把 document_id + content_hash 写入 SQLite 文档清单
    """
    embeddings = _build_embeddings()
    collection = _get_chroma_collection()
    guide_documents = load_guide_documents()

    if embeddings is None:
        raise RuntimeError("当前环境缺少 embedding 能力，无法写入 Chroma。")
    if collection is None:
        raise RuntimeError("当前环境缺少 chromadb，无法写入 Chroma。")

    chunks: list[dict[str, str]] = []
    for guide_document in guide_documents:
        chunks.extend(guide_document["chunks"])  # type: ignore[arg-type]

    documents = [_build_document_text(chunk) for chunk in chunks]
    vectors = embeddings.embed_documents(documents)
    ids = [chunk["id"] for chunk in chunks]
    metadatas = [
        {
            "title": chunk["title"],
            "source": chunk["source"],
            "document_id": chunk["document_id"],
            "content_hash": chunk["content_hash"],
            "destination": chunk["destination"],
            "category": chunk.get("category", "guide"),
            "entity_name": chunk.get("entity_name", ""),
            "section": chunk.get("section", ""),
            "subsection": chunk.get("subsection", ""),
            "budget_tier": chunk.get("budget_tier", ""),
            "retrieval_scope": chunk.get(
                "retrieval_scope", RETRIEVAL_SCOPE_PLANNING
            ),
        }
        for chunk in chunks
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=vectors,
    )

    # 同步文档清单：document_id + content_hash + chunk 数量
    for guide_document in guide_documents:
        upsert_document(
            document_id=str(guide_document["document_id"]),
            source_path=str(guide_document["source_path"]),
            content_hash=str(guide_document["content_hash"]),
            last_modified=float(guide_document["last_modified"]),
            chunk_count=len(guide_document["chunks"]),  # type: ignore[arg-type]
            destination=str(guide_document["destination"]),
            status="active",
        )

    return len(chunks)


def _search_guide_chunks_by_chroma(
    query: str,
    top_k: int = RAG_TOP_K,
    destination: str | None = None,
    retrieval_scope: str | None = None,
    categories: list[str] | None = None,
    budget_tier: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """优先使用 Chroma 做向量检索，并返回在线 query embedding token。"""
    collection = _get_chroma_collection()
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    if collection is None:
        return [], empty_usage
    if collection.count() == 0:
        return [], empty_usage

    query_embedding, embedding_usage = _embed_query_with_usage(query)
    if query_embedding is None:
        return [], empty_usage
    query_args = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas"],
    }
    where = _build_chroma_where(
        destination,
        retrieval_scope,
        categories=categories,
        budget_tier=budget_tier,
    )
    if where:
        query_args["where"] = where
    result = collection.query(**query_args)

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    matched_chunks: list[dict[str, str]] = []
    for document, metadata in zip(documents, metadatas):
        title = metadata.get("title", "未命名片段") if metadata else "未命名片段"
        source = metadata.get("source", "未知来源") if metadata else "未知来源"
        document_id = (
            (metadata.get("document_id") or source) if metadata else source
        )
        content_hash = metadata.get("content_hash", "") if metadata else ""
        chunk_destination = metadata.get("destination", "") if metadata else ""
        category = metadata.get("category", "guide") if metadata else "guide"
        entity_name = metadata.get("entity_name", "") if metadata else ""
        section = metadata.get("section", "") if metadata else ""
        subsection = metadata.get("subsection", "") if metadata else ""
        budget_tier = metadata.get("budget_tier", "") if metadata else ""
        chunk_retrieval_scope = (
            metadata.get("retrieval_scope", RETRIEVAL_SCOPE_PLANNING)
            if metadata
            else RETRIEVAL_SCOPE_PLANNING
        )
        text = document.split("\n", 1)[1] if "\n" in document else document
        matched_chunks.append(
            {
                "title": title,
                "text": text,
                "source": source,
                "document_id": document_id,
                "content_hash": content_hash,
                "destination": chunk_destination,
                "category": category,
                "entity_name": entity_name,
                "section": section,
                "subsection": subsection,
                "budget_tier": budget_tier,
                "retrieval_scope": chunk_retrieval_scope,
            }
        )

    return matched_chunks, embedding_usage


def search_guide_chunks_with_usage(
    query: str,
    top_k: int = RAG_TOP_K,
    destination: str | None = None,
    retrieval_scope: str | None = None,
    categories: list[str] | None = None,
    budget_tier: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """
    从本地攻略片段里找最相关的 top_k 条结果。

    优先走 Chroma 向量检索；如果当前环境还没准备好，再回退到关键词检索。
    """
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    chroma_results, embedding_usage = _search_guide_chunks_by_chroma(
        query=query,
        top_k=top_k,
        destination=destination,
        retrieval_scope=retrieval_scope,
        categories=categories,
        budget_tier=budget_tier,
    )
    if chroma_results:
        return chroma_results, embedding_usage
    return _search_guide_chunks_by_keywords(
        query=query,
        top_k=top_k,
        destination=destination,
        retrieval_scope=retrieval_scope,
        categories=categories,
        budget_tier=budget_tier,
    ), empty_usage


def search_guide_chunks(
    query: str,
    top_k: int = RAG_TOP_K,
    destination: str | None = None,
    retrieval_scope: str | None = None,
    categories: list[str] | None = None,
    budget_tier: str | None = None,
) -> list[dict[str, str]]:
    """只返回检索片段（不含 token usage）。"""
    chunks, _ = search_guide_chunks_with_usage(
        query=query,
        top_k=top_k,
        destination=destination,
        retrieval_scope=retrieval_scope,
        categories=categories,
        budget_tier=budget_tier,
    )
    return chunks
