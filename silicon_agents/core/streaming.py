"""Helpers for server-sent events."""

from __future__ import annotations

import json
from typing import Any


def sse_event(event_type: str, payload: dict[str, Any]) -> str:
    body = json.dumps({"type": event_type, "payload": payload})
    return f"data: {body}\n\n"

