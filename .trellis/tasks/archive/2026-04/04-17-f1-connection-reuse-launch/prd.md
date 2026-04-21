# F1 Connection Reuse Sync And Launch

## Goal
Sync the remote-validated LLM connection reuse client improvement into the local main checkout, then launch the `F1` 3G exploit experiment remotely from an isolated experiment checkout.

## Requirements
- Copy the remote-validated connection reuse implementation for `eoh/src/eoh/llm/api_general.py` into the local main checkout.
- Keep experiment-only F1 seed changes isolated from the main checkout.
- Launch the remote `F1` run on `heyun` using `EXP_N_PROC=6` as an explicit throughput test.
- Keep campaign bookkeeping in the main local repo and use the existing `3g-exploit-round1` campaign.

## Acceptance Criteria
- [ ] Local main checkout contains the connection reuse implementation used by the stable remote setup.
- [ ] Shared LLM client code still parses and passes a minimal smoke check.
- [ ] A dedicated remote checkout exists for `F1`.
- [ ] The remote `F1` run is launched with explicit env settings, including `EXP_N_PROC=6`.
- [ ] Run startup details and any immediate risk observations are reported back.

## Technical Notes
- GitNexus impact on `get_response` is HIGH because it affects the shared LLM client path across EOH/AEL/LS. Keep the interface unchanged and apply the smallest validated diff.
- `heyun` currently runs `grok2api` on `127.0.0.1:8000` with `SERVER_WORKERS=1`; `EXP_N_PROC=6` is an aggressive experiment setting, not the stable default.
