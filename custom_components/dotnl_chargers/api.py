"""Async API client for DOT-NL / NDW charge-point GeoJSON and OCPI tariffs."""

from __future__ import annotations

import gzip
import json
import logging
import math
from typing import Any

import aiohttp

from .const import (
    GEOJSON_URL,
    KM_PER_DEG_LAT,
    MAX_BBOX_AREA_DEG2,
    TARIFFS_URL,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS84 points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def radius_to_bbox(
    latitude: float,
    longitude: float,
    radius_km: float,
    *,
    max_area_deg2: float = MAX_BBOX_AREA_DEG2,
) -> tuple[float, float, float, float]:
    """Derive a capped bbox (minLon, minLat, maxLon, maxLat) from centre + radius.

    The DOT-NL API rejects queries whose bbox area exceeds ``max_area_deg2``
    (default 1.0 deg²). When the requested radius would exceed that limit the
    half-extents are scaled down uniformly so the area equals the cap.
    """
    if radius_km <= 0:
        radius_km = 0.1

    cos_lat = max(math.cos(math.radians(latitude)), 0.01)
    deg_lat = radius_km / KM_PER_DEG_LAT
    deg_lon = radius_km / (KM_PER_DEG_LAT * cos_lat)

    area = (2.0 * deg_lat) * (2.0 * deg_lon)
    if area > max_area_deg2:
        scale = math.sqrt(max_area_deg2 / area)
        deg_lat *= scale
        deg_lon *= scale
        # Guard float drift so area never exceeds the API hard limit.
        area2 = (2.0 * deg_lat) * (2.0 * deg_lon)
        if area2 > max_area_deg2:
            shrink = math.sqrt(max_area_deg2 / area2) * 0.999999
            deg_lat *= shrink
            deg_lon *= shrink
        _LOGGER.debug(
            "Radius %.2f km capped to bbox area %.3f deg² (scale=%.3f)",
            radius_km,
            max_area_deg2,
            scale,
        )

    min_lon = longitude - deg_lon
    max_lon = longitude + deg_lon
    min_lat = latitude - deg_lat
    max_lat = latitude + deg_lat
    return (min_lon, min_lat, max_lon, max_lat)


def bbox_area_deg2(bbox: tuple[float, float, float, float]) -> float:
    """Return the area of a bbox in square degrees."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return abs(max_lon - min_lon) * abs(max_lat - min_lat)


def classify_status(available: int, total: int) -> str:
    """Map connector counts to available|partial|occupied|unknown."""
    if total <= 0:
        return "unknown"
    if available <= 0:
        return "occupied"
    if available >= total:
        return "available"
    return "partial"


def extract_energy_price(tariff: dict[str, Any]) -> float | None:
    """Lowest positive ENERGY price (EUR/kWh) on an OCPI tariff.

    Operators often publish a 0.0 ENERGY component as a placeholder next to
    the real rate. That zero must not win, or the cheapest sensor stays at
    0.0. A tariff that only has zeros is genuinely free and returns 0.0.
    """
    prices: list[float] = []
    for element in tariff.get("elements") or []:
        if not isinstance(element, dict):
            continue
        for component in element.get("price_components") or []:
            if not isinstance(component, dict) or component.get("type") != "ENERGY":
                continue
            price = component.get("price")
            if price is None:
                continue
            try:
                prices.append(float(price))
            except (TypeError, ValueError):
                continue
    positive = [price for price in prices if price > 0]
    if positive:
        return min(positive)
    if prices:
        return 0.0
    return None


class DotNLChargersApi:
    """Thin aiohttp wrapper around the NDW DOT-NL endpoints."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, application/geo+json, */*",
        }

    async def fetch_features(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[dict[str, Any]]:
        """ONE poll call: GeoJSON FeatureCollection within radius (capped bbox)."""
        bbox = radius_to_bbox(latitude, longitude, radius_km)
        params = {
            "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        }
        _LOGGER.debug(
            "Fetching DOT-NL features bbox=%s area=%.4f",
            params["bbox"],
            bbox_area_deg2(bbox),
        )
        async with self._session.get(
            GEOJSON_URL,
            params=params,
            headers=self._headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise DotNLApiError(
                    f"DOT-NL GeoJSON HTTP {response.status}: {text[:200]}"
                )
            payload = await response.json(content_type=None)
            features = payload.get("features") if isinstance(payload, dict) else None
            if not isinstance(features, list):
                raise DotNLApiError("DOT-NL response missing features list")
            return features

    async def fetch_tariffs(self) -> dict[str, float]:
        """Download OCPI tariffs gzip once; return {tariff_id: energy_eur_kwh}.

        Never call this inside the main poll hot-path — cache via Store and
        refresh every 6–12 h only.
        """
        _LOGGER.debug("Fetching OCPI tariffs from %s", TARIFFS_URL)
        async with self._session.get(
            TARIFFS_URL,
            headers=self._headers(),
            timeout=aiohttp.ClientTimeout(total=120),
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise DotNLApiError(
                    f"OCPI tariffs HTTP {response.status}: {text[:200]}"
                )
            raw = await response.read()

        try:
            if raw[:2] == b"\x1f\x8b":
                data = json.loads(gzip.decompress(raw))
            else:
                data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as err:
            raise DotNLApiError(f"Failed to decode tariffs: {err}") from err

        tariffs_list: list[dict[str, Any]] = []
        if isinstance(data, dict):
            # OCPI Tariff response shapes: {data: [...]} or {tariffs: [...]}
            for key in ("data", "tariffs", "Tariffs"):
                if isinstance(data.get(key), list):
                    tariffs_list = data[key]
                    break
            if not tariffs_list and "id" in data:
                tariffs_list = [data]
        elif isinstance(data, list):
            tariffs_list = data

        price_map: dict[str, float] = {}
        for tariff in tariffs_list:
            if not isinstance(tariff, dict):
                continue
            tid = tariff.get("id")
            if not tid:
                continue
            price = extract_energy_price(tariff)
            if price is not None:
                price_map[str(tid)] = price

        _LOGGER.info("Loaded %s OCPI ENERGY tariff prices", len(price_map))
        return price_map


class DotNLApiError(Exception):
    """Raised when the upstream DOT-NL / NDW API fails."""
