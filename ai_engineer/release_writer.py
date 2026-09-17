#!/usr/bin/env python3
"""AI release notes writer for DOT-NL Chargers."""
from __future__ import annotations

import os
import subprocess

from openai import OpenAI


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


def _log() -> str:
    try:
        return subprocess.check_output(
            ["git", "log", "-20", "--oneline"], text=True
        )
    except Exception as exc:
        return str(exc)


client, model = _llm_client()
tag = os.getenv("RELEASE_TAG", "0.1.0")
prompt = f"""
Write GitHub release notes for DOT-NL Chargers tag {tag}.
Domain: dotnl_chargers. Highlight sensors, trackers, tariff cache, Lovelace card.
Keep markdown. Commits:\n{_log()}
"""
try:
    completion = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    notes = completion.choices[0].message.content or ""
    print(notes)
    with open("release_notes.md", "w", encoding="utf-8") as fh:
        fh.write(notes)
except Exception as exc:  # noqa: BLE001
    print(f"release_writer failed: {exc}")
