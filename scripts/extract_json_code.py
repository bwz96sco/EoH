#!/usr/bin/env python3

"""Utility script to print the code snippet stored under a JSON field."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_JSON = "/Users/zhangbowen/Projects/EoH/results/pops_best/population_generation_2.json"


def read_code_snippet(json_path: str, field: str) -> str:
    """Read the requested JSON file and return the text stored under `field`."""
    path = Path(json_path).expanduser()
    with path.open("r", encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON from {path}") from exc

    try:
        code = payload[field]
    except KeyError as exc:
        raise ValueError(f"Field '{field}' not present in {path}") from exc

    if not isinstance(code, str):
        raise ValueError(f"Field '{field}' in {path} must be a string.")

    return code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print the Python code stored under the 'code' field of a JSON file."
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        default=DEFAULT_JSON,
        help=f"Path to the JSON file (default: {DEFAULT_JSON})",
    )
    parser.add_argument(
        "--field",
        default="code",
        help="JSON field containing the code snippet (default: code)",
    )
    args = parser.parse_args()

    try:
        snippet = read_code_snippet(args.json_path, args.field)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(snippet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

