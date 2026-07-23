from __future__ import annotations

from pathlib import Path
import sys


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_DIR,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    OLLAMA_EMBED_URL,
)
from app.rag.document_registry import list_documents
from app.rag.vector_db import ingest_guide_chunks_to_chroma, load_guide_documents


def main() -> int:
    guide_documents = load_guide_documents()
    chunk_count = sum(len(doc["chunks"]) for doc in guide_documents)

    print("=== 准备写入 Chroma + 文档清单 ===")
    print(f"document_count: {len(guide_documents)}")
    print(f"chunk_count: {chunk_count}")
    print(f"embedding_provider: {EMBEDDING_PROVIDER}")
    print(f"embedding_model: {EMBEDDING_MODEL}")
    if EMBEDDING_PROVIDER == "ollama":
        print(f"ollama_embed_url: {OLLAMA_EMBED_URL}")
    print(f"chroma_db_dir: {CHROMA_DB_DIR}")
    print(f"collection_name: {CHROMA_COLLECTION_NAME}")
    print()

    for doc in guide_documents:
        print(
            f"- {doc['document_id']}: hash={str(doc['content_hash'])[:12]}... "
            f"chunks={len(doc['chunks'])} destination={doc['destination']}"
        )
    print()

    written_count = ingest_guide_chunks_to_chroma()

    print("=== 写入完成 ===")
    print(f"written_count: {written_count}")
    print()
    print("=== 文档清单 (kb_documents) ===")
    for record in list_documents(status=None):
        print(
            f"- {record.document_id}: hash={record.content_hash[:12]}... "
            f"chunks={record.chunk_count} status={record.status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
