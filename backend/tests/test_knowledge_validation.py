from pathlib import Path
import sys


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag import knowledge_validation  # noqa: E402


def test_current_knowledge_base_is_consistent() -> None:
    """当前攻略、fallback 和评估断言必须保持一致。"""
    assert knowledge_validation.validate_knowledge_base() == []
