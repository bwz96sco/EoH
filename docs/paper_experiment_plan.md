# Paper Experiment Plan: OpenRouter-Reproduced EoH vs SABR for ABR

## Paper Story

**Paradigm comparison**: interpretable evolved heuristics (EoH) vs black-box BC+RL (SABR) for adaptive bitrate streaming.

The paper-facing experiment policy is now:

1. All EoH results used in main paper tables must be regenerated through OpenRouter.
2. Previous mixed-provider results are pilot evidence only. They can guide experiment design, expected score ranges, artifact checks, and appendix discussion, but they should not be reported as final EoH evidence.
3. Every OpenRouter run must preserve enough request, routing, cost, timeout, and artifact metadata to make the result auditable.

Key claims after the OpenRouter reproduction:

1. EoH evolves interpretable ABR heuristics that are competitive with or stronger than SABR on in-domain benchmarks.
2. EoH requires no expert demonstrations or offline RL policy-training dataset; it uses simulator-based fitness evaluation.
3. Evolved heuristics show non-trivial cross-regime transfer, but direct in-domain evolution is expected to remain best.
4. The evolutionary framework is not tied to one LLM backbone only if the OpenRouter-controlled model-sensitivity runs confirm this under a shared API path.

Recommended claim wording before formal runs finish:

> Pilot experiments suggest that EoH can evolve interpretable ABR heuristics competitive with SABR while requiring no demonstrations or offline policy-training dataset. For the paper, all EoH tables will be regenerated through a single OpenRouter-based experiment stack so that model, provider route, timeout, and cost effects are explicit.

Recommended claim wording after successful formal runs:

> Under a reproducible OpenRouter-based evaluation stack, EoH evolves interpretable ABR heuristics that are competitive with or stronger than SABR on in-domain ABR benchmarks, require no expert demonstrations or offline policy-training dataset, and show non-trivial cross-regime transfer. Backbone-sensitivity results show how much performance varies across LLM families under the same gateway.

---

## Formal Reproduction Rules

### OpenRouter substrate

Use OpenRouter for every paper-facing EoH evolution run:

- Base URL: `https://openrouter.ai/api/v1`
- Chat completion path: `/chat/completions`
- Request mode: OpenAI-compatible chat completion, `stream=false`
- Model selection: fixed OpenRouter model ID, not provider-native aliases
- Routing: explicit raw-JSON `provider` object whenever possible, using OpenRouter field names such as `order`, `only`, `allow_fallbacks`, and `require_parameters`
- Strict routing: for formal model/provider comparisons, use an exact provider slug in `provider.order` or `provider.only` plus `allow_fallbacks=false`; if no exact provider can be pinned, label the condition as an OpenRouter gateway run rather than a strict provider-pinned run
- Fallbacks: disabled for strict comparisons; if fallback or load balancing is intentionally enabled, report it as part of the experimental condition
- Metadata: send `session_id`, `metadata`, and tracing fields where supported; enable OpenRouter routing metadata in responses when available

Required implementation update before formal runs:

- Extend `eoh/src/eoh/llm/api_general.py` so `InterfaceAPI` can pass OpenRouter-specific request fields and headers from environment/config.
- Required request fields: `provider`, `metadata`, `session_id`, optional `trace`, and optional `seed`.
- Required headers: `HTTP-Referer`, `X-Title` or `X-OpenRouter-Title`, and `X-OpenRouter-Experimental-Metadata` if routing metadata is needed.
- Required logging: raw response `model`, `usage`, `system_fingerprint`, `openrouter_metadata`, HTTP status, error body excerpt, retry count, timeout status, and wall-clock latency.

The current `InterfaceAPI` only sends `{model, stream, messages}`. It already has hard timeout support, but it must become OpenRouter-aware before any final paper run.

### Frozen run manifest

Create one immutable manifest for each formal campaign:

