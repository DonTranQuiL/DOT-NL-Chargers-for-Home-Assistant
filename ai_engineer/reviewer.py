#!/usr/bin/env python3
"""AI PR reviewer focused on custom_components/dotnl_chargers/."""
from __future__ import annotations

import os
import subprocess

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


def _diff() -> str:
    try:
        out = subprocess.check_output(
            ["git", "diff", "origin/main...HEAD", "--", COMPONENT],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out[-12000:]
    except Exception:
        try:
            return subprocess.check_output(
                ["git", "diff", "HEAD~1", "--", COMPONENT], text=True
            )[-12000:]
        except Exception as exc:
            return f"(no diff: {exc})"


client, model = _llm_client()
diff = _diff()
pr = os.getenv("PR_NUMBER")
repo = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_TOKEN")

prompt = f"""
Review this Home Assistant custom integration PR for DOT-NL Chargers.
Focus on {COMPONENT}: async aiohttp only, coordinator-first, no live network in tests,
bbox caps, unique_ids, has_entity_name, HA 2025.1 patterns.

DIFF:
{diff}

Write a concise PR review comment with findings and severity.
"""

try:
    completion = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    body = completion.choices[0].message.content or ""
    print(body)
    if pr and repo and token:
        import requests

        requests.post(
            f"https://api.github.com/repos/{repo}/issues/{pr}/comments",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"body": f"**AI Review**\n\n{body}"},
            timeout=30,
        )
except Exception as exc:  # noqa: BLE001
    print(f"Review failed: {exc}")
