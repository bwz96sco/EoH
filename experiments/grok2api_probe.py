#!/usr/bin/env python3
"""grok2api stability probe.

Two modes:
  quality: single-process, sequential long-prompt calls. Measures response
           quality (empty_200 rate), latency, and first-vs-reused-connection
           delta.
  load:    multi-process via joblib (loky backend), sweeping client
           concurrency. Mirrors EoH's `get_algorithm` pattern so probe and
           production exercise the same HTTP + retry path.

The probe imports eoh.llm.api_general.InterfaceAPI directly; it does not
reimplement HTTP. Empty-content detection lives in this probe only — the
production client is not modified.

Typical first-round run on heyun (see experiments/grok2api_probe_README.md):

  uv run python experiments/grok2api_probe.py --mode quality --n-calls 30 \\
      --report-out /tmp/q-w1.json

  for N in 1 2 3 6; do
    uv run python experiments/grok2api_probe.py --mode load \\
        --concurrency "$N" --pop-size 6 --n-gen 3 \\
        --report-out "/tmp/l-w1-n${N}.json"
  done
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from joblib import Parallel, delayed

from eoh.llm.api_general import InterfaceAPI

DEFAULT_PROMPT_FILE = Path(__file__).with_name("grok2api_probe_sample_prompt.txt")
TRANSPORT_ERROR_TYPES = {
    "RemoteDisconnected",
    "BrokenPipeError",
    "TimeoutError",
    "timeout",
    "ConnectionResetError",
    "ConnectionError",
    "ConnectionAbortedError",
    "ConnectionRefusedError",
    "OSError",
    "TotalTimeoutExceeded",
}


@dataclass
class CallRecord:
    t: str
    mode: str
    worker: int
    concurrency: int
    call_idx: int
    http_attempts: int
    content_len: int
    elapsed_ms: float
    error_type: str | None
    status: str
    content_preview: str = ""


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _client_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return dict(
        api_endpoint=args.endpoint,
        api_key=args.api_key,
        model_LLM=args.model,
        debug_mode=False,
        request_timeout_s=args.request_timeout,
        total_timeout_s=args.total_timeout,
    )


def _classify(response: Any, meta: dict[str, Any]) -> str:
    if response is None:
        return meta.get("error_type") or meta.get("status") or "no_response"
    if isinstance(response, str) and response.strip() == "":
        return "empty_200"
    return "success"


def _one_call(
    client: InterfaceAPI,
    prompt: str,
    *,
    mode: str,
    worker: int,
    concurrency: int,
    call_idx: int,
) -> CallRecord:
    start = time.monotonic()
    try:
        response: Any = client.get_response(prompt)
    except Exception as exc:  # pragma: no cover — defensive
        elapsed_ms = (time.monotonic() - start) * 1000
        return CallRecord(
            t=_iso_now(),
            mode=mode,
            worker=worker,
            concurrency=concurrency,
            call_idx=call_idx,
            http_attempts=0,
            content_len=0,
            elapsed_ms=elapsed_ms,
            error_type=type(exc).__name__,
            status="probe_exception",
            content_preview=f"{type(exc).__name__}: {exc}"[:80],
        )

    meta = dict(getattr(client, "last_request_meta", {}))
    content_len = len(response) if isinstance(response, str) else 0
    preview = ""
    if isinstance(response, str) and response:
        preview = response.strip().replace("\n", " ")[:80]
    return CallRecord(
        t=_iso_now(),
        mode=mode,
        worker=worker,
        concurrency=concurrency,
        call_idx=call_idx,
        http_attempts=int(meta.get("attempts") or 0),
        content_len=content_len,
        elapsed_ms=float(meta.get("elapsed_ms") or (time.monotonic() - start) * 1000),
        error_type=meta.get("error_type"),
        status=_classify(response, meta),
        content_preview=preview,
    )


def run_quality(args: argparse.Namespace, prompt: str) -> list[CallRecord]:
    client = InterfaceAPI(**_client_kwargs(args))
    records: list[CallRecord] = []
    for i in range(args.n_calls):
        rec = _one_call(
            client,
            prompt,
            mode="quality",
            worker=0,
            concurrency=1,
            call_idx=i,
        )
        records.append(rec)
        print(json.dumps(asdict(rec)))
    return records


def _load_worker(
    client_kwargs: dict[str, Any],
    prompt: str,
    worker_idx: int,
    concurrency: int,
    n_calls: int,
) -> list[CallRecord]:
    client = InterfaceAPI(**client_kwargs)
    return [
        _one_call(
            client,
            prompt,
            mode="load",
            worker=worker_idx,
            concurrency=concurrency,
            call_idx=i,
        )
        for i in range(n_calls)
    ]


def run_load(args: argparse.Namespace, prompt: str) -> list[CallRecord]:
    concurrencies = [int(x) for x in args.concurrency.split(",") if x.strip()]
    total_target = args.pop_size * args.n_gen
    all_records: list[CallRecord] = []

    for n_workers in concurrencies:
        per_worker = max(1, -(-total_target // n_workers))
        print(
            f"--- load N={n_workers} total_target={total_target} "
            f"per_worker={per_worker} ---"
        )
        try:
            groups = Parallel(
                n_jobs=n_workers,
                backend="loky",
                timeout=args.parallel_timeout,
            )(
                delayed(_load_worker)(
                    _client_kwargs(args),
                    prompt,
                    worker_idx,
                    n_workers,
                    per_worker,
                )
                for worker_idx in range(n_workers)
            )
        except Exception as exc:
            print(
                f"[probe] Parallel run crashed for N={n_workers}: "
                f"{type(exc).__name__}: {exc}"
            )
            groups = []

        for group in groups:
            for rec in group:
                all_records.append(rec)
                print(json.dumps(asdict(rec)))

    return all_records


def summarize(records: list[CallRecord]) -> dict[str, Any]:
    total = len(records)
    if total == 0:
        return {"total": 0}

    by_status = Counter(r.status for r in records)
    by_attempts = Counter(r.http_attempts for r in records)
    transport_err = sum(
        1 for r in records if (r.error_type or "") in TRANSPORT_ERROR_TYPES
    )

    latencies = [r.elapsed_ms for r in records if r.elapsed_ms > 0]
    latency_stats: dict[str, float] = {}
    if latencies:
        sorted_lat = sorted(latencies)

        def _pct(p: float) -> float:
            idx = min(len(sorted_lat) - 1, max(0, int(round(len(sorted_lat) * p)) - 1))
            return sorted_lat[idx]

        latency_stats = {
            "min": sorted_lat[0],
            "p50": _pct(0.50),
            "p95": _pct(0.95),
            "p99": _pct(0.99),
            "max": sorted_lat[-1],
            "mean": statistics.mean(sorted_lat),
        }

    content_lens = [r.content_len for r in records]
    first_vs_reused: dict[str, float] = {}
    per_worker_first: dict[int, float] = {}
    per_worker_rest: dict[int, list[float]] = {}
    for r in records:
        if r.elapsed_ms <= 0:
            continue
        if r.call_idx == 0:
            per_worker_first.setdefault(r.worker, r.elapsed_ms)
        else:
            per_worker_rest.setdefault(r.worker, []).append(r.elapsed_ms)
    if per_worker_first and per_worker_rest:
        firsts = list(per_worker_first.values())
        rest_flat = [x for lst in per_worker_rest.values() for x in lst]
        if firsts and rest_flat:
            first_vs_reused = {
                "first_mean_ms": statistics.mean(firsts),
                "reused_mean_ms": statistics.mean(rest_flat),
                "delta_ms": statistics.mean(firsts) - statistics.mean(rest_flat),
            }

    return {
        "total": total,
        "success_rate": by_status.get("success", 0) / total,
        "empty_200_rate": by_status.get("empty_200", 0) / total,
        "transport_error_rate": transport_err / total,
        "by_status": dict(by_status),
        "by_http_attempts": dict(sorted(by_attempts.items())),
        "content_len_mean": statistics.mean(content_lens) if content_lens else 0,
        "content_len_min": min(content_lens) if content_lens else 0,
        "content_len_max": max(content_lens) if content_lens else 0,
        "latency_ms": latency_stats,
        "first_vs_reused": first_vs_reused,
    }


def summarize_by_concurrency(
    records: list[CallRecord],
) -> dict[str, dict[str, Any]]:
    buckets: dict[int, list[CallRecord]] = {}
    for r in records:
        buckets.setdefault(r.concurrency, []).append(r)
    return {str(n): summarize(recs) for n, recs in sorted(buckets.items())}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="grok2api stability probe")
    p.add_argument("--mode", choices=["quality", "load"], required=True)
    p.add_argument(
        "--endpoint",
        default=os.environ.get("LLM_API_ENDPOINT", "http://127.0.0.1:8000"),
        help="grok2api endpoint (default: env LLM_API_ENDPOINT or 127.0.0.1:8000)",
    )
    p.add_argument(
        "--api-key",
        default=os.environ.get("LLM_API_KEY", "xxx"),
        help="API key (default: env LLM_API_KEY)",
    )
    p.add_argument(
        "--model",
        default=os.environ.get("LLM_MODEL", "grok-4.20-fast"),
        help="model name (default: env LLM_MODEL)",
    )
    p.add_argument(
        "--request-timeout",
        type=int,
        default=int(os.environ.get("LLM_REQUEST_TIMEOUT_S", "300")),
    )
    p.add_argument(
        "--total-timeout",
        type=int,
        default=int(os.environ.get("LLM_TOTAL_TIMEOUT_S", "600")),
    )
    p.add_argument(
        "--prompt-file",
        default=str(DEFAULT_PROMPT_FILE),
        help="path to long-prompt sample; defaults to repo sample",
    )
    p.add_argument("--report-out", default="", help="write summary+records JSON to path")

    p.add_argument(
        "--n-calls",
        type=int,
        default=30,
        help="quality mode: sequential calls (default 30)",
    )

    p.add_argument(
        "--concurrency",
        default="1,2,3,6",
        help="load mode: comma-separated client worker counts (default 1,2,3,6)",
    )
    p.add_argument(
        "--pop-size",
        type=int,
        default=6,
        help="load mode: EoH pop_size analog (default 6)",
    )
    p.add_argument(
        "--n-gen",
        type=int,
        default=3,
        help="load mode: generation count analog (default 3)",
    )
    p.add_argument(
        "--parallel-timeout",
        type=int,
        default=3600,
        help="joblib Parallel timeout seconds (default 3600)",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    prompt_path = Path(args.prompt_file)
    if not prompt_path.is_file():
        raise SystemExit(f"prompt file not found: {prompt_path}")
    prompt = prompt_path.read_text()
    print(
        f"# probe mode={args.mode} endpoint={args.endpoint} "
        f"model={args.model} prompt_len={len(prompt)} "
        f"request_timeout={args.request_timeout} total_timeout={args.total_timeout}"
    )

    if args.mode == "quality":
        records = run_quality(args, prompt)
        summary: dict[str, Any] = summarize(records)
    else:
        records = run_load(args, prompt)
        summary = {
            "overall": summarize(records),
            "by_concurrency": summarize_by_concurrency(records),
        }

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))

    if args.report_out:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "mode": args.mode,
                    "endpoint": args.endpoint,
                    "model": args.model,
                    "prompt_len": len(prompt),
                    "records": [asdict(r) for r in records],
                    "summary": summary,
                },
                indent=2,
            )
        )
        print(f"\nreport saved to {out}")


if __name__ == "__main__":
    main()