| Field | Requirement |
|-------|-------------|
| Manifest ID | Date-stamped campaign ID, for example `202605-openrouter-main-3g-v1` |
| Code state | Git commit hash, dirty diff if any, runner command, Python/uv environment lock state |
| Dataset state | ABRBench split, trace list, simulator parameters, QoE formula, chunk count, penalty coefficients |
| LLM state | OpenRouter model ID, model object snapshot from `/api/v1/models`, provider routing object, headers, timeout policy |
| EoH state | Seed heuristic, population size, generations, random seed, prompt template hash, parser/evaluator hash |
| Execution state | `EXP_N_PROC`, retry policy, machine, start/end time, API errors, invalid offspring, token usage, estimated cost |
| Artifact state | Output directory, population files, best heuristic, per-generation best QoE, evaluation summary |

Store the manifest beside the run artifacts and copy a compact summary into the experiment tracker.

### Validity rule

A run is paper-valid only if:

- It uses the formal OpenRouter endpoint.
- It uses the frozen manifest for that campaign.
- It records OpenRouter route/usage metadata or explicitly records that metadata was unavailable.
- It completes the planned generations and evaluation without manual cherry-picking.
- Failed API calls, invalid offspring, and timeouts are included in the run report.

If a provider route fails, do not silently switch to another provider for a strict comparison. Mark the run failed and reschedule under the same manifest, or create a new manifest if the route policy changes.

---

## Pilot Evidence Summary

These results are useful for design and sanity checks only.

### In-domain pilots

| Regime | Provider path | Model | Seed/init mode | Pop | Budget note | Avg QoE | Pilot interpretation |
|--------|---------------|-------|----------------|-----|-------------|---------|----------------------|
| ABRBench-3G | grok2api | `grok-4.20-beta` | mixed all built-in seeds | 25 | tracker label `exp12` | 87.6 | Prior mixed-population reference: `20260401-132132-mixed-pop25-exp12` |
| ABRBench-3G | grok2api | `grok-4.20-beta` | quetra | 25 | 10 generations | 88.9 | Strong A1 heuristic; use as expected-range reference |
| ABRBench-4G+ | Vertex AI | `gemini-2.5-flash` | quetra | 25 | 10 generations | 1578.1 | Strong target-domain pilot; verify ceiling/artifact risk |

Pilot 3G mixed-pop25 and A1 both beat online baselines, with A1/QUETRA stronger than the mixed-pop25 pilot. For paper reproducibility and reviewer robustness, use the OpenRouter mixed-pop25 design as the formal main-table protocol, while keeping A1/QUETRA as an internal expected-range reference. Pilot 4G+ beat SABR on 6/6 datasets, but the very high Solis-Wi-Fi and repeated `1842.5` ceiling-like values must be checked before they influence the paper story.

### Transfer pilots

| Direction | SABR Avg | Pilot EoH Avg | Delta | Wins | Interpretation |
|-----------|----------|---------------|-------|------|----------------|
| 3G -> 4G+ | 1188.6 | 1027.4 | -13.6% | 0/6 | Useful negative control; source-domain heuristic does not replace target-domain evolution |
| 4G+ -> 3G | 83.3 | 85.5 | +2.7% | 4/6 | Non-trivial rule-level transfer, but below direct 3G evolution |

### Legacy model/provider pilots

| Existing model | Provider path | 3G QoE avg | Paper-readiness concern |
|----------------|---------------|------------|--------------------------|
| `grok-4.20-beta` | grok2api | 84.4 | Legacy proxy route; provider behavior differs from OpenRouter |
| `gemini-2.5-flash` | Vertex AI | 83.6 | Same model family as 4G+ pilot but direct provider transport |
| `gemini-2.5-pro` | Vertex AI | 81.7 | Direct provider path; less useful for gateway-controlled comparison |
| `gemini-2.0-flash-lite` | Vertex AI | 75.7 | Weaker model and different provider behavior |
| `GLM-5.1` | SiliconFlow | 75.7 | Provider and model family both change |
| `claude-sonnet-4-6-thinking` | hybgzs | 87.6 | Useful pilot; provider-specific route |
| `gpt-5.4-mini` | hybgzs | 85.3 | Clean serial pilot; not an OpenRouter result |

