"""D-Tools Cloud API client.

V2 — read + write. The D-Tools Cloud API exposes 8 write endpoints (clients,
opportunities, product price/status/barcode, project metadata); change orders
and quotes remain GET-only at the API itself. `_request` allows GET/POST/PUT;
non-idempotent POSTs skip the network-retry loop to avoid double-create. The
generic `dt_query` escape hatch stays GET-only via gateway `enforce_get_only`.

Auth:
  - BASIC_AUTH: D-Tools shared Basic header literal (public constant, every
    tenant sends the same value per D-Tools auth documentation).
  - X-API-Key: per-tenant secret resolved via op-injected DTOOLS_X_API_KEY.

Credentials note for Task 1.7:
  The 1Password item field name is `credential` (not `X-API-Key`). The
  dtools.env op-run mapping should read from that field when wiring the
  DTOOLS_X_API_KEY env var.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from xssentials.dtools.cloud.auth import DTAuthError, resolve_x_api_key
from xssentials.shared.paths import dtools_log_dir

logger = logging.getLogger(__name__)

# D-Tools shared Basic auth literal. Every tenant sends the same value per the
# D-Tools auth documentation ("Do not make your own"). Not a cryptographic
# secret — it is a public constant identical across all D-Tools integrations.
BASIC_AUTH = "Basic RFRDbG91ZEFQSVVzZXI6MyNRdVkrMkR1QCV3Kk15JTU8Yi1aZzlV"
BASE_URL = "https://dtcloudapi.d-tools.cloud/api/v1"

TIMEOUT_SECONDS = 15
LOG_PATH = os.path.join(dtools_log_dir(), "dtools_responses.log")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class ThrottleAuthFailure(RuntimeError):
    """3 consecutive 401s within 5 minutes — auth ladder exhausted."""


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Token-bucket rate limiter. Blocks callers past `rate_per_min` calls/min."""

    def __init__(self, rate_per_min: int = 100) -> None:
        self._rate = rate_per_min
        self._tokens = float(rate_per_min)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            # Refill tokens proportional to elapsed time
            self._tokens = min(
                float(self._rate),
                self._tokens + elapsed * (self._rate / 60.0),
            )
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            # Not enough tokens — calculate wait time and sleep
            deficit = 1.0 - self._tokens
            wait = deficit / (self._rate / 60.0)
        time.sleep(wait)
        with self._lock:
            self._tokens = max(0.0, self._tokens - 1.0 + wait * (self._rate / 60.0))


_rate_limiter = _RateLimiter(rate_per_min=100)


# ---------------------------------------------------------------------------
# Response logger
# ---------------------------------------------------------------------------

