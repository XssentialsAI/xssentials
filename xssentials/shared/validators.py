"""Vendor-agnostic input validators.

`check_payload_size` defends against Claude Code stdio bug #36319 (silent drop
above ~766B-1109B threshold). Tool wrappers call this at function entry and
surface the rejection as a Markdown error so the bug becomes a visible failure
instead of a hang.

`enforce_get_only` is the wrapper-layer read-only boundary used by gateway-
shaped tools (`cw_query`, `dt_query`, …).
"""

from __future__ import annotations

import json

PAYLOAD_MAX_BYTES = 750  # below the observed stdio threshold


def check_payload_size(args: dict, max_bytes: int = PAYLOAD_MAX_BYTES) -> None:
    """Raise ValueError if the JSON-serialized arg dict exceeds the stdio threshold.

    Names the offending arg (the one whose value is largest) so the error is
    actionable, not just "payload too big."
    """
    serialized = json.dumps(args, default=str)
    size = len(serialized.encode("utf-8"))
    if size <= max_bytes:
        return
    largest = max(args.items(), key=lambda kv: len(json.dumps(kv[1], default=str)))
    raise ValueError(
        f"Tool args payload {size}B exceeds {max_bytes}B stdio safety limit. "
        f"Largest offender: `{largest[0]}` "
        f"({len(json.dumps(largest[1], default=str))}B). Tighten filters and retry."
    )


def enforce_get_only(method: str) -> None:
    """Read-only boundary for gateway tools. Raises on anything but GET."""
    if method.upper() != "GET":
        raise ValueError(
            f"Gateway tool is GET-only (read-only). Got: {method!r}. "
            "Write methods require explicit role-flip + per-call confirmation."
        )
