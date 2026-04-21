# Grok2api Stability Probe — First Round Report (heyun, 2026-04-21)

> Probe run against heyun's production grok2api (`http://127.0.0.1:8000`, `grok-4.20-fast`, `LLM_REQUEST_TIMEOUT_S=180`, `LLM_TOTAL_TIMEOUT_S=360`). `eoh/src/eoh/llm/api_general.py:InterfaceAPI` includes the cf9ecc5 keep-alive connection reuse. `SERVER_WORKERS=1` on port 8000 (confirmed via `ss -tlnp` — single granian master + one worker). Total probe wall clock ≈ 15 minutes (30-call quality + 4-level load sweep with 18 calls each).

## Baseline environment snapshot (captured before probe)

- `grok2api.service`: active, single granian master (pid 545871) + one worker (545867)
- Listening on `:8000` only (no sidecar on 8001/8002 during probe — `drawer_c06821b1` trap avoided)
- `curl /v1/models` with no auth: HTTP 401 in ~5 ms (fast control plane)
- `~/code/EoH-repro` `.venv/bin/python` imports `eoh.llm.api_general.InterfaceAPI` cleanly
- LLM creds sourced from `examples/user_abr/.env`
- Probe: 4 files scp'd into `~/code/EoH-repro/experiments/` from local worktree `experiment/grok2api-stability-probe` at commit 0c06113

## Quality probe (single process, n=30)

| Metric | Value |
|---|---|
| success_rate | **100 %** (30 / 30) |
| empty_200_rate | **0 %** |
| transport_error_rate | **0 %** |
| HTTP attempts: 1 / 2 / ≥3 | 28 / 2 / 0 |
| Latency p50 | 13.2 s |
| Latency p95 | 15.7 s |
| Latency p99 / max | 22.2 s |
| Content length range | 2490 – 3884 (mean 3193) |
| Keep-alive delta (first vs reused mean) | **−2060 ms** |

Both retry cases are grok2api surfacing upstream HTTP 429 from Grok. After `InterfaceAPI._reset_connection` + backoff, the second attempt succeeds. cf9ecc5 keep-alive saves ~2 s per call on the 15k-char synthetic e1 prompt.

## Server-side log sanity (during probe window)

```
journalctl -u grok2api --since "15 min ago" | grep -c text_len=0         → 0
journalctl -u grok2api --since "15 min ago" | grep -c "429|upstream|error" → 19
```

