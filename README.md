<div align="center">

# DOT-NL Chargers

**Home Assistant custom integration for Dutch EV charge-point availability via DOT-NL / NDW AFIR open data.**

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA](https://img.shields.io/badge/Home%20Assistant-2025.1.0+-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/releases)
[![Issues](https://img.shields.io/github/issues/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/issues)

</div>

## Features

- Live GeoJSON poll of nearby charge points (one HTTP call per cycle)
- Occupancy sensors: available / occupied / free connectors / totals
- Closest available + cheapest EUR/kWh (OCPI ENERGY tariffs, cached 6h+)
- Optional map `device_tracker` pins (stale force-remove ~45 min)
- Lovelace card (`dotnl_chargers-card`) with filters / sort / expandable rows
- Defensive polling with `consecutive_errors` + last-good-data fallback
- Dutch + English UI translations

## Install (HACS custom repository)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. URL: `https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant`
3. Category: **Integration**
4. Download **DOT-NL Chargers**, then restart Home Assistant
5. Settings → Devices & services → Add Integration → **DOT-NL Chargers**

## Lovelace card

Copy the card into your HA config www folder:

```bash
cp dotnl_chargers-card.js /config/www/dotnl_chargers-card.js
```

Then add a Lovelace resource:

- URL: `/local/dotnl_chargers-card.js`
- Type: JavaScript Module

Card config example:

```yaml
type: custom:dotnl_chargers-card
entity: sensor.dot_nl_chargers_overview
title: Chargers near home
```

## Recorder tip

The overview sensor carries fat attributes (`items`, `history`, …). Exclude it from the recorder to keep the database lean:

```yaml
recorder:
  exclude:
    entities:
      - sensor.dot_nl_chargers_overview
```

(Adjust the entity id to match your instance.)

## Options

| Option | Default | Notes |
|--------|---------|-------|
| `scan_interval` | 120 s | Minimum 60 |
| `radius_km` | 2.0 | Bbox area capped at 1.0 deg² by API |
| `min_available` | 0 | Filter stations |
| `power_min_kw` | 0 | Filter by max connector power |
| `enable_map_trackers` | true | GPS pins |
| `enable_tariff_enrichment` | true | Background OCPI gzip (not in poll hot-path) |
| `max_map_markers` | 40 | Cap tracker entities |
| `show_only_open` | false | Filter `open` flag |

## Entities

| Entity | Role |
|--------|------|
| `sensor.*_overview` | Free connectors + fat attrs |
| `sensor.*_available_stations` | Count |
| `sensor.*_occupied_stations` | Count |
| `sensor.*_free_connectors` | Count |
| `sensor.*_total_connectors` | Count |
| `sensor.*_closest_available` | Distance km |
| `sensor.*_cheapest_energy_price` | EUR/kWh |
| `sensor.*_consecutive_errors` | Diagnostic |
| `sensor.*_last_update_status` | Diagnostic |
| `sensor.*_last_update_time` | Diagnostic timestamp |
| `device_tracker.*` | Map pins (optional) |
| `button.*_refresh` | Manual refresh |

## Disclaimer

DOT-NL / AFIR charge-point data is **free open data** published by **NDW** (Nationaal Dataportaal Wegverkeer). This integration is unofficial, not affiliated with NDW or any CPO. Availability and tariffs may be delayed or incomplete — always verify on-site before relying on a connector.

**Credit:** NDW open data — [dotnl.ndw.nu](https://dotnl.ndw.nu) / [opendata.ndw.nu](https://opendata.ndw.nu).

## License

MIT © DonTranQuiL