Failed or saturated starts, especially `EXP_N_PROC=4` HTTP 429 cases, are provider-capacity evidence, not model-quality evidence.

---

## Formal Experiment Table 1: Main In-Domain Results

**Goal**: Reproduce the main EoH vs SABR comparison using OpenRouter-generated EoH heuristics only.

### Formal common setup

- Datasets: ABRBench-3G and ABRBench-4G+
- Initial population: mixed all-seed population with five seed families, `quetra`, `rate_based`, `bb`, `bola`, and `robust_mpc`
- Population/generations: pop=25, 10 generations
- Fitness: mean QoE over the target training/evaluation set, matching the current EoH setup
- Minimum formal unit: one completed OpenRouter mixed-pop25 run per regime
- Preferred formal unit: 3 independent OpenRouter mixed-pop25 repeats per regime
- Report: mean +/- std across independent mixed-pop25 repeats; include initial-population composition and best-run heuristic in appendix
- SABR comparison: use SABR paper values and average-rank methodology; if SABR code/artifacts are available, rerun them separately and label the source

### Mixed-seed main-table protocol

The main EoH row should not be a QUETRA-only result. QUETRA is the strongest pilot seed and is useful as an internal anchor, but using it alone creates a plausible reviewer objection that the result is seed-selected. The paper-facing protocol should follow the previous mixed-population design: one pop=25 run initialized from all five seed families, with five initial individuals per family.

Implementation note confirmed from prior records and the runner:

- Prior record: `20260401-132132-mixed-pop25-exp12` is listed as `mixed seeds, pop=25`.
- Current `examples/user_abr/runEoH.py` expands the selected seed list round-robin when `EC_POP_SIZE` exceeds the number of selected seeds.
- With five built-in seeds and `EC_POP_SIZE=25`, the initial population contains 25 seed individuals: five from each seed family.

For each network regime, use this initial population:

| Seed family | Initial individuals | Role in Table 1 |
|-------------|---------------------|-----------------|
| `quetra` | 5 | Included in one mixed pop=25 initialization |
| `rate_based` | 5 | Included in one mixed pop=25 initialization |
| `bb` | 5 | Included in one mixed pop=25 initialization |
| `bola` | 5 | Included in one mixed pop=25 initialization |
| `robust_mpc` | 5 | Included in one mixed pop=25 initialization |

Primary Table 1 value: average over independent OpenRouter repeats of this mixed-pop25 initialization. Appendix value: initial-population composition plus, if useful, lineage/parent-family analysis of final best heuristics. Do not average five separate seed-only campaigns as the main result.

### ABRBench-3G formal table

| Method | Type | FCC-16 | FCC-18 | Oboe | Puffer-21 | Puffer-22 | HSR | Avg | Ave Rank |
|--------|------|--------|--------|------|-----------|-----------|-----|-----|----------|
| BB | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| BOLA | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| QUETRA | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| RobustMPC | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| SABR | BC+RL | 36.68 | 145.18 | 99.68 | 36.05 | 40.05 | 142.20 | TBD | 1.8 |
| EoH-OpenRouter (mixed pop25) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Status**: Formal OpenRouter mixed-pop25 rerun pending. Pilot expected range: mixed-pop25 reached `87.5768` on 3G, while A1/QUETRA reached `88.9`; do not report either as final.

### ABRBench-4G+ formal table

| Method | Type | Norway3G | Lumos4G | Lumos5G | SolisWi-Fi | Ghent | Lab | Avg | Ave Rank |
|--------|------|----------|---------|---------|------------|-------|-----|-----|----------|
| SABR | BC+RL | 57.7 | 1711.9 | 1836.6 | 669.8 | 1188.9 | 1666.7 | 1188.6 | 1.7 |
| EoH-OpenRouter (mixed pop25) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Status**: Formal OpenRouter mixed-pop25 rerun pending. Before running the full campaign, verify whether the pilot `1842.5` ceiling-like values are valid simulator outcomes or an evaluation artifact.

### Formal anchor model choice

