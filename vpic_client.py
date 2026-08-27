import httpx

VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
_TIMEOUT = 10.0


class VinNotFoundError(Exception):
    """Raised when vPIC returns a successful response but has no data for the VIN."""


class VinDecodeServiceError(Exception):
    """Raised when the vPIC API call fails, errors, or times out."""


async def decode_vin(vin: str) -> dict:
    """Call vPIC DecodeVinValues and return decoded fields for the given VIN.

    Returns a dict with keys: make, model, model_year, body_class.
    Raises VinNotFoundError if vPIC has no data for the VIN.
    Raises VinDecodeServiceError if the request fails or times out.
    """
    url = VPIC_URL.format(vin=vin)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise VinDecodeServiceError("vPIC request failed") from exc
    except httpx.HTTPStatusError as exc:
        raise VinDecodeServiceError("vPIC returned an error status") from exc

    result = response.json().get("Results", [{}])[0]

    make = result.get("Make", "")
    model = result.get("Model", "")
    model_year = result.get("ModelYear", "")
    body_class = result.get("BodyClass", "")

    if not make and not model and not body_class:
        raise VinNotFoundError(vin)

    return {
        "make": make,
        "model": model,
        "model_year": model_year,
        "body_class": body_class,
    }
