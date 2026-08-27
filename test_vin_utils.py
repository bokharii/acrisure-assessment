import pytest
from fastapi import HTTPException

from vin_utils import validate_vin


def test_valid_vin_returns_normalized():
    assert validate_vin("1FTZF1724XNB39516") == "1FTZF1724XNB39516"


def test_lowercase_vin_is_uppercased():
    assert validate_vin("1ftzf1724xnb39516") == "1FTZF1724XNB39516"


def test_whitespace_is_trimmed():
    assert validate_vin("  1FTZF1724XNB39516  ") == "1FTZF1724XNB39516"


def test_wrong_length_raises_400():
    with pytest.raises(HTTPException) as exc_info:
        validate_vin("SHORT")
    assert exc_info.value.status_code == 400


def test_contains_q_raises_400():
    with pytest.raises(HTTPException):
        validate_vin("1FTZQ1724XNB39516")