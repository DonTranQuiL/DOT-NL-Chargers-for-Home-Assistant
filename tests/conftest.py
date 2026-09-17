"""Shared fixtures for DOT-NL Chargers tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.dotnl_chargers.const import DOMAIN

SAMPLE_FEATURE = {
    "type": "Feature",
    "id": "NL-GFX-0ACB965D-1AFA-4BEA-BAD2-289A3143ED38",
    "geometry": {"type": "Point", "coordinates": [5.137595, 52.093586]},
    "properties": {
        "address": "145 Maliebaan",
        "last_updated": "2026-09-17T16:10:54Z",
        "open": False,
        "cpo_id": "GFX",
        "availabilities": [
            {
                "available": 1,
                "connector_format": "SOCKET",
                "connector_type": "IEC_62196_T2",
                "power_max": 15000.0,
                "power_type": "AC3",
                "total": 2,
                "tariff_ids": ["t-sample-energy"],
            }
        ],
        "country": "NLD",
        "operator_name": "TotalEnergies",
        "owner_name": "TotalEnergies",
        "suboperator_name": None,
    },
}

SAMPLE_FEATURE_OCCUPIED = {
    "type": "Feature",
    "id": "NL-EFL-occupied-001",
    "geometry": {"type": "Point", "coordinates": [5.130000, 52.090000]},
    "properties": {
        "address": "10 Occupied Lane",
        "last_updated": "2026-09-17T16:00:00Z",
        "open": True,
        "cpo_id": "EFL",
        "availabilities": [
            {
                "available": 0,
                "connector_format": "SOCKET",
                "connector_type": "IEC_62196_T2",
                "power_max": 22000.0,
                "power_type": "AC3",
                "total": 2,
                "tariff_ids": [],
            }
        ],
        "country": "NLD",
        "operator_name": "E-Flux",
        "owner_name": None,
        "suboperator_name": "E-Flux",
    },
}

SAMPLE_FEATURE_AVAILABLE = {
    "type": "Feature",
    "id": "NL-LMS-available-001",
    "geometry": {"type": "Point", "coordinates": [5.125000, 52.095000]},
    "properties": {
        "address": "5 Free Street",
        "last_updated": "2026-09-17T16:05:00Z",
        "open": True,
        "cpo_id": "LMS",
        "availabilities": [
            {
                "available": 4,
                "connector_format": "CABLE",
                "connector_type": "IEC_62196_T2",
                "power_max": 11000.0,
                "power_type": "AC3",
                "total": 4,
                "tariff_ids": ["t-cheap"],
            }
        ],
        "country": "NLD",
        "operator_name": "50five",
        "owner_name": "50five",
        "suboperator_name": "50five",
    },
}


@pytest.fixture
def sample_features():
    return [SAMPLE_FEATURE, SAMPLE_FEATURE_OCCUPIED, SAMPLE_FEATURE_AVAILABLE]


@pytest.fixture
def mock_api_features(sample_features):
    with patch(
        "custom_components.dotnl_chargers.api.DotNLChargersApi.fetch_features",
        new_callable=AsyncMock,
        return_value=sample_features,
    ) as mock:
        yield mock


@pytest.fixture
def mock_api_tariffs():
    with patch(
        "custom_components.dotnl_chargers.api.DotNLChargersApi.fetch_tariffs",
        new_callable=AsyncMock,
        return_value={"t-sample-energy": 0.40, "t-cheap": 0.21},
    ) as mock:
        yield mock


@pytest.fixture
def hass_config_defaults():
    return {"latitude": 52.0907, "longitude": 5.1214}


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.title = "DOT-NL Chargers (test)"
    entry.data = {
        "instance_name": "test",
        "latitude": 52.0907,
        "longitude": 5.1214,
        "radius_km": 2.0,
    }
    entry.options = {
        "scan_interval": 120,
        "radius_km": 2.0,
        "min_available": 0,
        "power_min_kw": 0.0,
        "enable_map_trackers": True,
        "enable_tariff_enrichment": True,
        "max_map_markers": 40,
        "show_only_open": False,
    }
    entry.add_update_listener = MagicMock()
    return entry
