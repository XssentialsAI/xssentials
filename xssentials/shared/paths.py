"""Shared filesystem paths for D-Tools logging.

Single source of truth for where the D-Tools response/write logs land, so the
shared client and the MCP server always agree. Honors `$DTOOLS_LOG_DIR`;
defaults to `~/.dtools-cloud-mcp` (a private, install-location-independent dir).
Callers create it lazily (best-effort) when they first write.
"""

import os


def dtools_log_dir() -> str:
    """Directory for D-Tools logs. Override with $DTOOLS_LOG_DIR."""
    return os.path.expanduser(os.environ.get("DTOOLS_LOG_DIR", "~/.dtools-cloud-mcp"))
