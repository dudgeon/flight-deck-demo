"""Remove paths from wheels in place and rewrite their RECORD.

Usage: python strip_wheel.py WHEEL [WHEEL ...] --remove PREFIX [--remove PREFIX ...]

The wheels keep their names: entries whose path starts with a PREFIX are
dropped and the RECORD file lists only what remains.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import zipfile
from pathlib import Path


def _record_line(name: str, data: bytes) -> list[str]:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return [name, f"sha256={digest}", str(len(data))]


def strip(wheel: Path, prefixes: list[str]) -> int:
    with zipfile.ZipFile(wheel) as source:
        entries = [(info, source.read(info)) for info in source.infolist()]
    record_name = next(info.filename for info, _ in entries if info.filename.endswith(".dist-info/RECORD"))
    kept = [
        (info, data)
        for info, data in entries
        if info.filename != record_name and not info.filename.startswith(tuple(prefixes))
    ]
    removed = len(entries) - 1 - len(kept)
    rows = io.StringIO()
    writer = csv.writer(rows, lineterminator="\n")
    for info, data in kept:
        writer.writerow(_record_line(info.filename, data))
    writer.writerow([record_name, "", ""])
    temp = wheel.with_suffix(".tmp")
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info, data in kept:
            target.writestr(info, data)
        target.writestr(record_name, rows.getvalue())
    temp.replace(wheel)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheels", nargs="+", type=Path)
    parser.add_argument("--remove", action="append", required=True)
    args = parser.parse_args()
    for wheel in args.wheels:
        print(f"{wheel.name}: removed {strip(wheel, args.remove)} files")


if __name__ == "__main__":
    main()
