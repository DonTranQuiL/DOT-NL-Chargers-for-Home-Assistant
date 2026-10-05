"""Persistent Store cache for OCPI tariff ENERGY prices."""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, TARIFF_REFRESH_SECONDS, VERSION

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = f"{DOMAIN}.tariffs"
STORAGE_VERSION = 2


class _TariffStore(Store[dict[str, Any]]):
    """Store with a no-op major-version migrate (payload shape unchanged)."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Migrate on-disk tariff cache to the current storage version.

        STORAGE_VERSION was bumped 1 → 2 without changing the payload shape
        ({version, fetched_at, prices}). Return the old data unchanged so HA
        can rewrite the file at the new version instead of raising
        NotImplementedError and aborting config-entry setup.
        """
        _LOGGER.info(
            "Migrating %s storage from %s.%s to %s.%s (payload unchanged)",
            self.key,
            old_major_version,
            old_minor_version,
            self.version,
            self.minor_version,
        )
        if not isinstance(old_data, dict):
            return {}
        return old_data


class TariffCache:
    """Background Store-backed map of tariff_id → energy_price_eur_kwh."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = _TariffStore(
            hass, STORAGE_VERSION, STORAGE_KEY
        )
        self._prices: dict[str, float] = {}
        self._fetched_at: float = 0.0
        self._loaded = False

    @property
    def prices(self) -> dict[str, float]:
        return self._prices

    @property
    def is_stale(self) -> bool:
        if not self._prices:
            return True
        return (time.time() - self._fetched_at) >= TARIFF_REFRESH_SECONDS

    async def async_load(self) -> None:
        """Load prices from HA Store (once per process).

        Never raises: a corrupt or unreadable store must not block setup.
        """
        if self._loaded:
            return
        try:
            data = await self._store.async_load()
        except Exception:  # noqa: BLE001 — cache must never kill setup
            _LOGGER.warning(
                "Failed to load tariff cache %s; starting empty "
                "(delete .storage/%s to force a clean rebuild)",
                STORAGE_KEY,
                STORAGE_KEY,
                exc_info=True,
            )
            try:
                await self._store.async_remove()
            except Exception:  # noqa: BLE001
                _LOGGER.debug(
                    "Could not remove broken tariff store %s",
                    STORAGE_KEY,
                    exc_info=True,
                )
            self._prices = {}
            self._fetched_at = 0.0
            self._loaded = True
            return

        self._loaded = True
        if not data:
            return
        prices = data.get("prices") or {}
        if isinstance(prices, dict):
            self._prices = {
                str(k): float(v) for k, v in prices.items() if v is not None
            }
        try:
            self._fetched_at = float(data.get("fetched_at") or 0.0)
        except (TypeError, ValueError):
            self._fetched_at = 0.0
        _LOGGER.debug(
            "Tariff cache loaded: %s prices, age=%.0fs",
            len(self._prices),
            time.time() - self._fetched_at if self._fetched_at else -1,
        )

    async def async_save(self, prices: dict[str, float]) -> None:
        """Persist a fresh price map."""
        self._prices = dict(prices)
        self._fetched_at = time.time()
        await self._store.async_save(
            {
                "version": VERSION,
                "fetched_at": self._fetched_at,
                "prices": self._prices,
            }
        )
        _LOGGER.debug("Tariff cache saved: %s prices", len(self._prices))

    def lookup(self, tariff_ids: list[str] | None) -> float | None:
        """Return the lowest ENERGY price among known tariff_ids."""
        if not tariff_ids or not self._prices:
            return None
        found: list[float] = []
        for tid in tariff_ids:
            price = self._prices.get(str(tid))
            if price is not None:
                found.append(price)
        if not found:
            return None
        return min(found)
