"""Inline assertions for xssentials.shared.

Run: python -m tests.test_shared (from ~/Pits_Of_Hathsin/xssentials)
"""

from __future__ import annotations

from xssentials.shared.formatters import (
    markdown_card,
    markdown_narrative,
    markdown_table,
    pagination_footer,
    partial_callout,
    link_cell,
    link_header,
)
from xssentials.shared.validators import check_payload_size, enforce_get_only
from xssentials.shared.auth_helpers import MissingEnvError, required_env


def test_pagination_footer():
    assert pagination_footer(4, 4, False) == "_count: 4 · total: 4 · has_more: false_"
    assert "has_more: true" in pagination_footer(25, 132, True)


def test_partial_callout():
    out = partial_callout("get_clients")
    assert out.startswith("> [!warning]"), out
    assert "get_clients" in out
    assert "15s" in out


def test_link_helpers_default():
    # Shared defaults are vendor-neutral
    assert link_header("https://x") == "[View →](https://x)"
    assert link_header("https://x", label="View in D-Tools →") == "[View in D-Tools →](https://x)"
    assert link_cell("https://x") == "[↗](https://x)"


def test_markdown_card_label_param():
    out = markdown_card("Title", "https://x", {"S": "v"}, header_label="View in D-Tools →")
    assert "[View in D-Tools →](https://x)" in out
    assert "## S" in out


def test_markdown_table_basic():
    out = markdown_table([{"a": "1", "_link": "u"}, {"a": "2", "_link": ""}], ["a"], link_col=True)
    assert "[↗](u)" in out
    # second row has no link, empty cell
    assert out.count("|") > 0


def test_markdown_narrative_under_threshold():
    """Verbatim — body shorter than threshold renders without truncation marker."""
    body = "Short scope of work."
    out = markdown_narrative(
        title="Quote #123",
        header_link="https://x",
        narrative_blocks={"Scope of Work": body},
        structured_fields={"Stage": "Won"},
        header_label="View in D-Tools →",
    )
    assert "**Quote #123**" in out
    assert "[View in D-Tools →](https://x)" in out
    assert "## Scope of Work" in out
    assert body in out
    assert "more chars" not in out  # no truncation marker
    assert "## Details" in out
    assert "| Stage | Won |" in out


def test_markdown_narrative_over_threshold():
    """Body longer than threshold gets truncated with tail marker."""
    body = "x" * 2500
    out = markdown_narrative(
        title="Big Quote",
        header_link=None,
        narrative_blocks={"Scope": body},
        structured_fields=None,
        header_label="View in D-Tools →",
        threshold_chars=2000,
    )
    assert "## Scope" in out
    # 500 chars over the 2000 threshold
    assert "_…[500 more chars — view in D-Tools]_" in out, out[-200:]
    # Verbatim portion is the first 2000 chars
    assert out.count("x") == 2000


def test_markdown_narrative_skips_empty_blocks():
    """Empty narrative blocks are silently dropped (not rendered as blank H2s)."""
    out = markdown_narrative(
        title="T",
        header_link=None,
        narrative_blocks={"Notes": "", "Internal": "   ", "Scope": "real text"},
        structured_fields=None,
    )
    assert "## Notes" not in out
    assert "## Internal" not in out
    assert "## Scope" in out


def test_markdown_narrative_no_link():
    """No header_link → no link line."""
    out = markdown_narrative(
        title="T",
        header_link=None,
        narrative_blocks={"S": "x"},
        structured_fields=None,
    )
    assert "View" not in out  # neither default nor labeled link present


def test_check_payload_size_pass():
    check_payload_size({"id": 12345, "limit": 25})


def test_check_payload_size_fail():
    big = {"conditions": "x" * 1000}
    try:
        check_payload_size(big)
    except ValueError as e:
        assert "conditions" in str(e)
        assert "750B" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_enforce_get_only():
    enforce_get_only("GET")
    enforce_get_only("get")
    for m in ("POST", "PUT", "PATCH", "DELETE"):
        try:
            enforce_get_only(m)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {m}")


def test_required_env_missing():
    import os
    name = "__XSS_SHARED_TEST_VAR_THAT_DOES_NOT_EXIST__"
    os.environ.pop(name, None)
    try:
        required_env(name, env_file_hint="dtools.env")
    except MissingEnvError as e:
        assert name in str(e)
        assert "dtools.env" in str(e)
    else:
        raise AssertionError("expected MissingEnvError")


def test_required_env_present():
    import os
    name = "__XSS_SHARED_TEST_PRESENT__"
    os.environ[name] = "value-x"
    try:
        assert required_env(name) == "value-x"
    finally:
        os.environ.pop(name, None)


if __name__ == "__main__":
    test_pagination_footer()
    test_partial_callout()
    test_link_helpers_default()
    test_markdown_card_label_param()
    test_markdown_table_basic()
    test_markdown_narrative_under_threshold()
    test_markdown_narrative_over_threshold()
    test_markdown_narrative_skips_empty_blocks()
    test_markdown_narrative_no_link()
    test_check_payload_size_pass()
    test_check_payload_size_fail()
    test_enforce_get_only()
    test_required_env_missing()
    test_required_env_present()
    print("All xssentials.shared assertions passed.")