Use one primary OpenRouter anchor model for both 3G and 4G+ main tables. Candidate anchor choice should be frozen after smoke tests:

| Candidate | Why consider it | Decision rule |
|-----------|------------------|---------------|
| `x-ai/grok-4.3` | Current Grok-family OpenRouter route, replacing the older `x-ai/grok-4.20` candidate | Prefer if route is stable and cost is acceptable |
| `google/gemini-3-flash-preview` | Current Gemini-family OpenRouter route, replacing `google/gemini-2.5-flash` for formal runs | Prefer if Grok route is unstable or too expensive |
| `openai/gpt-5.4-mini` | Strong cost-controlled GPT-family pilot signal | Use as backup anchor or backbone-sweep member |

Once selected, the anchor must remain fixed for the main results, transfer study, initialization-composition analysis, population ablation, and convergence curve. Other models belong in the LLM sensitivity table only.

---

## Formal Experiment Table 2: Zero-Shot Transfer

**Goal**: Evaluate whether OpenRouter-evolved heuristics transfer across network regimes without target-domain evolution.

### Formal design

| Transfer direction | Source heuristic | Target evaluation | Required runs | Report |
|--------------------|------------------|-------------------|---------------|--------|
| 3G -> 4G+ | Formal 3G OpenRouter mixed-pop25 heuristics | ABRBench-4G+ | Same formal repeat set | Per-dataset QoE, avg, wins vs SABR |
| 4G+ -> 3G | Formal 4G+ OpenRouter mixed-pop25 heuristics | ABRBench-3G | Same formal repeat set | Per-dataset QoE, avg, wins vs SABR |

Use the same OpenRouter anchor model and mixed-pop25 protocol as Table 1. Transfer should be reported as secondary evidence. It should not be framed as replacing in-domain evolution unless it beats or matches the direct in-domain OpenRouter result.

### Pilot reference ranges

| Direction | Pilot result | Use in formal design |
|-----------|--------------|----------------------|
| 3G -> 4G+ | Avg `1027.4`, 0/6 wins vs SABR | Expect transfer to be below direct 4G+ evolution |
| 4G+ -> 3G | Avg `85.5`, 4/6 wins vs SABR | Expect useful but not best-in-paper transfer |

---

## Formal Experiment Table 3: OpenRouter LLM Backbone Sensitivity

**Goal**: Measure LLM-family sensitivity while keeping endpoint, prompt, seed heuristic, population, generations, dataset, parser, evaluator, timeout policy, and logging fixed.

### Design

- Dataset: ABRBench-3G first; add 4G+ only if results are central to the paper.
- Seed policy: QUETRA-only is acceptable for the cheap pop=5 screening sweep, because the goal is controlled model comparison rather than a main performance claim.
- Budget tier: pop=5, 10 generations for sweep.
- Confirmation tier: pop=25, 10 generations for the top 2-3 families, using the mixed-pop25 initialization if the result will support a paper claim.
- Repetitions: one seed per model for the sweep; 3+ independent runs for promoted models.
- Invalid result rule: provider saturation, 429 storms, missing route metadata, or route fallback outside the manifest invalidates the run for model-quality comparison.

### Candidate roster

Refresh the roster from `https://openrouter.ai/api/v1/models?output_modalities=text` immediately before execution and save the model objects. The following IDs were visible in the OpenRouter models API check on 2026-05-13:

| Family | Candidate model ID | Role |
|--------|--------------------|------|
| xAI | `x-ai/grok-4.3` | Latest available Grok-family representative; replaces `x-ai/grok-4.20` in the formal sweep |
| Google | `google/gemini-3-flash-preview` | New Gemini-family representative; replaces `google/gemini-2.5-flash` in the formal sweep |
| OpenAI | `openai/gpt-5.4-mini` | Cost-controlled GPT-family representative |
| Anthropic | `anthropic/claude-sonnet-4.6` | Claude-family representative |
| DeepSeek | `deepseek/deepseek-v4-pro` | DeepSeek-family representative; use Pro rather than V3.2/V4 Flash for the formal sweep |
| Z.ai | `z-ai/glm-5.1` | GLM-family representative |
| MiniMax | `minimax/minimax-m2.7` | Independent Chinese-model family |

