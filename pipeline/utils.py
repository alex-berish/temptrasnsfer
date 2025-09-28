"""Small utility helpers reused across pipeline scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def read_json(path: Path) -> Any:
    """Load JSON data from *path*.

    Raises FileNotFoundError if the file does not exist and json.JSONDecodeError on
    invalid content.
    """

    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any, *, indent: int = 4) -> None:
    """Write JSON *data* to *path* with the given *indent*."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent)


def append_text(path: Path, lines: Iterable[str]) -> None:
    """Append lines of text to *path*, creating parent directories as needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line)


__all__ = ["read_json", "write_json", "append_text"]
