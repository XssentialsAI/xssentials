"""ConnectWise Manage REST client.

Auth scheme: HTTP Basic with `<CW_COMPANY_ID>+<CW_PUBLIC_KEY>:<CW_PRIVATE_KEY>`,
plus a `clientId` header carrying the developer registration UUID
(`CW_CLIENT_ID` — distinct from `CW_COMPANY_ID`).

All credentials are sourced from environment variables resolved at process start
by `op run --env-file=cw.env -- ...`. No plaintext on disk.

Required env vars:
    CW_COMPANY_ID   — tenant short name (e.g., "xssentials")
    CW_PUBLIC_KEY   — Member API public key
    CW_PRIVATE_KEY  — Member API private key
    CW_CLIENT_ID    — CW developer Client ID (UUID)
    CW_TENANT_URL   — full API base URL including the version path,
                      e.g., "https://na.myconnectwise.net/v4_6_release/apis/3.0"
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

from xssentials.shared.auth_helpers import MissingEnvError, required_env

logger = logging.getLogger(__name__)

API_VERSION = "v2025_1"
TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 3


class CWAuthError(RuntimeError):
    """Credentials missing, malformed, or rejected by CW (401)."""


class CWAPIError(RuntimeError):
    """CW returned a non-auth error or all retries failed."""


def _required_env(name: str) -> str:
    try:
        return required_env(name, env_file_hint="cw.env")
    except MissingEnvError as e:
        raise CWAuthError(str(e)) from e


def _auth_header() -> str:
    company = _required_env("CW_COMPANY_ID")
    public = _required_env("CW_PUBLIC_KEY")
    private = _required_env("CW_PRIVATE_KEY")
    raw = f"{company}+{public}:{private}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _base_url() -> str:
    # CW_TENANT_URL is expected to be the full API base URL including version path
    # (e.g., https://na.myconnectwise.net/v4_6_release/apis/3.0). The 1Password
    # `api_url` field stores it that way; strip any trailing whitespace/slash.
    return _required_env("CW_TENANT_URL").strip().rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "Authorization": _auth_header(),
        "clientId": _required_env("CW_CLIENT_ID"),
        "Accept": f"application/vnd.connectwise.com+json; version={API_VERSION}",
    }


def _request(method: str, path: str, params: dict | None = None) -> Any:
    if method != "GET":
        raise NotImplementedError("Phase 1 is read-only; only GET is supported.")
    url = _base_url() + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urlencode(clean)
    last_err: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            req = urllib.request.Request(url, method="GET", headers=_headers())
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                body = resp.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 401:
                detail = e.read()[:500].decode(errors="replace")
                raise CWAuthError(
                    f"401 Unauthorized from CW. clientId={os.environ.get('CW_CLIENT_ID', '')[:8]}..., "
                    f"company={os.environ.get('CW_COMPANY_ID')!r}. Body: {detail}"
                ) from e
            if e.code == 429 or e.code >= 500:
                wait = 2 ** attempt
                logger.warning("CW %s on %s — retrying in %ds (attempt %d/%d)",
                               e.code, path, wait, attempt + 1, MAX_ATTEMPTS)
                time.sleep(wait)
                continue
            detail = e.read()[:500].decode(errors="replace")
            raise CWAPIError(f"HTTP {e.code} on {path}: {detail}") from e
        except urllib.error.URLError as e:
            last_err = e
            wait = 2 ** attempt
            logger.warning("URL error on %s (%s) — retrying in %ds",
                           path, e.reason, wait)
            time.sleep(wait)
            continue
    raise CWAPIError(f"All {MAX_ATTEMPTS} attempts failed for GET {path}: {last_err}")


def get_system_info() -> dict:
    """Return CW Manage instance info (version, region, license).

    This is the W0 cred-verification canary: a successful response proves
    the full 1Password → op → env → CW REST chain works end-to-end.
    `/system/members/me` was attempted first but CW v2025.1 interprets `me`
    as numeric Member ID 0 (404 Not Found) — `/system/info` is the supported
    minimal authenticated endpoint.

    Returns keys: version, serverTimeZone, cloudRegion, isCloud, licenseBits,
    maxWorkFlowRecordsAllowed.
    """
    return _request("GET", "/system/info")


def get_list(
    path: str,
    conditions: str | None = None,
    page_size: int = 25,
    page: int = 1,
    fields: str | None = None,
    order_by: str | None = None,
) -> list:
    """Generic GET-list wrapper used by curated tools and the gateway.

    CW Manage REST conventions:
      - `conditions` = SQL-like filter, e.g. 'name contains "driftwood"' or
        'status/id = 1 and company/id = 65317'. Fields use slashes for nested
        access (`company/name`, not `company.name`).
      - `pageSize` defaults to 25, hard-capped at 1000 by CW. No cursor-based
        pagination — use `page=N` with stable `orderBy` for deterministic results.
      - `fields` = comma-separated field allowlist (top-level only). Selecting a
        nested field name returns the entire nested object.
    """
    params = {
        "conditions": conditions,
        "pageSize": page_size,
        "page": page,
        "fields": fields,
        "orderBy": order_by,
    }
    return _request("GET", path, params=params)


def get_one(path: str, fields: str | None = None) -> dict:
    """Generic GET-one wrapper for single-resource endpoints (e.g. /project/projects/{id})."""
    params = {"fields": fields} if fields else None
    return _request("GET", path, params=params)


def get_count(path: str, conditions: str | None = None) -> int:
    """Cheap cardinality probe — returns CW's `count` field for a list endpoint.

    Useful for `pagination_footer(total=...)` without paging through full results.
    Endpoint convention: `<list-path>/count`, e.g. /service/tickets/count.
    """
    resp = _request("GET", path.rstrip("/") + "/count",
                    params={"conditions": conditions} if conditions else None)
    if isinstance(resp, dict) and "count" in resp:
        return int(resp["count"])
    raise RuntimeError(f"unexpected /count response shape: {type(resp).__name__}")
