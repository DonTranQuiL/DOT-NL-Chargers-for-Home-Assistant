#!/usr/bin/env python3
"""AI self-heal: whole-file overwrite via FILEPATH + CODE markers."""
from __future__ import annotations

import os
import re

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


try:
    with open("failed_logs.txt", encoding="utf-8") as fh:
        logs = fh.read()[-4000:]
except FileNotFoundError:
    print("No failed_logs.txt found. Exiting.")
    raise SystemExit(0)

match = re.search(r"(?:-->\s+)?([a-zA-Z0-9_./\-]+(?:\.py|\.json|\.yaml))", logs)
file_path = match.group(1) if match else None
file_content = "File content could not be loaded."
if file_path and os.path.isfile(file_path):
    with open(file_path, encoding="utf-8") as fh:
        file_content = fh.read()

client, model = _llm_client()
prompt = f"""
You are the AI repair agent for DOT-NL Chargers ({COMPONENT}).
Fix the broken file using a FULL file overwrite.

Broken file: {file_path}

CODE:
{file_content}

ERROR LOG:
{logs}

Your response MUST start with:
FILEPATH: <path>
Then a short explanation.
Then:
CODE:
```python
<entire fixed file>
```
"""

try:
    completion = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    response_text = completion.choices[0].message.content or ""
    print(response_text)

    target_file = None
    code_lines: list[str] = []
    in_code = False
    for line in response_text.splitlines():
        if line.startswith("FILEPATH:"):
            target_file = line.replace("FILEPATH:", "", 1).strip()
        elif line.startswith("CODE:"):
            in_code = True
            continue
        elif in_code and line.strip().startswith("```"):
            if code_lines:
                break
            continue
        elif in_code:
            code_lines.append(line)

    if target_file and code_lines:
        with open(target_file, "w", encoding="utf-8") as fh:
            fh.write("\n".join(code_lines) + "\n")
        print(f"Patched {target_file}")
    else:
        print("Failed to parse FILEPATH/CODE markers.")
except Exception as exc:  # noqa: BLE001
    print(f"Repair failed: {exc}")
