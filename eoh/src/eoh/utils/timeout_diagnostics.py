from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - non-Unix fallback
    fcntl = None


SUMMARY_ROOT_CAUSES = (
    "success",
    "llm_timeout",
    "eval_timeout",
    "parse_error",
    "worker_budget_timeout",
)


def write_timeout_record(path: str | None, record: dict, enabled: bool) -> None:
    """Append a single diagnostics record to a JSONL file."""
    if not enabled or not path:
        return

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, default=str, sort_keys=True)

    with output_path.open("a", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(line + "\n")
        handle.flush()
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def summarize_timeout_records(path: str | None) -> dict[str, int]:
    """Return counts for the main timeout root causes."""
    counter: Counter[str] = Counter()
    if not path:
        return {key: 0 for key in SUMMARY_ROOT_CAUSES}

    input_path = Path(path)
    if not input_path.exists():
        return {key: 0 for key in SUMMARY_ROOT_CAUSES}

    with input_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            event = record.get("event")
            if event == "offspring_result":
                counter[str(record.get("root_cause", "unknown"))] += 1
            elif event == "worker_budget_timeout":
                counter["worker_budget_timeout"] += 1

    return {key: int(counter.get(key, 0)) for key in SUMMARY_ROOT_CAUSES}
