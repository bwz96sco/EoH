# Grok2api Stability Probe

## Goal
Deliver a reusable probe tool (`experiments/grok2api_probe.py`) and first-round heyun report that tells the next 3G EoH campaign **which `EXP_N_PROC` × `SERVER_WORKERS` combination is a stable operating envelope**, and which failure class dominates (empty-content 200 / transport drops / capacity saturation). Future grok2api jitter should be diagnosed by re-running the probe rather than ad hoc by codex.

## Background
heyun's grok2api path has shown three distinct failure modes across 04-13 → 04-21:
- HTTP 200 with `content=""` (codex smoke 6/10, server logs show `text_len=0`).
- `RemoteDisconnected` / `BrokenPipeError` on long-prompt e1 calls.
- Scheduler lock / ASGI SendError when `SERVER_WORKERS>1` shares data dir with sidecars.

`cf9ecc5` added client keep-alive + per-exception reset, which helps transport but does not touch response quality. The probe must quantify which class dominates today, so the next fix (client-side empty-content detection, server worker reconfig, preflight gate, etc.) is evidence-driven rather than speculative.

## Requirements
- `experiments/grok2api_probe.py` imports `eoh.llm.api_general.InterfaceAPI` and `joblib.Parallel` (loky backend) so probe and production go through identical HTTP + concurrency code paths.
- Two modes:
  - `quality`: single-process, N sequential long-prompt calls; reports content-length distribution, empty-200 rate, p50/p95/p99 latency, first-vs-reused-connection latency delta.
  - `load`: multi-process via `joblib.Parallel`, with `--concurrency 1,2,3,6` sweep, `--pop-size` and `--n-gen` parameters matching EoH's `get_algorithm` shape. Reports per-concurrency `success_rate` / `empty_200_rate` / `transport_error_rate` (`error_type ∈ {RemoteDisconnected, BrokenPipeError, TimeoutError, socket.timeout}`).
- Emit JSONL per call (`{worker, call_idx, http_attempts, content_len, elapsed_ms, error_type, status}`) plus a summary JSON; path controlled by `--report-out`.
- Empty-content detection lives **in the probe script** (probe flags `""` responses as `empty_200`). Do not change `eoh/src/eoh/llm/api_general.py` in this task.
- Use a repo-tracked synthetic ~15k-character e1-shaped prompt at `experiments/grok2api_probe_sample_prompt.txt`, built from the template in `eoh/src/eoh/methods/eoh/eoh_evolution.py:96-111` with fake parent algorithm/code strings. Allow `--prompt-file` override.
- `experiments/grok2api_probe_README.md` documents the A/B matrix (client concurrency × server workers), the decision rules for interpreting empty-200 / transport / capacity signals, and the exact command sequence for a first-round run on heyun.
- First-round report produced on heyun covering: (a) quality baseline under current config, (b) load sweep N=1,2,3,6 under `SERVER_WORKERS=1`, (c) repeat of (b) under `SERVER_WORKERS=2` (after cleaning sidecar granian 8001/8002 per drawer_c06821b1). Report saved under `experiments/campaign_data/grok2api-stability-probe/` or task research/.

## Acceptance Criteria
- [ ] `experiments/grok2api_probe.py` exists, `uv run python experiments/grok2api_probe.py --help` prints both mode signatures.
- [ ] `uv run python -c "from eoh.llm.api_general import InterfaceAPI"` works from this repo root (import path is valid).
- [ ] `experiments/grok2api_probe_README.md` contains the A/B matrix table and decision rules.
- [ ] `experiments/grok2api_probe_sample_prompt.txt` is ≥12k characters and round-trips through `InterfaceAPI.get_response` on a local dry run.
- [ ] First-round JSON reports (`/tmp/q-w1.json`, `/tmp/l-w{1,2}-n{1,2,3,6}.json`) produced on heyun, compared side-by-side in a short markdown report pasted into the task `research/` directory or into session.
- [ ] Report gives a concrete answer to: dominant failure class, client concurrency cliff, workers=1 vs 2 verdict.

## Technical Notes
- Worktree policy: per drawer_71169aa4, code goes in a dedicated worktree (`experiment/grok2api-stability-probe` or similar); this task directory stays in the primary checkout for bookkeeping.
- Do not mutate `eoh/src/eoh/llm/api_general.py` or any EoH core in this task. Any change there is a follow-up task after the probe report judges it necessary.
- Server-side `SERVER_WORKERS` changes on heyun are operator actions done outside this repo; the probe just records what it measures.
- The probe must tolerate `InterfaceAPI.get_response` returning `None` or `""` without crashing, and log both distinctly.

## Follow-up Candidates (out of scope for this task)
- If empty_200_rate > 5%: open a task to make `InterfaceAPI.get_response` raise on empty content so `_reset_connection` + HTTP retry take over (avoid `_get_alg`'s 4× prompt_attempts amplification).
- Add a `Phase 0` preflight gate to `experiments/run_eoh_target_experiment.sh` that runs the probe quality mode before launching, with a fail threshold.
- Keep-alive stale detection (track `_last_used_ts`, close on long idle) if probe shows idle-close as a frequent failure.
- Push fixes upstream to grok2api if `text_len=0` is attributable to server-side bug.
