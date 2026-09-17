#!/usr/bin/env python3
"""AI dependency updater — inspects requirements* for DOT-NL Chargers."""
from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

COMPONENT = "custom_components/dotnl_chargers/"


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


files = {
    "requirements.txt": Path("requirements.txt").read_text(encoding="utf-8")
    if Path("requirements.txt").exists()
    else "",
    "requirements_test.txt": Path("requirements_test.txt").read_text(encoding="utf-8")
    if Path("requirements_test.txt").exists()
    else "",
    "manifest.json": Path(f"{COMPONENT}manifest.json").read_text(encoding="utf-8")
    if Path(f"{COMPONENT}manifest.json").exists()
    else "",
}

client, model = _llm_client()
prompt = f"""
Suggest safe dependency bumps for DOT-NL Chargers ({COMPONENT}).
Prefer empty runtime requirements (HA built-ins). Update test deps carefully.

Current files:
{files}

If changing a file, emit FILEPATH + CODE whole-file overwrite markers.
Otherwise print NO_CHANGES.
"""
try:
    completion = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    print(completion.choices[0].message.content or "")
except Exception as exc:  # noqa: BLE001
    print(f"dependency_updater failed: {exc}")
