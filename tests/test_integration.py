"""End-to-end-ish integration tests with fully mocked network I/O."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.dotnl_chargers.api import DotNLChargersApi
from custom_components.dotnl_chargers.const import DOMAIN, ITEM_FIELDS
from tests.conftest import SAMPLE_FEATURE


@pytest.mark.asyncio
async def test_api_fetch_features_mocked():
    session = MagicMock()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(
        return_value={"type": "FeatureCollection", "features": [SAMPLE_FEATURE]}
    )
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=response)

    api = DotNLChargersApi(session)
    features = await api.fetch_features(52.09, 5.12, 2.0)
    assert len(features) == 1
    assert features[0]["id"] == SAMPLE_FEATURE["id"]
    # Ensure User-Agent set
    _args, kwargs = session.get.call_args
    assert "HomeAssistant-DotNL-Chargers/0.1.0" in kwargs["headers"]["User-Agent"]


@pytest.mark.asyncio
async def test_api_http_error():
    from custom_components.dotnl_chargers.api import DotNLApiError

    session = MagicMock()
    response = AsyncMock()
    response.status = 500
    response.text = AsyncMock(return_value="nope")
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=response)

    api = DotNLChargersApi(session)
    with pytest.raises(DotNLApiError):
        await api.fetch_features(52.09, 5.12, 2.0)


def test_item_whitelist_keys():
    """Coordinator item keys must be a subset of ITEM_FIELDS."""
    from custom_components.dotnl_chargers.coordinator import DotNLChargersCoordinator

    hass = MagicMock()
    hass.config.latitude = 52.09
    hass.config.longitude = 5.12
    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {
        "instance_name": "t",
        "latitude": 52.09,
        "longitude": 5.12,
        "radius_km": 2.0,
    }
    entry.options = {}

    with (
        patch(
            "custom_components.dotnl_chargers.coordinator.async_get_clientsession"
        ),
        patch(
            "custom_components.dotnl_chargers.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ),
    ):
        coord = DotNLChargersCoordinator.__new__(DotNLChargersCoordinator)
        coord.hass = hass
        coord.entry = entry
        coord.tariff_cache = MagicMock()
        coord.tariff_cache.lookup = MagicMock(return_value=0.4)

        item = DotNLChargersCoordinator._feature_to_item(
            coord, SAMPLE_FEATURE, 52.09, 5.12
        )
        assert item is not None
        assert set(item.keys()) <= set(ITEM_FIELDS)
        assert item["status"] == "partial"
        assert item["max_power_kw"] == 15.0
        assert item["available"] == 1
        assert item["total"] == 2
        assert item["occupied"] == 1
        assert DOMAIN == "dotnl_chargers"
