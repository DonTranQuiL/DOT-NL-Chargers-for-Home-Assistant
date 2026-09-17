"""Sensor state unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.dotnl_chargers.sensor import (
    DotNLAvailableStationsSensor,
    DotNLCheapestSensor,
    DotNLConsecutiveErrorsSensor,
    DotNLFreeConnectorsSensor,
    DotNLOverviewSensor,
)


def _coord_with(data, errors=0):
    coord = MagicMock()
    coord.data = data
    coord.consecutive_errors = errors
    coord.last_update_status = "ok"
    coord.last_update_success_timestamp = None
    return coord


def _entry():
    entry = MagicMock()
    entry.entry_id = "abc"
    entry.data = {"instance_name": "test"}
    return entry


def test_overview_state_free_connectors():
    data = {
        "counts": {
            "available": 2,
            "occupied": 1,
            "partial": 1,
            "connectors_free": 5,
            "connectors_total": 10,
        },
        "items": [{"id": "x"}],
        "history": [],
        "closest": None,
        "cheapest": None,
        "total": 1,
        "entered": [],
        "exited": [],
    }
    sensor = DotNLOverviewSensor(_coord_with(data), _entry())
    assert sensor.native_value == 5
    attrs = sensor.extra_state_attributes
    assert "items" in attrs
    assert "counts" in attrs
    assert attrs["counts"]["connectors_free"] == 5


def test_available_and_free_sensors():
    data = {
        "counts": {
            "available": 3,
            "occupied": 1,
            "partial": 0,
            "connectors_free": 7,
            "connectors_total": 12,
        }
    }
    entry = _entry()
    coord = _coord_with(data)
    assert DotNLAvailableStationsSensor(coord, entry).native_value == 3
    assert DotNLFreeConnectorsSensor(coord, entry).native_value == 7


def test_cheapest_sensor():
    data = {
        "cheapest": {
            "id": "c1",
            "energy_price_eur_kwh": 0.21,
            "name": "Cheap",
        }
    }
    sensor = DotNLCheapestSensor(_coord_with(data), _entry())
    assert sensor.native_value == 0.21
    assert sensor.extra_state_attributes["id"] == "c1"


def test_consecutive_errors_diagnostic():
    sensor = DotNLConsecutiveErrorsSensor(_coord_with({}, errors=4), _entry())
    assert sensor.native_value == 4
