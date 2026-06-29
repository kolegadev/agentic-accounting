"""Formatting helpers — pre-render structured data as markdown tables.

The LLM is unreliable at faithfully reproducing structured data.  Instead of
asking it to reformat tool results, we pre-render them here and pass the
formatted string through directly.
"""

from __future__ import annotations

from typing import Any


def render_table(
    rows: list[dict],
    columns: list[tuple[str, str]],
    *,
    max_rows: int = 100,
    empty_message: str = "No results found.",
) -> dict:
    """Render a list of dicts as a markdown table.

    Args:
        rows: List of dicts to render.
        columns: List of (key, display_header) tuples.
        max_rows: Maximum rows before truncation.
        empty_message: Message when rows is empty.

    Returns:
        {"formatted": str, "count": int, "truncated": bool}
    """
    total = len(rows)
    if total == 0:
        return {"formatted": empty_message, "count": 0, "truncated": False}

    truncated = total > max_rows
    display = rows[:max_rows]

    header = "| " + " | ".join(h for _, h in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"

    body_lines = []
    for row in display:
        cells = []
        for key, _ in columns:
            v = row.get(key)
            if v is None:
                cells.append("")
            else:
                s = str(v).replace("|", "\\|").replace("\n", " ")
                cells.append(s)
        body_lines.append("| " + " | ".join(cells) + " |")

    table = "\n".join([header, sep, *body_lines])

    if truncated:
        table += f"\n\n*Showing {max_rows} of {total} results.*"

    return {"formatted": table, "count": total, "truncated": truncated}


def format_pence(amount: int | None) -> str:
    """Convert integer pence to £X,XXX.XX string."""
    if amount is None:
        return ""
    sign = "-" if amount < 0 else ""
    pounds = abs(amount) / 100
    return f"{sign}£{pounds:,.2f}"
