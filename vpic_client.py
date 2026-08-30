import httpx

VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
_TIMEOUT = 10.0


class VinNotFoundError(Exception):
    """Raised when vPIC returns a successful response but has no data for the VIN."""


class VinDecodeServiceError(Exception):
    """Raised when the vPIC API call fails, errors, or times out."""


def create_http_client() -> httpx.AsyncClient:
    """Return an httpx client configured for vPIC requests."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


def _parse_decode_result(payload: object) -> dict:
    """Extract decode fields from a vPIC JSON payload.

    Raises VinDecodeServiceError if the payload shape is unexpected.
    """
    if not isinstance(payload, dict):
        raise VinDecodeServiceError("vPIC returned an unexpected payload")

    results = payload.get("Results")
    if not isinstance(results, list) or not results:
        raise VinDecodeServiceError("vPIC returned an unexpected payload")

    result = results[0]
    if not isinstance(result, dict):
        raise VinDecodeServiceError("vPIC returned an unexpected payload")

    return {
        "make": result.get("Make") or "",
        "model": result.get("Model") or "",
        "model_year": result.get("ModelYear") or "",
        "body_class": result.get("BodyClass") or "",
    }


async def decode_vin(vin: str, client: httpx.AsyncClient) -> dict:
    """Call vPIC DecodeVinValues and return decoded fields for the given VIN.

    Returns a dict with keys: make, model, model_year, body_class.
    Raises VinNotFoundError if vPIC has no data for the VIN.
    Raises VinDecodeServiceError if the request fails, times out, or
    returns an unusable payload.
    """
    url = VPIC_URL.format(vin=vin)

    try:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    except httpx.RequestError as exc:
        raise VinDecodeServiceError("vPIC request failed") from exc
    except httpx.HTTPStatusError as exc:
        raise VinDecodeServiceError("vPIC returned an error status") from exc
    except ValueError as exc:
        raise VinDecodeServiceError("vPIC returned invalid JSON") from exc

    fields = _parse_decode_result(payload)

    if not fields["make"] and not fields["model"] and not fields["body_class"]:
        raise VinNotFoundError(vin)

    return fields
