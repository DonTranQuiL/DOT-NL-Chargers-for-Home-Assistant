#!/usr/bin/env python3
"""AI issue resolver — proposes whole-file patches with FILEPATH + CODE."""
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


def _snapshot() -> str:
    root = Path(COMPONENT)
    parts: list[str] = []
    if not root.exists():
        return "(component missing)"
    for path in sorted(root.rglob("*.py")):
        parts.append(f"\n===== {path} =====\n{path.read_text(encoding='utf-8')[:4000]}")
    return "\n".join(parts)[-20000:]


issue_title = os.getenv("ISSUE_TITLE", "")
issue_body = os.getenv("ISSUE_BODY", "")
client, model = _llm_client()

prompt = f"""
Resolve this GitHub issue for DOT-NL Chargers by proposing full-file overwrites.

Title: {issue_title}
Body: {issue_body}

Current component snapshot:
{_snapshot()}

For each changed file output:
FILEPATH: <path>
CODE:
```python
<entire file>
```
Only touch files under {COMPONENT} or tests/.
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
                print(f"Wrote {target}")
            target = line.replace("FILEPATH:", "", 1).strip()
            code = []
            in_code = False
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
    print(f"Issue resolver failed: {exc}")
