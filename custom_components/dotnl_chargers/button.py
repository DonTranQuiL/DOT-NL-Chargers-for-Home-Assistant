"""Button platform — manual refresh for DOT-NL Chargers."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_INSTANCE_NAME, DOMAIN, MANUFACTURER, NAME
from .coordinator import DotNLChargersCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotNLChargersCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DotNLRefreshButton(coordinator, entry)])


class DotNLRefreshButton(ButtonEntity):
    """Force a coordinator refresh."""

    _attr_has_entity_name = True
    _attr_name = "Refresh"
    _attr_icon = "mdi:refresh"

    def __init__(
        self, coordinator: DotNLChargersCoordinator, entry: ConfigEntry
    ) -> None:
        self.coordinator = coordinator
        self._entry = entry
        instance = entry.data.get(CONF_INSTANCE_NAME, NAME)
        self._attr_unique_id = f"{DOMAIN}_refresh_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{NAME} ({instance})",
            manufacturer=MANUFACTURER,
            model="DOT-NL / NDW AFIR Open Data",
            configuration_url=(
                "https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant"
            ),
        )

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
