import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from vpic_client import VinDecodeServiceError, VinNotFoundError, decode_vin

VIN = "1HGCM82633A004352"

pytestmark = pytest.mark.asyncio


def _make_response(payload: dict, status_error: bool = False) -> MagicMock:
    """Build a mock httpx response with a controllable json() and raise_for_status()."""
    response = MagicMock()
    response.json.return_value = payload
    if status_error:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
    else:
        response.raise_for_status.return_value = None
    return response


async def test_decode_vin_success():
    payload = {
        "Results": [
            {
                "Make": "HONDA",
                "Model": "Accord",
                "ModelYear": "2003",
                "BodyClass": "Coupe",
            }
        ]
    }
    client = AsyncMock()
    client.get.return_value = _make_response(payload)

    result = await decode_vin(VIN, client)

    assert result == {
        "make": "HONDA",
        "model": "Accord",
        "model_year": "2003",
        "body_class": "Coupe",
    }


async def test_decode_vin_raises_not_found_when_fields_empty():
    payload = {
        "Results": [
            {
                "Make": "",
                "Model": "",
                "ModelYear": "",
                "BodyClass": "",
            }
        ]
    }
    client = AsyncMock()
    client.get.return_value = _make_response(payload)

    with pytest.raises(VinNotFoundError):
        await decode_vin(VIN, client)


async def test_decode_vin_raises_service_error_on_request_error():
    client = AsyncMock()
    client.get.side_effect = httpx.RequestError("connection failed")

    with pytest.raises(VinDecodeServiceError):
        await decode_vin(VIN, client)


async def test_decode_vin_raises_service_error_on_http_status_error():
    client = AsyncMock()
    client.get.return_value = _make_response({}, status_error=True)

    with pytest.raises(VinDecodeServiceError):
        await decode_vin(VIN, client)
