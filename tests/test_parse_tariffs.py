"""parse_tariffs runs off the event loop and handles gzip/plain payloads."""

import gzip
import json

import pytest

from custom_components.dotnl_chargers.api import DotNLApiError, parse_tariffs

TARIFFS = {
    "data": [
        {
            "id": "t1",
            "elements": [{"price_components": [{"type": "ENERGY", "price": 0.39}]}],
        },
        {
            "id": "t2",
            "elements": [{"price_components": [{"type": "TIME", "price": 2}]}],
        },
        {"elements": []},
    ]
}


def test_parse_gzip_and_plain():
    raw = json.dumps(TARIFFS).encode()
    assert parse_tariffs(raw) == {"t1": 0.39}
    assert parse_tariffs(gzip.compress(raw)) == {"t1": 0.39}


def test_parse_invalid():
    with pytest.raises(DotNLApiError):
        parse_tariffs(b"\x1f\x8bnot-gzip")
    with pytest.raises(DotNLApiError):
        parse_tariffs(b"{nope")