Every server-side `status=429` line is paired with a following `chat request completed attempt=2/2 text_len=N` (grok2api's internal retry recovered). No `ASGI transport error` / `SendError` in the window. `text_len=0` count is zero.

## Load sweep — SERVER_WORKERS=1

(pop_size=6, n_gen=3 → total target 18 calls per concurrency level; joblib loky workers each build their own `InterfaceAPI`)

| N | total | success | empty_200 | transport_err | p50 | p95 | mean | http_attempts dist |
|---|-------|---------|-----------|---------------|------|------|------|--------------------|
| 1 | 18 | 100 % | 0 % | 0 % | 12.7 s | 15.7 s | 12.8 s | {1: 16, 2: 2} |
| 2 | 18 | 100 % | 0 % | 0 % | 14.1 s | 20.0 s | 15.2 s | {1: 13, 2: 2, 3: 3} |
| 3 | 18 | 100 % | 0 % | 0 % | 14.4 s | 17.5 s | 15.0 s | {1: 14, 2: 3, 3: 1} |
| 6 | 18 | 100 % | 0 % | 0 % | 12.5 s | 14.7 s | 12.7 s | {1: 16, 2: 2} |

Retry totals (rate-limit collisions): N=1→2, N=2→5, N=3→4, N=6→2. **No transport errors (RemoteDisconnected / BrokenPipe / TimeoutError) across any concurrency level.** Per-call latency does NOT inflate with N, which contradicts the a-priori expectation that `SERVER_WORKERS=1` would serialize and queue. Most likely explanation: granian's single worker has async I/O that overlaps upstream waits across concurrent requests, so concurrency does not impose wall-time cost.

`first_vs_reused` delta is only meaningful in the quality (single-process) row; in the load rows, "call_idx=0" is per-worker so all workers pay the handshake simultaneously on launch. The quality delta of −2060 ms is the clean keep-alive benefit measurement.

## Decisions

### Dominant failure class

**Upstream Grok HTTP 429 rate limit**, not `empty_200` and not transport. Across 120 probe calls (30 quality + 4×18 load) there were **zero empty-content responses** and **zero transport errors**. The 04-21 morning observation of 6/10 empty_200 from codex has cleared up — likely because (a) upstream Grok rate window recovered, and/or (b) grok2api on heyun is currently running clean single-worker with no sidecars on 8001/8002. The synthetic probe prompt may also be slightly easier for Grok than a real EoH e1 prompt; a real-campaign probe remains necessary to fully dismiss the empty_200 risk.

### Client concurrency cliff

**No cliff observed up to N=6 under SERVER_WORKERS=1.** `success_rate` is a flat 100 % across N=1/2/3/6. Per-call latency mean stays ~12–15 s. Retry density rises at N=2/3 (upstream 429 pressure) but the backoff path handles it and final success rate is unaffected.

**Practical conclusion for next 3G campaigns: `EXP_N_PROC=6` is safe under the current heyun state.** This contradicts the working hypothesis I coded into the probe README ("`EXP_N_PROC ≤ 3` because server is serial"). The probe falsified that hypothesis. Keep the pre-campaign probe as a mandatory preflight so the recommendation stays evidence-driven run to run.

### Workers=1 vs 2 verdict

**Deferred.** Not rerun under `SERVER_WORKERS=2` because:
1. Under the current `SERVER_WORKERS=1`, N=6 already shows 100 % success and flat latency. There is no problem to solve by adding a second worker.
2. Switching workers requires operator action (edit service unit + restart + verify no sidecar regresses). It also re-exposes the `drawer_c06821b1` scheduler-lock trap.
3. Codex's 04-21 morning observation in `drawer_eoh_default_65c21fe1` already judged `workers=2` materially worse than `workers=1`.

If a future campaign shows `EXP_N_PROC > 6` is needed, revisit this. Otherwise, the default stays `SERVER_WORKERS=1`.

## Operational recommendations (interim)

1. **Default campaign config**: `SERVER_WORKERS=1` on grok2api, `EXP_N_PROC=6` on EoH, `LLM_REQUEST_TIMEOUT_S=180`, `LLM_TOTAL_TIMEOUT_S=360`, `grok-4.20-fast` — this matches `drawer_eoh_default_c06821b1` and is now backed by load-sweep evidence.
2. **Keep cf9ecc5**: the keep-alive savings are real (~2 s/call, ~15 % of total latency). Do not regress.
3. **No client-side code change indicated**: empty-content detection in `InterfaceAPI` is not triggered by this round. Reopen only if a future probe shows `empty_200_rate ≥ 5 %`.
4. **Preflight gate** in `experiments/run_eoh_target_experiment.sh` is viable: the 30-call quality probe takes ~7 min, catches outages before wasting a 3-hour campaign. Candidate for a follow-up task.
5. **Probe re-run cadence**: before every new 3G campaign, after any grok2api upgrade, or when live runs start showing `parse_error` / `RemoteDisconnected` bursts.

## Raw artifacts (in this directory)

- `q-w1.json` — quality run, 30 calls
- `l-w1-n1.json` — load sweep N=1
- `l-w1-n2.json` — load sweep N=2
- `l-w1-n3.json` — load sweep N=3
- `l-w1-n6.json` — load sweep N=6

Server-side artifacts remain under `/tmp/` on heyun: `q-w1.json`, `l-w1-n{1,2,3,6}.json`, `load-sweep-w1.log`, `run-load-sweep.sh`.

## Followup task candidates (not started)

- **Phase 0 preflight gate** in `run_eoh_target_experiment.sh`: invoke probe quality mode, fail-fast if `success_rate < 0.9` or `empty_200_rate > 0.05`.
- **Real-campaign probe replication**: after the next 3G campaign run, re-probe with the *actual* e1 prompt captured from that run to confirm the synthetic prompt is a fair proxy.
- **Long-horizon probe mode**: an hour-long continuous load probe, to surface drift / idle-timeout effects the 18-call snapshot cannot see.
