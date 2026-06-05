"""Guard tests for the ConnectWise write transport.

The write path must reject any method other than POST/PATCH and any path outside
the /system/members allowlist BEFORE touching the network or credentials — so
these run with no env configured.

Run from the xssentials repo root: python -m tests.test_connectwise_write_guard
"""

from __future__ import annotations

from xssentials.connectwise import client


def test_rejects_non_write_methods():
    for method in ("GET", "PUT", "DELETE", "HEAD"):
        try:
            client._write_request(method, "/system/members", {})
        except NotImplementedError:
            pass
        else:
            raise AssertionError(f"expected NotImplementedError for method {method!r}")


def test_rejects_paths_outside_allowlist():
    for path in ("/finance/invoices", "/company/companies", "/system/info", "/system/membersX"):
        try:
            client._write_request("POST", path, {})
        except ValueError as e:
            assert "allowlist" in str(e).lower(), e
        else:
            raise AssertionError(f"expected ValueError for path {path!r}")


def test_allowlist_accepts_member_paths():
    # These pass the guard (so they'd hit the network) — assert the guard does
    # NOT raise by checking the failure is a network/auth error, not a guard error.
    assert client._path_allowed("/system/members") is True
    assert client._path_allowed("/system/members/820") is True
    assert client._path_allowed("/system/membersX") is False
    assert client._path_allowed("/finance/invoices") is False


if __name__ == "__main__":
    test_rejects_non_write_methods()
    test_rejects_paths_outside_allowlist()
    test_allowlist_accepts_member_paths()
    print("All connectwise write-guard assertions passed.")
