"""DataUpdateCoordinator for DOT-NL Chargers."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    DotNLApiError,
    DotNLChargersApi,
    classify_status,
    haversine_km,
)
from .cache import TariffCache
from .const import (
    ATTRIBUTION,
    CONF_ENABLE_TARIFF_ENRICHMENT,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MAX_MAP_MARKERS,
    CONF_MIN_AVAILABLE,
    CONF_POWER_MIN_KW,
    CONF_RADIUS_KM,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_ONLY_OPEN,
    DEFAULT_ENABLE_TARIFF_ENRICHMENT,
    DEFAULT_MAX_MAP_MARKERS,
    DEFAULT_MIN_AVAILABLE,
    DEFAULT_POWER_MIN_KW,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOW_ONLY_OPEN,
    DOMAIN,
    EVENT_ENTRY,
    EVENT_EXIT,
    HISTORY_MAX,
    ITEM_FIELDS,
    MIN_SCAN_INTERVAL,
    STATUS_AVAILABLE,
    STATUS_OCCUPIED,
    STATUS_PARTIAL,
)

_LOGGER = logging.getLogger(__name__)

# Shared tariff cache across entries (one Store, one download)
_SHARED_TARIFF_CACHE: TariffCache | None = None


def get_tariff_cache(hass: HomeAssistant) -> TariffCache:
    """Return the process-wide TariffCache singleton."""
    global _SHARED_TARIFF_CACHE
    if _SHARED_TARIFF_CACHE is None:
        _SHARED_TARIFF_CACHE = TariffCache(hass)
    return _SHARED_TARIFF_CACHE


def _option(entry: ConfigEntry, key: str, default: Any) -> Any:
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


class DotNLChargersCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator-first poller for DOT-NL charge points near a home location."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.consecutive_errors = 0
        self.last_good_data: dict[str, Any] | None = None
        self.last_update_status = "never"
        self.last_update_success_timestamp = None
        self._prev_ids: set[str] = set()
        self._history: list[dict[str, Any]] = []
        self._tariff_refresh_task = False

        scan = int(_option(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        scan = max(scan, MIN_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=scan),
            config_entry=entry,
        )

        session = async_get_clientsession(hass)
        self.api = DotNLChargersApi(session)
        self.tariff_cache = get_tariff_cache(hass)

    def _centre(self) -> tuple[float, float, float]:
        lat = float(
            _option(
                self.entry,
                CONF_LATITUDE,
                self.hass.config.latitude or 52.09,
            )
        )
        lon = float(
            _option(
                self.entry,
                CONF_LONGITUDE,
                self.hass.config.longitude or 5.12,
            )
        )
        radius = float(_option(self.entry, CONF_RADIUS_KM, DEFAULT_RADIUS_KM))
        return lat, lon, radius

    async def _async_maybe_refresh_tariffs(self) -> None:
        enable = bool(
            _option(
                self.entry,
                CONF_ENABLE_TARIFF_ENRICHMENT,
                DEFAULT_ENABLE_TARIFF_ENRICHMENT,
            )
        )
        if not enable:
            return
        await self.tariff_cache.async_load()
        if not self.tariff_cache.is_stale:
            return
        try:
            prices = await self.api.fetch_tariffs()
            await self.tariff_cache.async_save(prices)
        except Exception as err:  # noqa: BLE001 — background best-effort
            _LOGGER.warning("Tariff enrichment refresh failed: %s", err)

    def _feature_to_item(
        self,
        feature: dict[str, Any],
        centre_lat: float,
        centre_lon: float,
    ) -> dict[str, Any] | None:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if len(coords) < 2:
            return None

        lon, lat = float(coords[0]), float(coords[1])
        availabilities = props.get("availabilities") or []
        available = 0
        total = 0
        max_power_w = 0.0
        tariff_ids: list[str] = []
        connectors: list[dict[str, Any]] = []

        for avail in availabilities:
            if not isinstance(avail, dict):
                continue
            a = int(avail.get("available") or 0)
            t = int(avail.get("total") or 0)
            available += a
            total += t
            pw = float(avail.get("power_max") or 0.0)
            if pw > max_power_w:
                max_power_w = pw
            for tid in avail.get("tariff_ids") or []:
                if tid is not None:
                    tariff_ids.append(str(tid))
            connectors.append(
                {
                    "available": a,
                    "total": t,
                    "connector_type": avail.get("connector_type"),
                    "connector_format": avail.get("connector_format"),
                    "power_type": avail.get("power_type"),
                    "power_max_kw": round(pw / 1000.0, 2) if pw else 0.0,
                    "tariff_ids": [str(x) for x in (avail.get("tariff_ids") or [])],
                }
            )

        occupied = max(total - available, 0)
        status = classify_status(available, total)
        address = props.get("address") or "Unknown"
        operator = (
            props.get("operator_name")
            or props.get("suboperator_name")
            or props.get("owner_name")
            or "Unknown"
        )
        fid = str(feature.get("id") or f"{lat},{lon}")
        distance = round(haversine_km(centre_lat, centre_lon, lat, lon), 3)
        max_power_kw = round(max_power_w / 1000.0, 2) if max_power_w else 0.0
        energy_price = self.tariff_cache.lookup(tariff_ids)

        item = {
            "id": fid,
            "name": f"{operator} — {address}",
            "latitude": lat,
            "longitude": lon,
            "distance_km": distance,
            "address": address,
            "operator": operator,
            "cpo_id": props.get("cpo_id"),
            "open": bool(props.get("open")),
            "available": available,
            "total": total,
            "occupied": occupied,
            "status": status,
            "connectors": connectors,
            "max_power_kw": max_power_kw,
            "energy_price_eur_kwh": energy_price,
            "tariff_ids": tariff_ids,
            "last_updated": props.get("last_updated"),
        }
        # Whitelist enforcement
        return {k: item[k] for k in ITEM_FIELDS if k in item}

    def _apply_filters(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        min_available = int(
            _option(self.entry, CONF_MIN_AVAILABLE, DEFAULT_MIN_AVAILABLE)
        )
        power_min = float(_option(self.entry, CONF_POWER_MIN_KW, DEFAULT_POWER_MIN_KW))
        show_only_open = bool(
            _option(self.entry, CONF_SHOW_ONLY_OPEN, DEFAULT_SHOW_ONLY_OPEN)
        )

        filtered: list[dict[str, Any]] = []
        for item in items:
            if show_only_open and not item.get("open"):
                continue
            if item.get("available", 0) < min_available:
                continue
            if power_min > 0 and float(item.get("max_power_kw") or 0) < power_min:
                continue
            filtered.append(item)
        return filtered

    def _build_payload(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        items_sorted = sorted(items, key=lambda x: x.get("distance_km", 9999))

        available_n = sum(1 for i in items_sorted if i["status"] == STATUS_AVAILABLE)
        occupied_n = sum(1 for i in items_sorted if i["status"] == STATUS_OCCUPIED)
        partial_n = sum(1 for i in items_sorted if i["status"] == STATUS_PARTIAL)
        connectors_free = sum(int(i.get("available") or 0) for i in items_sorted)
        connectors_total = sum(int(i.get("total") or 0) for i in items_sorted)

        closest = next(
            (
                i
                for i in items_sorted
                if i["status"] in (STATUS_AVAILABLE, STATUS_PARTIAL)
                and int(i.get("available") or 0) > 0
            ),
            None,
        )

        priced = [
            i
            for i in items_sorted
            if i.get("energy_price_eur_kwh") is not None
            and int(i.get("available") or 0) > 0
        ]
        cheapest = (
            min(priced, key=lambda x: float(x["energy_price_eur_kwh"]))
            if priced
            else None
        )

        current_ids = {i["id"] for i in items_sorted}
        entered_ids = current_ids - self._prev_ids
        exited_ids = self._prev_ids - current_ids
        entered = [i for i in items_sorted if i["id"] in entered_ids]
        exited = [{"id": eid} for eid in exited_ids]

        for item in entered:
            self.hass.bus.async_fire(EVENT_ENTRY, {"item": item})
        for eid in exited_ids:
            self.hass.bus.async_fire(EVENT_EXIT, {"id": eid})

        # History: merge by id, newest first, cap HISTORY_MAX
        combined = {i["id"]: i for i in (items_sorted + self._history)}
        history = list(combined.values())
        history.sort(key=lambda x: x.get("last_updated") or "", reverse=True)
        self._history = history[:HISTORY_MAX]
        self._prev_ids = current_ids

        max_markers = int(
            _option(self.entry, CONF_MAX_MAP_MARKERS, DEFAULT_MAX_MAP_MARKERS)
        )
        tracked = items_sorted[: max(0, max_markers)]

        return {
            "items": items_sorted,
            "total": len(items_sorted),
            "counts": {
                "available": available_n,
                "occupied": occupied_n,
                "partial": partial_n,
                "connectors_free": connectors_free,
                "connectors_total": connectors_total,
            },
            "closest": closest,
            "cheapest": cheapest,
            "entered": entered,
            "exited": exited,
            "history": list(self._history),
            "tracked": tracked,
            "attribution": ATTRIBUTION,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        await self._async_maybe_refresh_tariffs()

        lat, lon, radius = self._centre()
        try:
            features = await self.api.fetch_features(lat, lon, radius)
            items_raw: list[dict[str, Any]] = []
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                item = self._feature_to_item(feature, lat, lon)
                # Distance filter (bbox is rectangle; keep true circle)
                if (
                    item is not None
                    and float(item.get("distance_km") or 0) <= radius + 0.05
                ):
                    items_raw.append(item)

            items = self._apply_filters(items_raw)
            payload = self._build_payload(items)

            self.consecutive_errors = 0
            self.last_good_data = payload
            self.last_update_status = "ok"
            self.last_update_success_timestamp = dt_util.utcnow()
            return payload

        except (DotNLApiError, TimeoutError, OSError) as err:
            self.consecutive_errors += 1
            self.last_update_status = f"error: {err}"
            _LOGGER.warning(
                "DOT-NL update failed (%s consecutive): %s",
                self.consecutive_errors,
                err,
            )
            if self.last_good_data is not None:
                return self.last_good_data
            raise UpdateFailed(str(err)) from err
