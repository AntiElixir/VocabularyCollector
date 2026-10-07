"""Self-contained vocabulary HTML page with atomic writes."""

from __future__ import annotations

import html
import os
from pathlib import Path

_HEADERS = ("english", "chinese", "domain", "created_at")

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Vocabulary</title>
</head>
<body>
<h1>Vocabulary</h1>
<table>
<thead>
<tr>{head}</tr>
</thead>
<tbody>
{body}
</tbody>
</table>
</body>
</html>
"""


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def render(rows) -> str:
    """Render a complete HTML document from newest-first rows."""
    head = "".join(f"<th>{_escape(column)}</th>" for column in _HEADERS)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{_escape(value)}</td>" for value in row[:4]) + "</tr>"
        for row in rows
    )
    return _PAGE.format(head=head, body=body)


def write_atomic(path: Path | str, content: str) -> None:
    """Write ``content`` to ``path`` via a temp file + os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    os.replace(tmp, path)