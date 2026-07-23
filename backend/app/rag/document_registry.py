"""知识库文档清单：维护 document_id + content_hash。"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path

from app.config import SessionLocal, engine
from app.models.db_models import KnowledgeDocument


def init_kb_tables() -> None:
    """确保 kb_documents 表存在。"""
    from app.config import Base

    # 导入模型，保证表定义注册到 Base.metadata
    from app.models import db_models as _db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def compute_content_hash(text: str) -> str:
    """对文档正文计算内容指纹（统一换行后 sha256）。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256(normalized.encode("utf-8")).hexdigest()


def compute_file_content_hash(file_path: Path) -> str:
    """读取文件并计算 content_hash。"""
    text = file_path.read_text(encoding="utf-8")
    return compute_content_hash(text)


def get_document(document_id: str) -> KnowledgeDocument | None:
    """按 document_id 查询文档清单记录。"""
    init_kb_tables()
    session = SessionLocal()
    try:
        return (
            session.query(KnowledgeDocument)
            .filter(KnowledgeDocument.document_id == document_id)
            .first()
        )
    finally:
        session.close()


def list_documents(status: str | None = "active") -> list[KnowledgeDocument]:
    """列出文档清单；默认只返回 active。status=None 时返回全部。"""
    init_kb_tables()
    session = SessionLocal()
    try:
        query = session.query(KnowledgeDocument)
        if status is not None:
            query = query.filter(KnowledgeDocument.status == status)
        return list(query.order_by(KnowledgeDocument.document_id).all())
    finally:
        session.close()


def upsert_document(
    *,
    document_id: str,
    source_path: str,
    content_hash: str,
    last_modified: float,
    chunk_count: int,
    destination: str = "",
    status: str = "active",
) -> None:
    """新增或更新文档清单中的一条记录。"""
    init_kb_tables()
    session = SessionLocal()
    try:
        record = (
            session.query(KnowledgeDocument)
            .filter(KnowledgeDocument.document_id == document_id)
            .first()
        )
        if record is None:
            session.add(
                KnowledgeDocument(
                    document_id=document_id,
                    source_path=source_path,
                    content_hash=content_hash,
                    last_modified=last_modified,
                    chunk_count=chunk_count,
                    destination=destination,
                    status=status,
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            record.source_path = source_path
            record.content_hash = content_hash
            record.last_modified = last_modified
            record.chunk_count = chunk_count
            record.destination = destination
            record.status = status
            record.updated_at = datetime.utcnow()
        session.commit()
    finally:
        session.close()


def remove_document(document_id: str) -> bool:
    """从文档清单中删除一条记录。存在并删除返回 True，不存在返回 False。"""
    init_kb_tables()
    session = SessionLocal()
    try:
        record = (
            session.query(KnowledgeDocument)
            .filter(KnowledgeDocument.document_id == document_id)
            .first()
        )
        if record is None:
            return False
        session.delete(record)
        session.commit()
        return True
    finally:
        session.close()


def document_to_dict(record: KnowledgeDocument) -> dict[str, object]:
    """把 ORM 记录转成普通 dict，方便脚本打印。"""
    return {
        "document_id": record.document_id,
        "source_path": record.source_path,
        "content_hash": record.content_hash,
        "last_modified": record.last_modified,
        "chunk_count": record.chunk_count,
        "destination": record.destination,
        "status": record.status,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
