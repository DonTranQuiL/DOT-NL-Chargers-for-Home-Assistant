#!/usr/bin/env python3
"""AI test writer for DOT-NL Chargers — mocks network, no live I/O."""
from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

COMPONENT = "custom_components/dotnl_chargers/"
TESTS = "tests/"


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


def _list_files() -> str:
    lines = []
    for base in (COMPONENT, TESTS):
        root = Path(base)
        if root.exists():
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    lines.append(str(p))
    return "\n".join(lines)


client, model = _llm_client()
prompt = f"""
Write additional pytest tests for DOT-NL Chargers.
Rules: AsyncMock network only, fixtures from GeoJSON sample, cover bbox math,
occupancy, UpdateFailed+last_good_data, config flow, sensor state. No live I/O.

Files:
{_list_files()}

Output FILEPATH + CODE whole-file overwrite markers for any new/updated test file
under {TESTS}.
"""

try:
    completion = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    text = completion.choices[0].message.content or ""
    print(text)
    target = None
    code: list[str] = []
    in_code = False
    for line in text.splitlines():
        if line.startswith("FILEPATH:"):
            if target and code:
                Path(target).write_text("\n".join(code) + "\n", encoding="utf-8")
            target = line.replace("FILEPATH:", "", 1).strip()
            code, in_code = [], False
        elif line.startswith("CODE:"):
            in_code = True
        elif in_code and line.strip().startswith("```"):
            if code:
                in_code = False
            continue
        elif in_code:
            code.append(line)
    if target and code:
        Path(target).write_text("\n".join(code) + "\n", encoding="utf-8")
        print(f"Wrote {target}")
except Exception as exc:  # noqa: BLE001
    print(f"test_writer failed: {exc}")
