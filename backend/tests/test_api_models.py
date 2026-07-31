from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.main import app  # noqa: E402
from app.llm import ZEN_FREE_MODELS  # noqa: E402


client = TestClient(app)


def test_models_endpoint_exposes_catalog_without_credentials() -> None:
    response = client.get("/models")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload["current"]) == {"provider", "model"}
    assert [item["id"] for item in payload["models"]] == list(ZEN_FREE_MODELS)
    assert "api_key" not in response.text.lower()
    assert "base_url" not in response.text.lower()
