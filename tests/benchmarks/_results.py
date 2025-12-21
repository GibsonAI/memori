from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_dir() -> Path:
    path = repo_root() / "results"
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_csv_row(path: str | Path, *, header: list[str], row: dict[str, Any]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = out_path.exists()
    with out_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