Do not use model aliases such as `latest` for the formal table. If a chosen ID expires or changes before execution, create a new manifest and record the replacement.

### Report fields

| Model ID | Provider route policy | Valid runs | 3G Avg QoE | Std | Invalid offspring | API error rate | Timeout rate | Tokens | Cost | Notes |
|----------|-----------------------|------------|------------|-----|-------------------|----------------|--------------|--------|------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### Expected narrative

The paper claim should be bounded: EoH may be robust across several LLM families, but the table should expose performance and reliability differences rather than hiding them. Provider reliability is a systems result; timeout and invalid-offspring rates help readers separate model reasoning quality from API instability.

---

## Formal Experiment Table 4: Ablations

All ablations must use the same OpenRouter anchor model and route policy as the main table unless the ablation explicitly studies LLM/model behavior.

### 4a: Initialization-composition analysis

**Goal**: Support the mixed-pop25 main-table result and show exactly how the initial population is constructed.

This is not a separate five-run seed ablation. It documents the seed composition inside the single pop=25 Table 1 initialization, and optionally analyzes which seed families survive as parents or ancestors of the final best heuristics.

| Seed family | Individuals in pop=25 | Single-seed pop5 pilot on 3G | Role |
|-------------|-----------------------|----------------------------|------|
| quetra | 5 | 87.0 | Included in mixed initialization |
| rate_based | 5 | 86.2 | Included in mixed initialization |
| bb | 5 | 85.9 | Included in mixed initialization |
| bola | 5 | 85.0 | Included in mixed initialization |
| robust_mpc | 5 | 84.8 | Included in mixed initialization |

Pilot data from `experiments/campaign_data/3g-seed-impact/` remains useful for context, but Table 1 should use the mixed-pop25 initialization, not five separate seed-only results averaged together.

### 4b: Population size effect

**Goal**: Quantify whether larger populations improve final heuristic quality under the same OpenRouter model.

| Pop size | Model | Seed protocol | Dataset | Formal QoE avg | Pilot reference | Status |
|----------|-------|---------------|---------|----------------|-----------------|--------|
| 5 | OpenRouter anchor | one individual per built-in seed, or QUETRA-only if explicitly labeled | 3G | TBD | grok pilot `84.4`, gemini pilot `83.6` | Formal rerun pending |
| 25 | OpenRouter anchor | mixed pop25, 5 individuals per built-in seed | 3G | TBD | mixed-pop25 pilot `87.5768`, A1/QUETRA pilot `88.9` | Formal rerun pending |
| 5 | OpenRouter anchor | one individual per built-in seed, or QUETRA-only if explicitly labeled | 4G+ | TBD | TBD | Optional |
| 25 | OpenRouter anchor | mixed pop25, 5 individuals per built-in seed | 4G+ | TBD | Vertex/QUETRA pilot `1578.1` | Formal rerun pending |

### 4c: Convergence curve

**Goal**: Show how quickly OpenRouter-EoH improves over generations.

Extract per-generation best and population mean QoE from `population_generation_*.json` files for the formal campaigns. Plot mean +/- std across independent runs where possible. This should be generated only from OpenRouter runs used in the paper tables.

### 4d: Best heuristic code showcase

**Goal**: Support interpretability.

For the final selected OpenRouter heuristic:

- Include compact pseudocode or a trimmed code block in the paper.
- Explain the main control logic in ABR terms.
- Link each explanation to the actual saved heuristic file.
- Avoid using the legacy A1 code as the main showcase unless it is reproduced or closely matched by a formal OpenRouter run.

---

## Experiment Priority Queue

