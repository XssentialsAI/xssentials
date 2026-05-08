"""Vendor-agnostic Markdown output helpers.

Vendor-specific link patterns (e.g., `cw_ui_link`, `dt_ui_link`) live in the
respective vendor packages. The label-bearing helpers here (`markdown_card`,
`link_header`) take a `header_label`/`label` parameter so vendor shims can
inject `View in CW →` / `View in D-Tools →` / etc.
"""

from __future__ import annotations

from typing import Mapping, Sequence


def markdown_card(
    title: str,
    header_link: str | None,
    sections: Mapping[str, str],
    header_label: str = "View →",
) -> str:
    """Render a single-resource result.

    Layout:
      **{title}**
      [{header_label}]({header_link})

      ## {section_name}
      {section_body}
    """
    lines: list[str] = [f"**{title}**"]
    if header_link:
        lines.append(f"[{header_label}]({header_link})")
    for section_name, section_body in sections.items():
        lines.append("")
        lines.append(f"## {section_name}")
        lines.append(section_body)
    return "\n".join(lines)


def markdown_table(
    rows: Sequence[Mapping[str, str]],
    columns: Sequence[str],
    link_col: bool = True,
) -> str:
    """Render a list-of-dicts as a pipe table.

    When `link_col=True`, an extra column with `[↗](url)` is appended; rows must
    include a `_link` key holding the URL (or empty string).
    """
    header_cells = list(columns) + ([""] if link_col else [])
    sep_cells = ["---"] * len(header_cells)
    out = [
        "| " + " | ".join(header_cells) + " |",
        "| " + " | ".join(sep_cells) + " |",
    ]
    for row in rows:
        cells = [str(row.get(col, "")) for col in columns]
        if link_col:
            link = row.get("_link", "")
            cells.append(f"[↗]({link})" if link else "")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def pagination_footer(count: int, total: int, has_more: bool) -> str:
    """Footer line for list-returning tools."""
    return f"_count: {count} · total: {total} · has_more: {str(has_more).lower()}_"


def partial_callout(failed_subcall: str, timeout_seconds: int = 15) -> str:
    """Leading Obsidian callout for a tool that returned partial data after a timeout."""
    return (
        f"> [!warning] Partial result — `{failed_subcall}` timed out at "
        f"{timeout_seconds}s. Re-run for full data."
    )


def link_header(url: str, label: str = "View →") -> str:
    """Header-style vendor-UI link for single-resource cards."""
    return f"[{label}]({url})"


def link_cell(url: str) -> str:
    """Inline vendor-UI link for table rows."""
    return f"[↗]({url})"


def markdown_narrative(
    title: str,
    header_link: str | None,
    narrative_blocks: Mapping[str, str],
    structured_fields: Mapping[str, str] | None = None,
    header_label: str = "View →",
    threshold_chars: int = 2000,
) -> str:
    """Narrative-first detail render.

    Lays the salesperson narrative (`scopeOfWork`, `notes`, etc.) as full text
    blocks under the title, with structured fields as a compact table beneath.
    Narrative blocks longer than `threshold_chars` are truncated with a tail
    marker pointing at the vendor UI for the full text.

    Layout:
      **{title}**
      [{header_label}]({header_link})

      ## {block_name}
      {block_body}
      _…[N more chars — view in {vendor}]_

      ## Details
      | field | value |
    """
    lines: list[str] = [f"**{title}**"]
    if header_link:
        lines.append(f"[{header_label}]({header_link})")

    # Derive a vendor name from header_label for the truncation tail
    # ("View in D-Tools →" → "D-Tools"; "View in CW →" → "CW"; fallback "the vendor UI")
    vendor = "the vendor UI"
    if "in " in header_label:
        tail = header_label.split("in ", 1)[1]
        vendor = tail.replace("→", "").strip() or vendor

    for block_name, block_body in narrative_blocks.items():
        if not block_body or not block_body.strip():
            continue
        lines.append("")
        lines.append(f"## {block_name}")
        if len(block_body) > threshold_chars:
            kept = block_body[:threshold_chars].rstrip()
            remaining = len(block_body) - threshold_chars
            lines.append(kept)
            lines.append("")
            lines.append(f"_…[{remaining} more chars — view in {vendor}]_")
        else:
            lines.append(block_body)

    if structured_fields:
        lines.append("")
        lines.append("## Details")
        lines.append("| field | value |")
        lines.append("| --- | --- |")
        for k, v in structured_fields.items():
            lines.append(f"| {k} | {v} |")

    return "\n".join(lines)
