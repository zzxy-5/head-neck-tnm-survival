from __future__ import annotations

import csv
from collections.abc import Iterator, Sequence
from pathlib import Path


class CsvSource:
    def __init__(self, paths: Sequence[Path], required_columns: Sequence[str]) -> None:
        self.paths = tuple(Path(path) for path in paths)
        self.required_columns = tuple(required_columns)
        self.source_counts: dict[str, int] = {}

    def rows(self) -> Iterator[dict[str, str]]:
        for path in self.paths:
            if not path.is_file():
                raise FileNotFoundError(f"SEER CSV not found: {path}")
            count = 0
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                header = set(reader.fieldnames or ())
                missing = sorted(set(self.required_columns) - header)
                if missing:
                    raise ValueError(f"{path.name} missing required columns: {', '.join(missing)}")
                for raw in reader:
                    count += 1
                    yield {name: raw.get(name) or "" for name in self.required_columns}
            self.source_counts[path.name] = count
