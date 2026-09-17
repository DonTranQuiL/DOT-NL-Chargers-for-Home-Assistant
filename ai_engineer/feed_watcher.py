#!/usr/bin/env python3
"""Watch DOT-NL / NDW open-data feeds for schema drift (AI summariser)."""
from __future__ import annotations

import os

import requests
from openai import OpenAI

COMPONENT = "custom_components/dotnl_chargers/"
GEOJSON_SAMPLE = (
    "https://dotnl.ndw.nu/api/rest/geojson/dynamic-road-status/"
    "charge-point-data/v1/features?bbox=5.1,52.08,5.15,52.11"
)


def _llm_client():
    xai = os.getenv("XAI_API_KEY")
    if xai:
        return OpenAI(base_url="https://api.x.ai/v1", api_key=xai), "grok-4"
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        return (
            OpenAI(base_url="https://openrouter.ai/api/v1", api_key=or_key),
            "openai/gpt-4o-mini",
        )
    print("No XAI_API_KEY or OPENROUTER_API_KEY — exiting cleanly.")
    raise SystemExit(0)


headers = {"User-Agent": "HomeAssistant-DotNL-Chargers/0.1.0-feed-watcher"}
snippet = ""
try:
    resp = requests.get(GEOJSON_SAMPLE, headers=headers, timeout=30)
    snippet = resp.text[:3000]
    print(f"Feed HTTP {resp.status_code}, bytes={len(resp.content)}")
except Exception as exc:  # noqa: BLE001
    print(f"Feed fetch failed: {exc}")
    raise SystemExit(0)

client, model = _llm_client()
memory = ""
mem_path = ".memory/dotnl_geojson_schema.json"
if os.path.isfile(mem_path):
    with open(mem_path, encoding="utf-8") as fh:
        memory = fh.read()[:2000]

prompt = f"""
Compare this live DOT-NL GeoJSON snippet to the remembered schema.
Flag breaking field changes relevant to {COMPONENT}.

SCHEMA MEMORY:
{memory}

LIVE SNIPPET:
{snippet}
"""
try:
    completion = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    report = completion.choices[0].message.content or ""
    print(report)
    with open("feed_watch_report.md", "w", encoding="utf-8") as fh:
        fh.write(report)
except Exception as exc:  # noqa: BLE001
    print(f"feed_watcher failed: {exc}")
