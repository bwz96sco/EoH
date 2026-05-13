# grok2api Stability Probe

`experiments/grok2api_probe.py` measures grok2api health the way EoH sees it. It reuses the exact production HTTP client (`eoh.llm.api_general.InterfaceAPI`) and the same multi-process shape (`joblib.Parallel` with loky backend) as EoH's `get_algorithm`, so any failure the probe sees is one EoH would also see.

The probe does **not** modify the production client. If it detects a pattern (e.g., high `empty_200_rate`) that should be caught at the client level, that's a follow-up task; the probe itself only measures.

## When to run

- Before a new 3G EoH campaign: confirm server is healthy and pick a sensible `EXP_N_PROC`.
- Right after grok2api upgrade / config change on heyun.
- When live runs start failing with `RemoteDisconnected`, `BrokenPipeError`, or `parse_error` — probe is the fastest way to attribute the cause.

## Two modes

### `quality` — single-process response-quality test

Sequential long-prompt calls; measures content-length distribution, `empty_200_rate`, latency, and first-vs-reused-connection delta (quantifies keep-alive savings).

```bash
uv run python experiments/grok2api_probe.py --mode quality \
    --n-calls 30 \
    --endpoint http://127.0.0.1:8000 \
    --model grok-4.20-fast \
    --request-timeout 300 --total-timeout 600 \
    --prompt-file experiments/grok2api_probe_sample_prompt.txt \
    --report-out /tmp/probe-quality-$(date +%s).json
```

### `load` — multi-process transport / capacity test

Mirrors EoH's `get_algorithm` shape. Sweeps `--concurrency` across comma-separated values; for each N it spawns N joblib workers, each running `pop_size * n_gen / N` calls. Reports per-concurrency `success_rate` / `empty_200_rate` / `transport_error_rate`.

```bash
uv run python experiments/grok2api_probe.py --mode load \
    --concurrency 1,2,3,6 --pop-size 6 --n-gen 3 \
    --endpoint http://127.0.0.1:8000 \
    --model grok-4.20-fast \
    --report-out /tmp/probe-load-$(date +%s).json
```

## Outputs

- **stdout**: one JSON line per call (easy to `| jq`), then a final `=== SUMMARY ===` block.
- **`--report-out`** file (optional): JSON with `{mode, endpoint, model, prompt_len, records: [...], summary: {...}}`.

Per-call record schema:

```json
{
  "t": "2026-04-21T14:05:01Z",
  "mode": "load",
  "worker": 3,
  "concurrency": 6,
  "call_idx": 12,
  "http_attempts": 1,
  "content_len": 0,
  "elapsed_ms": 812.3,
  "error_type": null,
  "status": "empty_200",
  "content_preview": ""
}
```

`status` values: `success` (non-empty content), `empty_200` (HTTP 200 but content empty), `<error_type>` (one of `RemoteDisconnected`, `BrokenPipeError`, `TimeoutError`, …), `probe_exception` (probe itself crashed on a call), `no_response` (InterfaceAPI gave up).

## A/B matrix

| Axis | Values | Who changes it |
|---|---|---|
| `--mode` | `quality`, `load` | probe arg |
| `--concurrency` (load) | `1`, `2`, `3`, `6` | probe arg |
| `SERVER_WORKERS` (grok2api) | `1`, `2` | operator, on heyun (systemctl / env edit + restart) |

## Decision rules

Read the summary. Interpret in this order:

1. **`empty_200_rate > 5%`** → dominant failure is **server-side response quality**. keep-alive and concurrency tuning will not fix this. Follow-up: either (a) chase the upstream root cause in grok2api (look for `text_len=0` in `journalctl -u grok2api`), or (b) open a task to make `eoh.llm.api_general.InterfaceAPI.get_response` raise on empty content so `_reset_connection` + HTTP-level retry replaces EoH's `_get_alg` 4× prompt-attempt amplification.
2. **`transport_error_rate` jumps between `concurrency=3` and `6`** → **capacity cliff**. Keep `EXP_N_PROC ≤ last clean concurrency` for the next campaign. Consider raising `SERVER_WORKERS` (see step 4).
3. **`first_vs_reused.delta_ms > 200ms`** → keep-alive is pulling real weight; do not regress `cf9ecc5`.
4. **`workers=2` worse than `workers=1`** (replicate what codex saw 04-21) → production stays `workers=1`, client concurrency stays ≤ 3. **`workers=2` better** → revisit whether `EXP_N_PROC=6` is safe with a dual-worker backend plus separated data directories (see drawer `drawer_eoh_default_c06821b1` on the `.scheduler.lock` trap).
5. If none of the above fires and `success_rate` is still low → likely a prompt-shape or model mismatch; rerun `quality` with a shorter `--prompt-file` to isolate.

## Heyun first-round runbook

From the remote EoH checkout on heyun:

```bash
source experiments/private/backup.env   # exports LLM_API_ENDPOINT, LLM_API_KEY, LLM_MODEL

# (a) quality baseline under current config
uv run python experiments/grok2api_probe.py --mode quality --n-calls 30 \
    --report-out /tmp/q-w1.json

# (b) load sweep at SERVER_WORKERS=1
for N in 1 2 3 6; do
  uv run python experiments/grok2api_probe.py --mode load --concurrency "$N" \
      --pop-size 6 --n-gen 3 --report-out "/tmp/l-w1-n${N}.json"
done

# (c) switch grok2api to SERVER_WORKERS=2 (careful: stop sidecars on 8001/8002)
#     sudo systemctl stop grok2api
#     edit service unit / env file: SERVER_WORKERS=2
#     confirm no other granian holds the shared data dir / .scheduler.lock
#     sudo systemctl start grok2api
#     curl -s http://127.0.0.1:8000/v1/models | head  # sanity

# (d) same load sweep at SERVER_WORKERS=2
for N in 1 2 3 6; do
  uv run python experiments/grok2api_probe.py --mode load --concurrency "$N" \
      --pop-size 6 --n-gen 3 --report-out "/tmp/l-w2-n${N}.json"
done
```

After the runs, pull the `/tmp/l-w*.json` files back, or compare them in place with jq:

```bash
for f in /tmp/l-w*-n*.json; do
  jq -r '[input_filename, .summary.overall.success_rate, \
          .summary.overall.empty_200_rate, \
          .summary.overall.transport_error_rate] | @tsv' "$f"
done
```

Fill out a short report in the task `research/` directory (or `experiments/campaign_data/grok2api-stability-probe/`) with the three decisions:

- **Dominant failure class**: `empty_200` / `transport` / `capacity` / `mixed`
- **Client concurrency cliff**: last N where `transport_error_rate < 1%` and `success_rate > 0.9`
- **Workers=1 vs 2 verdict**: pick one, quote numbers

## Regenerating the sample prompt

The committed `experiments/grok2api_probe_sample_prompt.txt` is synthetic (see `experiments/_build_grok2api_probe_sample_prompt.py`). If EoH's e1 prompt template changes materially, rebuild it:

```bash
uv run python experiments/_build_grok2api_probe_sample_prompt.py
```

You can also point the probe at a real dumped e1 prompt via `--prompt-file` if you want to stress on the exact shape an ongoing run is emitting.

## What the probe does *not* do

- It does not restart grok2api for you. `SERVER_WORKERS` switches are manual operator actions.
- It does not modify `eoh.llm.api_general.InterfaceAPI`. Any client-side fix is a follow-up task, landed after the probe proves it's needed.
- It does not run any ABR evaluation. It only exercises the LLM HTTP path.
