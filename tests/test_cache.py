"""Tariff Store cache: version migrate + soft-fail load."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.dotnl_chargers.cache import (
    STORAGE_KEY,
    STORAGE_VERSION,
    TariffCache,
)


@pytest.mark.asyncio
async def test_tariff_cache_migrates_v1_to_v2(hass, hass_storage):
    """A v1 on-disk store must load under STORAGE_VERSION=2 without crashing."""
    assert STORAGE_VERSION == 2
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {
            "version": "0.1.3",
            "fetched_at": 1700000000.0,
            "prices": {"t-sample": 0.42, "t-cheap": 0.21},
        },
    }

    cache = TariffCache(hass)
    await cache.async_load()

    assert cache.prices == {"t-sample": 0.42, "t-cheap": 0.21}
    assert cache.lookup(["t-cheap", "t-sample"]) == 0.21
    # Migrated file rewritten at the current major version
    assert hass_storage[STORAGE_KEY]["version"] == STORAGE_VERSION
    assert hass_storage[STORAGE_KEY]["data"]["prices"]["t-sample"] == 0.42


@pytest.mark.asyncio
async def test_tariff_cache_load_failure_is_soft(hass):
    """Store load/migration errors must not abort config-entry setup."""
    cache = TariffCache(hass)
    with (
        patch.object(
            cache._store, "async_load", side_effect=NotImplementedError
        ),
        patch.object(
            cache._store, "async_remove", new_callable=AsyncMock
        ) as mock_remove,
    ):
        await cache.async_load()

    assert cache.prices == {}
    assert cache._loaded is True
    mock_remove.assert_awaited_once()
    # Second call is a no-op (already marked loaded)
    await cache.async_load()
    assert cache.prices == {}


@pytest.mark.asyncio
async def test_tariff_cache_roundtrip(hass, hass_storage):
    """Fresh save then load preserves prices."""
    cache = TariffCache(hass)
    await cache.async_save({"t-a": 0.35, "t-b": 0.50})
    assert cache.prices == {"t-a": 0.35, "t-b": 0.50}

    cache2 = TariffCache(hass)
    await cache2.async_load()
    assert cache2.prices == {"t-a": 0.35, "t-b": 0.50}
    assert hass_storage[STORAGE_KEY]["version"] == STORAGE_VERSION
