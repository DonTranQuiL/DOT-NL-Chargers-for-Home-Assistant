"""Device tracker platform — map markers for nearby DOT-NL chargers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_ENABLE_MAP_TRACKERS,
    CONF_INSTANCE_NAME,
    DEFAULT_ENABLE_MAP_TRACKERS,
    DOMAIN,
    MANUFACTURER,
    NAME,
)
from .coordinator import DotNLChargersCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotNLChargersCoordinator = hass.data[DOMAIN][entry.entry_id]
    active: dict[str, DotNLChargerTracker] = {}

    def _charger_id_from_unique_id(unique_id: str) -> str | None:
        prefix = f"{DOMAIN}_tracker_"
        suffix = f"_{entry.entry_id}"
        if not unique_id.startswith(prefix) or not unique_id.endswith(suffix):
            return None
        charger_id = unique_id[len(prefix) : -len(suffix)]
        return charger_id or None

    def _purge_registry(keep: set[str]) -> None:
        """Delete tracker registry rows that are no longer in the cap.

        Options reload drops entities the platform does not re-add. Those
        rows otherwise stay in the registry and show up as unavailable.
        """
        registry = er.async_get(hass)
        for reg in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
            if reg.domain != "device_tracker":
                continue
            charger_id = _charger_id_from_unique_id(reg.unique_id)
            if charger_id is None or charger_id in keep:
                continue
            registry.async_remove(reg.entity_id)
            _LOGGER.debug("Removed dropped tracker %s", charger_id)

    @callback
    def _update() -> None:
        enable = entry.options.get(
            CONF_ENABLE_MAP_TRACKERS,
            entry.data.get(CONF_ENABLE_MAP_TRACKERS, DEFAULT_ENABLE_MAP_TRACKERS),
        )
        if not enable:
            _force_remove(list(active.keys()))
            _purge_registry(set())
            return

        data = coordinator.data or {}
        tracked = data.get("tracked") or []
        current_ids: set[str] = set()
        new_entities: list[DotNLChargerTracker] = []

        for item in tracked:
            cid = item.get("id")
            if not cid:
                continue
            current_ids.add(cid)
            if cid not in active:
                tracker = DotNLChargerTracker(coordinator, entry, cid)
                active[cid] = tracker
                new_entities.append(tracker)

        if new_entities:
            async_add_entities(new_entities)

        # Cap went down, or a station left the feed: drop it now.
        # Waiting leaves the old pins as unavailable after an options reload.
        dropped = [cid for cid in list(active) if cid not in current_ids]
        if dropped:
            _force_remove(dropped)
        _purge_registry(current_ids)

    def _force_remove(ids: list[str]) -> None:
        registry = er.async_get(hass)
        for cid in ids:
            entity = active.pop(cid, None)
            if entity is None:
                continue
            entity_id = entity.entity_id
            hass.async_create_task(entity.async_remove(force_remove=True))
            if entity_id and registry.async_get(entity_id):
                registry.async_remove(entity_id)
            _LOGGER.debug("Removed tracker %s", cid)

    coordinator.async_add_listener(_update)
    _update()


class DotNLChargerTracker(CoordinatorEntity[DotNLChargersCoordinator], TrackerEntity):
    """GPS tracker for a single charge point (map pin)."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:ev-station"
    # BaseTrackerEntity sets this to DIAGNOSTIC. These pins are the
    # stations the user wants on the device page, so keep them uncategorized.
    # device_tracker is grouped under Sensors when category is None.
    _attr_entity_category = None

    def __init__(
        self,
        coordinator: DotNLChargersCoordinator,
        entry: ConfigEntry,
        charger_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._charger_id = charger_id
        instance = entry.data.get(CONF_INSTANCE_NAME, NAME)
        self._attr_unique_id = f"{DOMAIN}_tracker_{charger_id}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{NAME} ({instance})",
            manufacturer=MANUFACTURER,
            model="DOT-NL / NDW AFIR Open Data",
        )

    def _item(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        for collection in ("tracked", "items"):
            for item in data.get(collection) or []:
                if item.get("id") == self._charger_id:
                    return item
        return None

    @property
    def name(self) -> str:
        item = self._item()
        if item:
            return item.get("name") or self._charger_id
        return f"Charger {self._charger_id[-8:]}"

    @property
    def latitude(self) -> float | None:
        item = self._item()
        return item.get("latitude") if item else None

    @property
    def longitude(self) -> float | None:
        item = self._item()
        return item.get("longitude") if item else None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def entity_picture(self) -> str:
        """Map pin image. Without this, Home Assistant draws name initials.

        Every tracker name starts with the device name, so the initials are
        always DC. A status-colored picture replaces that badge.
        """
        item = self._item()
        status = (item or {}).get("status") or "unknown"
        if status not in ("available", "partial", "occupied", "unknown"):
            status = "unknown"
        return f"/{DOMAIN}_assets/marker-{status}.png"

    @property
    def location_name(self) -> str | None:
        item = self._item()
        if not item:
            return "not_home"
        status = item.get("status", "unknown")
        return status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        item = self._item()
        if not item:
            return {"charger_id": self._charger_id}
        return {
            "charger_id": self._charger_id,
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "address": item.get("address"),
            "operator": item.get("operator"),
            "status": item.get("status"),
            "available": item.get("available"),
            "total": item.get("total"),
            "max_power_kw": item.get("max_power_kw"),
            "energy_price_eur_kwh": item.get("energy_price_eur_kwh"),
            "distance_km": item.get("distance_km"),
            "open": item.get("open"),
        }
