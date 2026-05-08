"""Env-var resolvers for `op run`-injected credentials.

Vendor-specific clients wrap `required_env` and re-raise as their own auth
error class so callers can keep catching by vendor.
"""

from __future__ import annotations

import os


class MissingEnvError(RuntimeError):
    """Required env var is missing — `op run --env-file=...` likely skipped."""


def required_env(name: str, env_file_hint: str = "the project's .env file") -> str:
    """Return the value of an env var or raise MissingEnvError.

    `env_file_hint` is interpolated into the error message so the caller can
    point at the right `.env` (cw.env, dtools.env, etc.) without reformatting.
    """
    value = os.environ.get(name)
    if not value:
        raise MissingEnvError(
            f"Missing required env var {name}. "
            f"Run via `op run --env-file={env_file_hint} -- ...` to resolve from 1Password."
        )
    return value
