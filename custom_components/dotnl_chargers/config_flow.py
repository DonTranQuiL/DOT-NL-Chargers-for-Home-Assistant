"""Config and options flow for DOT-NL Chargers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ENABLE_MAP_TRACKERS,
    CONF_ENABLE_TARIFF_ENRICHMENT,
    CONF_INSTANCE_NAME,
    CONF_MAX_MAP_MARKERS,
    CONF_MIN_AVAILABLE,
    CONF_POWER_MIN_KW,
    CONF_RADIUS_KM,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_ONLY_OPEN,
    DEFAULT_ENABLE_MAP_TRACKERS,
    DEFAULT_ENABLE_TARIFF_ENRICHMENT,
    DEFAULT_MAX_MAP_MARKERS,
    DEFAULT_MIN_AVAILABLE,
    DEFAULT_POWER_MIN_KW,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOW_ONLY_OPEN,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    NAME,
)


def _unique_id(lat: float, lon: float, radius: float) -> str:
    return f"{DOMAIN}_{lat:.4f}_{lon:.4f}_{radius:.2f}"


class DotNLChargersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DOT-NL Chargers."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        hass_lat = self.hass.config.latitude or 52.0907
        hass_lon = self.hass.config.longitude or 5.1214

        if user_input is not None:
            lat = float(user_input.get(CONF_LATITUDE, hass_lat))
            lon = float(user_input.get(CONF_LONGITUDE, hass_lon))
            radius = float(user_input.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))
            instance = (user_input.get(CONF_INSTANCE_NAME) or "").strip() or NAME

            await self.async_set_unique_id(_unique_id(lat, lon, radius))
            self._abort_if_unique_id_configured()

            data = {
                CONF_INSTANCE_NAME: instance,
                CONF_LATITUDE: lat,
                CONF_LONGITUDE: lon,
                CONF_RADIUS_KM: radius,
            }
            options = {
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_RADIUS_KM: radius,
                CONF_MIN_AVAILABLE: DEFAULT_MIN_AVAILABLE,
                CONF_POWER_MIN_KW: DEFAULT_POWER_MIN_KW,
                CONF_ENABLE_MAP_TRACKERS: DEFAULT_ENABLE_MAP_TRACKERS,
                CONF_ENABLE_TARIFF_ENRICHMENT: DEFAULT_ENABLE_TARIFF_ENRICHMENT,
                CONF_MAX_MAP_MARKERS: DEFAULT_MAX_MAP_MARKERS,
                CONF_SHOW_ONLY_OPEN: DEFAULT_SHOW_ONLY_OPEN,
            }
            return self.async_create_entry(
                title=f"{NAME} ({instance})",
                data=data,
                options=options,
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_INSTANCE_NAME, default=NAME): str,
                vol.Optional(
                    CONF_LATITUDE, default=hass_lat
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-90,
                        max=90,
                        step=0.0001,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_LONGITUDE, default=hass_lon
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-180,
                        max=180,
                        step=0.0001,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=50,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return DotNLChargersOptionsFlow()


class DotNLChargersOptionsFlow(config_entries.OptionsFlow):
    """Handle options for DOT-NL Chargers."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            scan = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
            user_input[CONF_SCAN_INTERVAL] = max(scan, MIN_SCAN_INTERVAL)
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        data = self.config_entry.data

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=3600,
                        step=30,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    CONF_RADIUS_KM,
                    default=opts.get(
                        CONF_RADIUS_KM, data.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=50,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="km",
                    )
                ),
                vol.Optional(
                    CONF_MIN_AVAILABLE,
                    default=opts.get(CONF_MIN_AVAILABLE, DEFAULT_MIN_AVAILABLE),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=50,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_POWER_MIN_KW,
                    default=opts.get(CONF_POWER_MIN_KW, DEFAULT_POWER_MIN_KW),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=350,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="kW",
                    )
                ),
                vol.Optional(
                    CONF_ENABLE_MAP_TRACKERS,
                    default=opts.get(
                        CONF_ENABLE_MAP_TRACKERS, DEFAULT_ENABLE_MAP_TRACKERS
                    ),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_TARIFF_ENRICHMENT,
                    default=opts.get(
                        CONF_ENABLE_TARIFF_ENRICHMENT,
                        DEFAULT_ENABLE_TARIFF_ENRICHMENT,
                    ),
                ): bool,
                vol.Optional(
                    CONF_MAX_MAP_MARKERS,
                    default=opts.get(CONF_MAX_MAP_MARKERS, DEFAULT_MAX_MAP_MARKERS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Optional(
                    CONF_SHOW_ONLY_OPEN,
                    default=opts.get(CONF_SHOW_ONLY_OPEN, DEFAULT_SHOW_ONLY_OPEN),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
