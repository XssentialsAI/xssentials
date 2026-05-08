"""D-Tools Cloud API auth resolver.

The X-API-Key is sourced from the environment via `op run --env-file=dtools.env`.
No plaintext credentials on disk.

Required env var:
    DTOOLS_X_API_KEY  — per-tenant API key from D-Tools Cloud portal
"""

from __future__ import annotations

from xssentials.shared.auth_helpers import MissingEnvError, required_env


class DTAuthError(RuntimeError):
    """D-Tools credentials missing or rejected (401)."""


def resolve_x_api_key() -> str:
    """Return DTOOLS_X_API_KEY from the environment or raise DTAuthError."""
    try:
        return required_env("DTOOLS_X_API_KEY", env_file_hint="dtools.env")
    except MissingEnvError as e:
        raise DTAuthError(str(e)) from e