| Priority | Experiment | Status | Estimated Time | Purpose |
|----------|------------|--------|----------------|---------|
| P0 | Implement OpenRouter-aware `InterfaceAPI` request/metadata support | Planned | 1-2h | Make formal runs auditable |
| P1 | Create frozen run manifest template and model snapshot script | Planned | 1h | Prevent undocumented provider/model drift |
| P2 | OpenRouter smoke tests for anchor candidates | Planned | 1-2h | Select stable anchor route |
| P3 | Verify Solis-Wi-Fi / 4G+ ceiling-like pilot scores | Planned | 1-2h | Remove evaluation-artifact risk |
| P4 | Formal 3G main campaign, mixed pop25, 5 individuals per seed family | Planned | 1-3 repeats | Main Table 1 without QUETRA-only seed selection |
| P5 | Formal 4G+ main campaign, mixed pop25, 5 individuals per seed family | Planned | 1-3 repeats | Main Table 1 without QUETRA-only seed selection |
| P6 | Formal transfer evaluation in both directions | Planned | 2-4h after P4/P5 | Table 2 |
| P7 | Average-rank computation matching SABR methodology | Planned | 2h | Paper metric consistency |
| P8 | OpenRouter population ablation under the selected mixed-population protocol | Planned | 10-30h | Table 4 |
| P9 | OpenRouter pop=5 backbone sweep | Planned | 10-20h | Table 3 |
| P10 | Pop=25 confirmation for 2-3 selected models | Planned | 15-30h per config | Backbone robustness claim |
| P11 | Convergence curve and best-heuristic extraction | Planned | 1-2h | Figures and interpretability evidence |

---

## Statistical Validity

SABR reports averaged results, so final EoH claims should not rely on a single lucky run or a single favorable seed heuristic.

- Minimum for Table 1: one OpenRouter mixed-pop25 run per regime, initialized with five individuals from each of the five built-in seed families.
- Preferred for Table 1: 3 independent OpenRouter repeats of the same mixed-pop25 protocol per regime.
- Report: mean +/- std across independent repeats, average rank, per-dataset wins/losses, and best-run heuristic separately.
- Always include the initial-population composition in the appendix; include lineage or parent-family analysis if the artifacts support it.
- Randomness: record EoH random seed, LLM model ID, provider route, and request-level seed if used.
- Failures: include failed runs in a reliability appendix; do not replace them silently.

---

## SABR Paper Reference

SABR paper: arXiv:2509.10486.

### QoE formula

```text
QoE = sum q(R_n) - delta * |q(R_{n+1}) - q(R_n)| - mu * sum T_n
q(R) = R
delta = 1
mu = 4.3 for 3G, 40 for 4G+
N = 49
```

### SABR reported results

- 3G average rank: 1.8
- 4G+ average rank: 1.7
- OOD average rank: 2.0
- Each method run 10 times, average reported

### Baselines in SABR paper

- Rule-based: BB, BOLA, QUETRA, RobustMPC
- RL-based: Pensieve, Comyco
- BC+RL: SABR

---

## Key Technical Details

### Pilot A1 heuristic

- Algorithm: future-sustainable heuristic
- 5th-percentile conservative throughput, 0.7 derating after rebuffer
- Myopic QoE plus proximity bonus to sustainable bitrate, scaled by 4.0
- Pilot model/provider: `grok-4.20-beta` through grok2api
- Pilot setup: QUETRA seed, pop=25, mean fitness, 10 generations

Treat A1 as a design reference and expected-range sanity check until reproduced through OpenRouter.

### Infrastructure

- Remote server: `ssh heyun`
- Primary checkout: `/root/code/EoH-repro/`
- Canonical experiment runner: `experiments/run_eoh_target_experiment.sh`
- Current hard-timeout fix: `eoh/src/eoh/llm/api_general.py`
- Formal API: OpenRouter OpenAI-compatible chat completions endpoint

### Source checks used for this plan

- Context7 library: `/websites/openrouter_ai`
- OpenRouter chat completions API: https://openrouter.ai/docs/api-reference/chat-completion
- OpenRouter provider routing: https://openrouter.ai/docs/features/provider-routing
- OpenRouter models API docs: https://openrouter.ai/docs/guides/overview/models
- OpenRouter models API endpoint: https://openrouter.ai/api/v1/models
