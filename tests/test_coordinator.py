"""Coordinator / API math and occupancy tests — mocked network."""

from __future__ import annotations

import pytest

from custom_components.dotnl_chargers.api import (
    bbox_area_deg2,
    classify_status,
    extract_energy_price,
    haversine_km,
    radius_to_bbox,
)
from custom_components.dotnl_chargers.const import MAX_BBOX_AREA_DEG2


def test_radius_to_bbox_area_within_cap():
    bbox = radius_to_bbox(52.09, 5.12, 2.0)
    assert bbox_area_deg2(bbox) <= MAX_BBOX_AREA_DEG2 + 1e-9
    min_lon, min_lat, max_lon, max_lat = bbox
    assert min_lon < 5.12 < max_lon
    assert min_lat < 52.09 < max_lat


def test_radius_to_bbox_large_radius_capped():
    """A huge radius must still produce area <= 1.0 deg²."""
    bbox = radius_to_bbox(52.09, 5.12, 100.0)
    area = bbox_area_deg2(bbox)
    assert area <= MAX_BBOX_AREA_DEG2 + 1e-6
    assert area == pytest.approx(MAX_BBOX_AREA_DEG2, rel=1e-4)


def test_haversine_same_point():
    assert haversine_km(52.0, 5.0, 52.0, 5.0) == pytest.approx(0.0, abs=1e-9)


def test_haversine_known_distance():
    # ~1 degree latitude ≈ 111 km
    d = haversine_km(52.0, 5.0, 53.0, 5.0)
    assert 110 < d < 112


@pytest.mark.parametrize(
    "available,total,expected",
    [
        (2, 2, "available"),
        (1, 2, "partial"),
        (0, 2, "occupied"),
        (0, 0, "unknown"),
        (3, 2, "available"),  # clamp treat as fully free
    ],
)
def test_classify_status(available, total, expected):
    assert classify_status(available, total) == expected


def test_extract_energy_price():
    tariff = {
        "id": "t-1",
        "elements": [
            {
                "price_components": [
                    {"type": "FLAT", "price": 0.0},
                    {"type": "ENERGY", "price": 0.21},
                ]
            }
        ],
    }
    assert extract_energy_price(tariff) == 0.21


def test_extract_energy_price_missing():
    assert extract_energy_price({"elements": []}) is None
    assert extract_energy_price({}) is None


@pytest.mark.asyncio
async def test_update_failed_keeps_last_good(mock_config_entry):
    """When API fails after a success, last_good_data is returned."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from homeassistant.helpers.update_coordinator import UpdateFailed

    from custom_components.dotnl_chargers.coordinator import DotNLChargersCoordinator

    hass = MagicMock()
    hass.config.latitude = 52.0907
    hass.config.longitude = 5.1214
    hass.bus.async_fire = MagicMock()
    hass.async_add_executor_job = AsyncMock()

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
        coord.entry = mock_config_entry
        coord.consecutive_errors = 0
        coord.last_good_data = None
        coord.last_update_status = "never"
        coord.last_update_success_timestamp = None
        coord._prev_ids = set()
        coord._history = []
        coord.api = MagicMock()
        coord.tariff_cache = MagicMock()
        coord.tariff_cache.is_stale = False
        coord.tariff_cache.async_load = AsyncMock()
        coord.tariff_cache.lookup = MagicMock(return_value=0.21)
        coord.logger = MagicMock()

        from tests.conftest import SAMPLE_FEATURE, SAMPLE_FEATURE_AVAILABLE

        coord.api.fetch_features = AsyncMock(
            return_value=[SAMPLE_FEATURE, SAMPLE_FEATURE_AVAILABLE]
        )

        payload = await DotNLChargersCoordinator._async_update_data(coord)
        assert payload["total"] >= 1
        assert coord.last_good_data is not None
        assert coord.consecutive_errors == 0

        from custom_components.dotnl_chargers.api import DotNLApiError

        coord.api.fetch_features = AsyncMock(side_effect=DotNLApiError("boom"))
        payload2 = await DotNLChargersCoordinator._async_update_data(coord)
        assert payload2 is coord.last_good_data
        assert coord.consecutive_errors == 1

        # With no last_good_data, UpdateFailed is raised
        coord.last_good_data = None
        coord.consecutive_errors = 0
        with pytest.raises(UpdateFailed):
            await DotNLChargersCoordinator._async_update_data(coord)
