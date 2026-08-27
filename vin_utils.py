from fastapi import HTTPException

_EXCLUDED_LETTERS = "IOQ"


def validate_vin(vin: str) -> str:
    """Normalize and validate a VIN string.

    Normalizes by trimming whitespace and uppercasing, then checks that the
    result is exactly 17 alphanumeric characters with no I, O, or Q.

    Returns the normalized VIN on success.
    Raises HTTPException 400 on any validation failure.
    """
    normalized = vin.strip().upper()

    if len(normalized) != 17:
        raise HTTPException(status_code=400, detail=f"Invalid VIN: {normalized}")

    if not normalized.isalnum():
        raise HTTPException(status_code=400, detail=f"Invalid VIN: {normalized}")

    if any(char in _EXCLUDED_LETTERS for char in normalized):
        raise HTTPException(status_code=400, detail=f"Invalid VIN: {normalized}")

    return normalized