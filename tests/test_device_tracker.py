"""Device tracker listener lifecycle tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.dotnl_chargers.const import CONF_ENABLE_MAP_TRACKERS, DOMAIN
from custom_components.dotnl_chargers.device_tracker import async_setup_entry


@pytest.mark.asyncio
async def test_listener_unsubscribed_on_unload(hass: HomeAssistant) -> None:
    """The coordinator listener must be released when the entry unloads."""
    unsub = MagicMock()
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.async_add_listener = MagicMock(return_value=unsub)

    entry = MagicMock()
    entry.entry_id = "abc"
    entry.data = {}
    entry.options = {CONF_ENABLE_MAP_TRACKERS: False}
    hass.data[DOMAIN] = {"abc": coordinator}

    await async_setup_entry(hass, entry, MagicMock())

    coordinator.async_add_listener.assert_called_once()
    entry.async_on_unload.assert_called_once_with(unsub)
