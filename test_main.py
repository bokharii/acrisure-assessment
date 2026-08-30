import io
import sqlite3
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import db
import main
from db import insert_vin
from main import app, get_http_client
from vpic_client import VinDecodeServiceError, VinNotFoundError

client = TestClient(app)

VALID_VIN = "1HGCM82633A004352"
DECODED_DATA = {
    "make": "HONDA",
    "model": "Accord",
    "model_year": "2003",
    "body_class": "Coupe",
}


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point db.DB_PATH at a temporary file for each test, then create the table."""
    test_db_path = tmp_path / "test_cache.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    yield


@pytest.fixture
def mock_decode_vin(monkeypatch):
    """Replace decode_vin with a controllable AsyncMock for each test."""
    mock = AsyncMock()
    monkeypatch.setattr(main, "decode_vin", mock)
    return mock


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides don't bleed between tests."""
    yield
    app.dependency_overrides.clear()


# ── /lookup ───────────────────────────────────────────────────────────────────

def test_lookup_calls_vpic_and_caches_on_miss(mock_decode_vin):
    mock_decode_vin.return_value = DECODED_DATA
    app.dependency_overrides[get_http_client] = lambda: AsyncMock()

    response = client.post("/lookup", json={"vin": VALID_VIN})

    assert response.status_code == 200
    body = response.json()
    assert body["make"] == "HONDA"
    assert body["cached"] is False


def test_lookup_returns_cached_result_on_second_call(mock_decode_vin):
    mock_decode_vin.return_value = DECODED_DATA
    app.dependency_overrides[get_http_client] = lambda: AsyncMock()

    client.post("/lookup", json={"vin": VALID_VIN})
    response = client.post("/lookup", json={"vin": VALID_VIN})

    assert response.status_code == 200
    body = response.json()
    assert body["cached"] is True
    assert body["make"] == "HONDA"
    assert mock_decode_vin.call_count == 1


def test_lookup_returns_404_when_vin_not_found(mock_decode_vin):
    mock_decode_vin.side_effect = VinNotFoundError(VALID_VIN)
    app.dependency_overrides[get_http_client] = lambda: AsyncMock()

    response = client.post("/lookup", json={"vin": VALID_VIN})

    assert response.status_code == 404
    assert f"No data found for VIN: {VALID_VIN}" in response.json()["detail"]


def test_lookup_returns_502_when_vpic_fails(mock_decode_vin):
    mock_decode_vin.side_effect = VinDecodeServiceError("timeout")
    app.dependency_overrides[get_http_client] = lambda: AsyncMock()

    response = client.post("/lookup", json={"vin": VALID_VIN})

    assert response.status_code == 502


def test_lookup_returns_400_for_invalid_vin():
    app.dependency_overrides[get_http_client] = lambda: AsyncMock()

    response = client.post("/lookup", json={"vin": "TOOSHORT"})

    assert response.status_code == 400


def test_lookup_returns_500_when_insert_fails(mock_decode_vin, monkeypatch):
    mock_decode_vin.return_value = DECODED_DATA
    app.dependency_overrides[get_http_client] = lambda: AsyncMock()

    def _raise_sqlite_error(*args: object, **kwargs: object) -> None:
        raise sqlite3.Error("disk i/o")

    monkeypatch.setattr(main, "insert_vin", _raise_sqlite_error)

    response = client.post("/lookup", json={"vin": VALID_VIN})

    assert response.status_code == 500


# ── /remove ───────────────────────────────────────────────────────────────────

def test_remove_returns_success_for_existing_vin():
    insert_vin(VALID_VIN, DECODED_DATA)

    response = client.post("/remove", json={"vin": VALID_VIN})

    assert response.status_code == 200
    body = response.json()
    assert body["vin"] == VALID_VIN
    assert body["success"] is True


def test_remove_returns_success_for_uncached_vin():
    response = client.post("/remove", json={"vin": VALID_VIN})

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_remove_returns_400_for_invalid_vin():
    response = client.post("/remove", json={"vin": "BAD"})

    assert response.status_code == 400


# ── /export ───────────────────────────────────────────────────────────────────

def test_export_returns_empty_parquet_when_cache_is_empty():
    response = client.get("/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"

    df = pd.read_parquet(io.BytesIO(response.content))
    assert list(df.columns) == ["vin", "make", "model", "model_year", "body_class"]
    assert len(df) == 0


def test_export_returns_parquet_with_cached_vins(mock_decode_vin):
    mock_decode_vin.return_value = DECODED_DATA
    app.dependency_overrides[get_http_client] = lambda: AsyncMock()

    client.post("/lookup", json={"vin": VALID_VIN})

    response = client.get("/export")

    assert response.status_code == 200
    df = pd.read_parquet(io.BytesIO(response.content))
    assert len(df) == 1
    assert df.iloc[0]["vin"] == VALID_VIN
    assert df.iloc[0]["make"] == "HONDA"
