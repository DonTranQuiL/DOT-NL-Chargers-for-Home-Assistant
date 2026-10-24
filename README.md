<div align="center">

# DOT-NL Chargers

**Home Assistant custom integration for Dutch EV charge-point availability via DOT-NL / NDW AFIR open data.**

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA](https://img.shields.io/badge/Home%20Assistant-2025.1.0+-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/releases)
[![Issues](https://img.shields.io/github/issues/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/issues)
[![Home Assistant CI](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/hass-ci.yml?label=Home%20Assistant%20CI&style=for-the-badge)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/actions/workflows/hass-ci.yml)
[![Code Checks](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/codechecker.yml?style=for-the-badge&label=CODE%20CHECKS&color=5dbb0f)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/actions)
[![Tests](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/pytest.yml?style=for-the-badge&label=TESTS&color=5dbb0f)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/actions)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/hacs.yaml?style=for-the-badge&label=HACS%20VALIDATION&color=5dbb0f)](https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant/actions)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=for-the-badge)](https://github.com/astral-sh/ruff)
[![Maintainer](https://img.shields.io/badge/maintainer-%40DonTranQuiL-007ec6?style=for-the-badge)](https://github.com/DonTranQuiL)
[![Donate](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-ffdd00?style=for-the-badge)](https://ko-fi.com/DonTranQuiL)
[![Liberapay patrons](https://img.shields.io/liberapay/patrons/Malosaaa.svg?logo=liberapay&style=for-the-badge)](https://liberapay.com/Malosaaa/donate)
[![Liberapay goal](https://img.shields.io/liberapay/goal/Malosaaa.svg?logo=liberapay&style=for-the-badge)](https://liberapay.com/Malosaaa/donate)
<a href="https://liberapay.com/Malosaaa/donate"><img alt="Donate using Liberapay" src="https://liberapay.com/assets/widgets/donate.svg"></a>
[![Discord](https://img.shields.io/badge/Discord-join%20community-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/qaHPTTKHae)

</div>

## Features

- Live GeoJSON poll of nearby charge points (one HTTP call per cycle)
- Occupancy sensors: available / occupied / free connectors / totals
- Closest available + cheapest EUR/kWh (OCPI ENERGY tariffs, cached 6h+)
- Optional map `device_tracker` pins (stale force-remove ~45 min)
- Lovelace card (`dotnl_chargers-card`) with filters / sort / expandable rows
- Defensive polling with `consecutive_errors` + last-good-data fallback
- Dutch + English UI translations

## Install (HACS)

**DOT-NL Chargers** is submitted to the **HACS default list**, so you can install it straight from the HACS store:

1. Open **HACS** in your sidebar and search for **DOT-NL Chargers**.
2. Open it and click **Download**.
3. **Restart Home Assistant.**
4. Settings → Devices & services → Add Integration → **DOT-NL Chargers**

<details>
<summary>Fallback: add as a custom repository</summary>

If DOT-NL Chargers does not show up in the HACS search (yet), click the three dots (⋮) in the top right of HACS → **Custom repositories**, paste `https://github.com/DonTranQuiL/DOT-NL-Chargers-for-Home-Assistant` with category **Integration**, click **Add**, then continue with step 2.

</details>

## Lovelace card

The card ships with the integration and is loaded automatically, so there is nothing to copy and no resource to add. After installing (or updating) the integration and restarting Home Assistant, do a hard refresh of your browser and add the card to a dashboard.

If you copied `dotnl_chargers-card.js` to `/config/www/` and added a `/local/dotnl_chargers-card.js` resource with an earlier version, remove that resource under **Settings → Dashboards → Resources** and delete the old file.

Card config example:

<img width="768" height="813" alt="CARD" src="https://github.com/user-attachments/assets/09e7d148-cf22-41b3-9884-b4b476e906e7" />



```yaml
type: grid
cards:
  - type: heading
    heading: New section
  - type: custom:dotnl_chargers-card
    entity: sensor.dot_nl_chargers_home_overview
    title: Chargers near home
    layout_options:
      grid_columns: full
column_span: 2

```

The entity id is based on the name you gave the entry: an entry named **Home** gives `sensor.dot_nl_chargers_home_overview`. Check **Settings → Devices & services → DOT-NL Chargers** for yours.

## Recorder

The overview sensor's large attributes (`items`, `history`, `entered`, `exited`) are excluded from the recorder automatically, so no `configuration.yaml` changes are needed.

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

## Built by AI

This integration was created entirely by AI and is maintained by AI.

## License

MIT © DonTranQuiL
