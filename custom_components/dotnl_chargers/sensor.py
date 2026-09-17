"""Sensor platform for DOT-NL Chargers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_INSTANCE_NAME,
    DOMAIN,
    MANUFACTURER,
    NAME,
)
from .coordinator import DotNLChargersCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotNLChargersCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DotNLOverviewSensor(coordinator, entry),
            DotNLAvailableStationsSensor(coordinator, entry),
            DotNLOccupiedStationsSensor(coordinator, entry),
            DotNLFreeConnectorsSensor(coordinator, entry),
            DotNLTotalConnectorsSensor(coordinator, entry),
            DotNLClosestAvailableSensor(coordinator, entry),
            DotNLCheapestSensor(coordinator, entry),
            DotNLConsecutiveErrorsSensor(coordinator, entry),
            DotNLLastUpdateStatusSensor(coordinator, entry),
            DotNLLastUpdateTimeSensor(coordinator, entry),
        ]
    )


class DotNLBaseSensor(CoordinatorEntity[DotNLChargersCoordinator], SensorEntity):
    """Shared base for DOT-NL sensors — one DeviceInfo per entry."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: DotNLChargersCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        instance = entry.data.get(CONF_INSTANCE_NAME, NAME)
        self._attr_unique_id = f"{DOMAIN}_{key}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{NAME} ({instance})",
            manufacturer=MANUFACTURER,
            model="DOT-NL / NDW AFIR Open Data",
            configuration_url=(
                "https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant"
            ),
        )

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}


class DotNLOverviewSensor(DotNLBaseSensor):
    """Fat overview sensor — free connectors (or available stations) + attrs."""

    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "overview")
        self._attr_name = "Overview"
        self._attr_icon = "mdi:ev-station"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        counts = self._data.get("counts") or {}
        free = counts.get("connectors_free")
        if free is not None:
            return int(free)
        return int(counts.get("available") or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._data
        return {
            "items": data.get("items") or [],
            "history": data.get("history") or [],
            "counts": data.get("counts") or {},
            "closest": data.get("closest"),
            "cheapest": data.get("cheapest"),
            "total": data.get("total", 0),
            "entered": data.get("entered") or [],
            "exited": data.get("exited") or [],
            "attribution": ATTRIBUTION,
        }


class DotNLAvailableStationsSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "available_stations")
        self._attr_name = "Available stations"
        self._attr_icon = "mdi:ev-station"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return int((self._data.get("counts") or {}).get("available") or 0)


class DotNLOccupiedStationsSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "occupied_stations")
        self._attr_name = "Occupied stations"
        self._attr_icon = "mdi:ev-station"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return int((self._data.get("counts") or {}).get("occupied") or 0)


class DotNLFreeConnectorsSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "free_connectors")
        self._attr_name = "Free connectors"
        self._attr_icon = "mdi:power-plug"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return int((self._data.get("counts") or {}).get("connectors_free") or 0)


class DotNLTotalConnectorsSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "total_connectors")
        self._attr_name = "Total connectors"
        self._attr_icon = "mdi:power-plug-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return int((self._data.get("counts") or {}).get("connectors_total") or 0)


class DotNLClosestAvailableSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "closest_available")
        self._attr_name = "Closest available"
        self._attr_icon = "mdi:map-marker-distance"
        self._attr_native_unit_of_measurement = "km"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        closest = self._data.get("closest")
        if not closest:
            return None
        return float(closest.get("distance_km") or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        closest = self._data.get("closest") or {}
        return dict(closest) if closest else {}


class DotNLCheapestSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "cheapest_eur_kwh")
        self._attr_name = "Cheapest energy price"
        self._attr_icon = "mdi:currency-eur"
        self._attr_native_unit_of_measurement = "EUR/kWh"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        cheapest = self._data.get("cheapest")
        if not cheapest:
            return None
        price = cheapest.get("energy_price_eur_kwh")
        return float(price) if price is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cheapest = self._data.get("cheapest") or {}
        return dict(cheapest) if cheapest else {}


class DotNLConsecutiveErrorsSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "consecutive_errors")
        self._attr_name = "Consecutive errors"
        self._attr_icon = "mdi:alert-circle"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return int(self.coordinator.consecutive_errors)


class DotNLLastUpdateStatusSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "last_update_status")
        self._attr_name = "Last update status"
        self._attr_icon = "mdi:cloud-sync"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        return str(self.coordinator.last_update_status)


class DotNLLastUpdateTimeSensor(DotNLBaseSensor):
    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "last_update_time")
        self._attr_name = "Last update time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:clock-check"

    @property
    def native_value(self):
        return self.coordinator.last_update_success_timestamp
