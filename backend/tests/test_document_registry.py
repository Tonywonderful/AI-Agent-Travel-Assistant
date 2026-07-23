from pathlib import Path
import sys


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag import document_registry, vector_db  # noqa: E402


def test_loaded_guide_chunks_have_document_id_and_content_hash() -> None:
    """每个 chunk 必须带正式 document_id，且同文档 content_hash 一致。"""
    chunks = vector_db.load_guide_chunks()
    assert chunks

    by_document: dict[str, set[str]] = {}
    for chunk in chunks:
        document_id = chunk["document_id"]
        assert document_id
        assert chunk["source"] == document_id
        assert chunk["content_hash"]
        assert len(chunk["content_hash"]) == 64  # sha256 hex
        by_document.setdefault(document_id, set()).add(chunk["content_hash"])

    # 同一文档下所有 chunk 的 content_hash 必须相同
    for document_id, hashes in by_document.items():
        assert len(hashes) == 1, f"{document_id} 出现多个 content_hash: {hashes}"


def test_load_guide_documents_matches_chunk_grouping() -> None:
    """按文档读取时，document_id/hash/chunk 数应与 load_guide_chunks 对齐。"""
    chunks = vector_db.load_guide_chunks()
    documents = vector_db.load_guide_documents()

    assert documents
    assert {doc["document_id"] for doc in documents} == {c["document_id"] for c in chunks}

    chunk_count_by_doc: dict[str, int] = {}
    for chunk in chunks:
        chunk_count_by_doc[chunk["document_id"]] = chunk_count_by_doc.get(chunk["document_id"], 0) + 1

    for doc in documents:
        assert doc["content_hash"]
        assert len(doc["chunks"]) == chunk_count_by_doc[doc["document_id"]]
        assert all(c["document_id"] == doc["document_id"] for c in doc["chunks"])
        assert all(c["content_hash"] == doc["content_hash"] for c in doc["chunks"])


def test_compute_content_hash_is_stable_and_sensitive() -> None:
    """content_hash：相同正文稳定；改一字即变；换行差异被规范化。"""
    base = "标题\n正文A"
    assert document_registry.compute_content_hash(base) == document_registry.compute_content_hash(base)
    assert document_registry.compute_content_hash(base) != document_registry.compute_content_hash("标题\n正文B")
    assert document_registry.compute_content_hash("a\r\nb") == document_registry.compute_content_hash("a\nb")


def test_upsert_and_list_documents(tmp_path, monkeypatch) -> None:
    """文档清单可写入并读出 document_id + content_hash。"""
    db_path = tmp_path / "test_kb.db"
    monkeypatch.setattr(
        "app.config.DATABASE_URL",
        f"sqlite:///{db_path.as_posix()}",
    )
    # 重新绑定 engine/session 到临时库
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(document_registry, "engine", test_engine)
    monkeypatch.setattr(document_registry, "SessionLocal", TestSession)

    from app.config import Base
    from app.models.db_models import KnowledgeDocument  # noqa: F401

    Base.metadata.create_all(bind=test_engine)

    document_registry.upsert_document(
        document_id="beijing_guide.md",
        source_path="data/beijing_guide.md",
        content_hash="a" * 64,
        last_modified=1.0,
        chunk_count=3,
        destination="北京",
        status="active",
    )
    document_registry.upsert_document(
        document_id="beijing_guide.md",
        source_path="data/beijing_guide.md",
        content_hash="b" * 64,
        last_modified=2.0,
        chunk_count=4,
        destination="北京",
        status="active",
    )

    records = document_registry.list_documents()
    assert len(records) == 1
    assert records[0].document_id == "beijing_guide.md"
    assert records[0].content_hash == "b" * 64
    assert records[0].chunk_count == 4