class _ResponseLogger:
    """Appends one JSONL record per response to dtools_responses.log.

    Rolling: rotates to .old when log exceeds 10 MB. Best-effort — never
    raises; failures are logged at DEBUG level only.
    """

    def __init__(self, path: str = LOG_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()

    def _ensure_dir(self) -> bool:
        """Return True if the log directory exists or was created."""
        d = os.path.dirname(self._path)
        if os.path.isdir(d):
            return True
        try:
            os.makedirs(d, exist_ok=True)
            return True
        except OSError:
            return False

    def log(
        self,
        method: str,
        path: str,
        status: int,
        headers: dict,
        elapsed_ms: float,
    ) -> None:
        record = json.dumps(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "method": method,
                "path": path,
                "status": status,
                "headers": dict(headers),
                "elapsed_ms": round(elapsed_ms, 1),
            }
        )
        try:
            with self._lock:
                if not self._ensure_dir():
                    return
                # Rotate if over cap
                if (
                    os.path.exists(self._path)
                    and os.path.getsize(self._path) > LOG_MAX_BYTES
                ):
                    old = self._path + ".old"
                    os.replace(self._path, old)
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(record + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.debug("_ResponseLogger silenced: %s", exc)


_response_logger = _ResponseLogger()


# ---------------------------------------------------------------------------
# Core request
# ---------------------------------------------------------------------------

def _request(
    method: str,
    path: str,
    params: dict | None = None,
    body: Any = None,
) -> Any:
    """Make a D-Tools Cloud API request.

    Supports GET (reads) and POST/PUT (writes). `body` is JSON-encoded and sent
    with Content-Type: application/json. POST is treated as non-idempotent — its
    network-retry loop is suppressed so a transient failure can't double-create.
    """
    method = method.upper()
    if method not in ("GET", "POST", "PUT"):
        raise ValueError(f"Unsupported HTTP method for D-Tools client: {method!r}")
    is_write = method != "GET"

    url = BASE_URL + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean, doseq=True)

    data = json.dumps(body).encode("utf-8") if body is not None else None

    # 401-as-throttle tracking state (per-process; resets on process restart)
    auth_failures: list[float] = []

    attempt = 0
    while True:
        _rate_limiter.acquire()

        headers = {
            "Authorization": BASIC_AUTH,
            "X-API-Key": resolve_x_api_key(),
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"

        t0 = time.monotonic()
        try:
            req = urllib.request.Request(
                url, data=data, method=method, headers=headers
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                elapsed_ms = (time.monotonic() - t0) * 1000
                resp_headers = dict(resp.getheaders())
                _response_logger.log(method, path, resp.status, resp_headers, elapsed_ms)
                resp_body = resp.read()
                return json.loads(resp_body) if resp_body else None

        except urllib.error.HTTPError as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            _response_logger.log(method, path, e.code, dict(e.headers), elapsed_ms)

            if e.code == 401:
                now = time.time()
                auth_failures.append(now)
                # Drop failures older than 5 minutes
                auth_failures[:] = [t for t in auth_failures if now - t < 300]

                if len(auth_failures) >= 3:
                    raise ThrottleAuthFailure(
                        f"3 consecutive 401s within 5 minutes on {path}. "
                        "Check DTOOLS_X_API_KEY and D-Tools tenant status."
                    ) from e

                if len(auth_failures) == 1:
                    # 1st 401: re-resolve auth (re-read env) + retry once
                    logger.warning(
                        "D-Tools 401 on %s (attempt %d) — re-resolving auth and retrying",
                        path, attempt + 1,
                    )
                    attempt += 1
                    continue  # retry with fresh resolve_x_api_key() call

                if len(auth_failures) == 2:
                    # 2nd 401 within 60s of 1st: exponential backoff
                    first_failure = auth_failures[0]
                    if now - first_failure <= 60:
                        backoff = [5, 30, 120]
                        wait = backoff[min(attempt - 1, len(backoff) - 1)]
                        logger.warning(
                            "D-Tools 401 on %s (attempt %d) — backing off %ds",
                            path, attempt + 1, wait,
                        )
                        time.sleep(wait)
                    attempt += 1
                    continue

            # Non-auth errors
            detail = e.read()[:500].decode(errors="replace")
            raise DTAuthError(
                f"HTTP {e.code} on {path}: {detail}"
            ) if e.code == 403 else RuntimeError(
                f"D-Tools HTTP {e.code} on {path}: {detail}"
            ) from e

        except urllib.error.URLError as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            # POST is non-idempotent: a network failure may have landed the
            # create on the server. Never auto-retry — surface it instead.
            if method == "POST":
                raise RuntimeError(
                    f"D-Tools connection failed for POST {path} (not retried — "
                    f"non-idempotent; verify whether the create landed): {e}"
                ) from e
            wait = 2 ** attempt
            logger.warning("D-Tools URL error on %s (%s) — retrying in %ds", path, e.reason, wait)
            time.sleep(wait)
            attempt += 1
            if attempt >= 3:
                raise RuntimeError(
                    f"D-Tools connection failed after 3 attempts for {method} {path}: {e}"
                ) from e
            continue


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_clients(**params: Any) -> list[dict]:
    """Primary canary call (dt_ping). Returns list from GET /Clients/GetClients."""
    return _request("GET", "/Clients/GetClients", params=params or None)


def get_client(client_id: str) -> dict:
    """Single-client detail by UUID. RPC path: /Clients/GetClient?id=<uuid>."""
    return get_one("Clients", client_id)


def search_clients(search: str, pageSize: int = 5) -> dict:
    """Substring + case-insensitive search by name. Returns dict with clients[] + totalClients."""
    return get_list("Clients", search=search, pageSize=pageSize, includeTotalCount=True)


def _depluralize(plural: str) -> str:
    """RPC-style D-Tools uses singular method names. e.g. Opportunities -> Opportunity."""
    if plural.endswith("ies"):
        return plural[:-3] + "y"
    if plural.endswith("s"):
        return plural[:-1]
    return plural


def get_one(resource: str, id: str) -> dict:
    """Fetch a single resource by ID via D-Tools RPC-style path.

    e.g. get_one('Clients', '<uuid>') -> GET /Clients/GetClient?id=<uuid>
    """
    method = "Get" + _depluralize(resource)
    return _request("GET", f"/{resource}/{method}", params={"id": id})


def get_list(resource: str, **params: Any) -> list[dict]:
    """Fetch a resource list via D-Tools RPC-style path.

    e.g. get_list('Opportunities', page=1, pageSize=50)
         -> GET /Opportunities/GetOpportunities?page=1&pageSize=50
    """
    return _request("GET", f"/{resource}/Get{resource}", params=params or None)


def get_quotes_for_opportunity(opp_id: str, **params: Any) -> dict:
    """Quotes belonging to an Opportunity. Returns dict with quotes[] + totalQuotes."""
    return get_list("Quotes", opportunityId=opp_id, includeTotalCount=True, **params)


# ---------------------------------------------------------------------------
# Write API (V2)
#
# The D-Tools Cloud API's entire write surface is these 8 endpoints. Change
# orders, quotes, line items, locations, and labor are NOT writable via the
# API — they must be entered through the D-Tools UI.
# ---------------------------------------------------------------------------

def update_product_prices(items: list[dict]) -> Any:
    """PUT /Products/UpdateProductPrices. Rows: {id, msrp, unitCost, unitPrice}."""
    return _request("PUT", "/Products/UpdateProductPrices", body=items)


def update_product_statuses(items: list[dict]) -> Any:
    """PUT /Products/UpdateProductStatuses. Rows: {id, isDiscontinued, isActive}."""
    return _request("PUT", "/Products/UpdateProductStatuses", body=items)


def update_product_barcodes(items: list[dict]) -> Any:
    """PUT /Products/UpdateProductBarcodes. Rows: {id, upcBarcode, eanBarcode, itfBarcode}."""
    return _request("PUT", "/Products/UpdateProductBarcodes", body=items)


def create_client(client: dict) -> Any:
    """POST /Clients/CreateClient. Body: Client record."""
    return _request("POST", "/Clients/CreateClient", body=client)


def update_client(id: str, client: dict) -> Any:
    """PUT /Clients/UpdateClient?id=<id>. Body: Client record."""
    return _request("PUT", "/Clients/UpdateClient", params={"id": id}, body=client)


def create_opportunity(opp: dict) -> Any:
    """POST /Opportunities/CreateOpportunity. Body: NewOpportunity record."""
    return _request("POST", "/Opportunities/CreateOpportunity", body=opp)


def update_opportunity(id: str, opp: dict) -> Any:
    """PUT /Opportunities/UpdateOpportunity?id=<id>. Body: UpdateOpportunity record."""
    return _request(
        "PUT", "/Opportunities/UpdateOpportunity", params={"id": id}, body=opp
    )


def update_project(id: str, project: dict) -> Any:
    """PUT /Projects/UpdateProject?id=<id>. Body: UpdateProject (metadata only)."""
    return _request("PUT", "/Projects/UpdateProject", params={"id": id}, body=project)
