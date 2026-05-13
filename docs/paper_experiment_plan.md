# Paper Experiment Plan: OpenRouter-Reproduced EoABR vs SABR for ABR

## Paper Story

**Paradigm comparison**: interpretable evolved ABR heuristics (EoABR) vs black-box BC+RL (SABR) for adaptive bitrate streaming.

Naming convention: use **EoABR** for the paper-facing method. Reserve **EoH** for the original general method in related-work discussion or for literal implementation names and paths, such as `eoh/src/eoh` and `examples/user_abr/runEoH.py`.

The paper-facing experiment policy is now:

1. All EoABR results used in main paper tables must be regenerated through OpenRouter.
2. Previous mixed-provider results are pilot evidence only. They can guide experiment design, expected score ranges, artifact checks, and appendix discussion, but they should not be reported as final EoABR evidence.
3. Every OpenRouter run must preserve enough request, routing, cost, timeout, and artifact metadata to make the result auditable.

Key claims after the OpenRouter reproduction:

1. EoABR evolves interpretable ABR heuristics that are competitive with or stronger than SABR on in-domain benchmarks.
2. EoABR requires no expert demonstrations or offline RL policy-training dataset; it uses simulator-based fitness evaluation.
3. Evolved heuristics show non-trivial cross-regime transfer, but direct in-domain evolution is expected to remain best.
4. The main paper table can expose model dependence directly by reporting separate EoABR rows for multiple OpenRouter LLM backbones under the same protocol.

Recommended claim wording before formal runs finish:

> Pilot experiments suggest that EoABR can evolve interpretable ABR heuristics competitive with SABR while requiring no demonstrations or offline policy-training dataset. For the paper, all EoABR tables will be regenerated through a single OpenRouter-based experiment stack so that model, provider route, timeout, and cost effects are explicit.

Recommended claim wording after successful formal runs:

> Under a reproducible OpenRouter-based evaluation stack, EoABR evolves interpretable ABR heuristics that are competitive with or stronger than SABR on in-domain ABR benchmarks, require no expert demonstrations or offline policy-training dataset, and show non-trivial cross-regime transfer. Separate main-table rows show how performance varies across selected LLM families under the same gateway.

---

## Formal Reproduction Rules

### OpenRouter substrate

Use OpenRouter for every paper-facing EoABR evolution run:

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
| EoABR state | Seed heuristic, population size, generations, random seed, prompt template hash, parser/evaluator hash |
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

### Data provenance rule

No numeric result should enter a paper table unless its source is explicit:

- **SABR paper value**: cite the exact SABR paper table and keep test/OOD sets separated unless the document clearly labels a derived aggregate.
- **Local EoABR result**: cite the run ID plus the artifact path, manifest, command, model route, and evaluator version.
- **Local SABR rerun**: cite the rerun command, checkpoint/artifact, logs, and parser output. Do not merge this with paper-reported SABR values.
- **Pilot reference**: allowed only for planning and expected-range checks; never use as final evidence.

Current audit decision: the SABR paper does **not** report `Norway3G`. The paper reports ABRBench-3G test results in Table IV, ABRBench-4G+ test results in Table V, and OOD results for HSR/Ghent/Lab in Table VI. Therefore, the document keeps no SABR baseline for the local six-set 4G+ evaluator unless a local SABR rerun artifact is produced.

### In-domain pilots

| Regime | Provider path | Model | Seed/init mode | Pop | Budget note | Avg QoE | Pilot interpretation |
|--------|---------------|-------|----------------|-----|-------------|---------|----------------------|
| ABRBench-3G | grok2api | `grok-4.20-beta` | mixed all built-in seeds | 25 | tracker label `exp12` | 87.6 | Prior mixed-population reference: `20260401-132132-mixed-pop25-exp12` |
| ABRBench-3G | grok2api | `grok-4.20-beta` | quetra | 25 | 10 generations | 88.9 | Strong A1 heuristic; use as expected-range reference |
| ABRBench-4G+ | Vertex AI | `gemini-2.5-flash` | quetra | 25 | 10 generations | 1578.1 | Strong target-domain pilot; verify ceiling/artifact risk |

Pilot 3G mixed-pop25 and A1 both beat online baselines, with A1/QUETRA stronger than the mixed-pop25 pilot. For paper reproducibility and reviewer robustness, use the OpenRouter mixed-pop25 design as the formal main-table protocol, while keeping A1/QUETRA as an internal expected-range reference. Pilot 4G+ reached a high local six-set average, but it currently has no sourced SABR comparator for that local six-set evaluator. The very high Solis-Wi-Fi and repeated `1842.5` ceiling-like values must also be checked before they influence the paper story.

### Transfer pilots

| Direction | Pilot EoABR Avg | SABR reference for paper writing | Status | Interpretation |
|-----------|------------------|----------------------------------|--------|----------------|
| 3G -> 4G+ | 1027.4 on local six-set 4G+ evaluator | None for the local six-set evaluator | Requires paper-protocol evaluation or a sourced local SABR rerun before SABR comparison | Useful negative-control candidate, but do not claim win/loss vs SABR yet |
| 4G+ -> 3G | 85.5 on local six-set 3G evaluator | Computed `83.3` from SABR paper Table IV plus HSR from Table VI | Derived comparison; label as computed, not paper-reported | Non-trivial rule-level transfer, but below direct 3G evolution |

Current local pilot data sources:

| Value | Source artifact | Status |
|-------|-----------------|--------|
| 3G mixed-pop25 `87.5768` | `experiments/campaign_data/3g-hardset-round2/mixed_pop25_results_summary.csv`, tracker run `20260401-132132-mixed-pop25-exp12` | Local pilot only |
| 3G A1/QUETRA-pop25 `88.8697` | `experiments/campaign_data/3g-hardset-round2/A1_quetra_pop25_mean_results_summary.csv`, campaign `experiments/campaigns/3g-hardset-round2.md` | Local pilot only |
| 4G+ in-domain `1578.1410` | `experiments/campaign_data/4gplus-hardset/results_summary.csv`, tracker run `20260427-081532-4gplus-a1-config-vertexflash-r1` | Local pilot only; no sourced local six-set SABR comparator |
| 3G -> 4G+ transfer `1027.4318` | `experiments/campaign_data/a1-4gplus-transfer/results_summary.csv` | Local pilot only; no sourced local six-set SABR comparator |
| 4G+ -> 3G transfer `85.5195` | `experiments/campaign_data/4gplus-to-3g-transfer/r1_vertexpro_results_summary.csv`, tracker run `20260507-4gplus-to-3g-vertexpro-r1` | Local pilot only |

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

**Goal**: Reproduce the main EoABR vs SABR comparison using OpenRouter-generated EoABR heuristics only, with separate rows for selected LLM backbones.

### Formal common setup

- Datasets: ABRBench-3G and ABRBench-4G+
- Initial population: mixed all-seed population with five seed families, `quetra`, `rate_based`, `bb`, `bola`, and `robust_mpc`
- Population/generations: pop=25, 10 generations
- Fitness: mean QoE over the target training/evaluation set, matching the current EoABR setup
- Minimum formal unit: one completed OpenRouter mixed-pop25 run per selected model and regime
- Preferred formal unit: 3 independent OpenRouter mixed-pop25 repeats per selected model and regime
- Report: one row per selected model; do not average results across models
- Per-row statistics: mean +/- std across independent mixed-pop25 repeats for that model; include initial-population composition and best-run heuristic in appendix
- SABR comparison: use SABR paper values and average-rank methodology; if SABR code/artifacts are available, rerun them separately and label the source. `Norway3G` has no SABR paper value and can only appear in a clearly labeled local extended evaluation.

### Mixed-seed main-table protocol

The main EoABR rows should not be QUETRA-only results. QUETRA is the strongest pilot seed and is useful as an internal reference, but using it alone creates a plausible reviewer objection that the result is seed-selected. The paper-facing protocol should follow the previous mixed-population design for every selected model: one pop=25 run initialized from all five seed families, with five initial individuals per family.

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

Primary Table 1 value: for each selected model, average over independent OpenRouter repeats of this mixed-pop25 initialization. Appendix value: initial-population composition plus, if useful, lineage/parent-family analysis of final best heuristics. Do not average five separate seed-only campaigns as the main result, and do not average different LLM backbones into one EoABR score.

### ABRBench-3G formal table

| Method | Type | FCC-16 | FCC-18 | Oboe | Puffer-21 | Puffer-22 | Computed test avg | Paper test Ave Rank | HSR (OOD) | Source |
|--------|------|--------|--------|------|-----------|-----------|-------------------|---------------------|-----------|--------|
| BB | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Formal rerun or SABR Table IV/VI |
| BOLA | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Formal rerun or SABR Table IV/VI |
| QUETRA | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Formal rerun or SABR Table IV/VI |
| RobustMPC | Rule | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Formal rerun or SABR Table IV/VI |
| SABR | BC+RL | 36.68 | 145.18 | 99.68 | 36.05 | 40.05 | 71.53 | 1.8 | 142.20 | SABR paper Tables IV and VI |
| EoABR (Grok 4.3, mixed pop25) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OpenRouter manifest/run artifact |
| EoABR (DeepSeek V4 Pro, mixed pop25) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OpenRouter manifest/run artifact |
| EoABR (Gemini 3 Flash Preview, mixed pop25; optional) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OpenRouter manifest/run artifact |

The HSR value is an OOD result from SABR Table VI, not part of the Table IV test-set average rank. Keep this separation in figures and text.

**Status**: Formal OpenRouter mixed-pop25 rerun pending. Pilot expected range: mixed-pop25 reached `87.5768` on 3G, while A1/QUETRA reached `88.9`; do not report either as final.

### ABRBench-4G+ formal table

| Method | Type | Lumos4G | Lumos5G | Solis-Wi-Fi | Computed test avg | Paper test Ave Rank | Ghent (OOD) | Lab (OOD) | Source |
|--------|------|---------|---------|------------|-------------------|---------------------|-------------|-----------|--------|
| SABR | BC+RL | 1309.65 | 1832.14 | 576.33 | 1239.37 | 1.7 | 1023.56 | 1561.18 | SABR paper Tables V and VI |
| EoABR (Grok 4.3, mixed pop25) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OpenRouter manifest/run artifact |
| EoABR (DeepSeek V4 Pro, mixed pop25) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OpenRouter manifest/run artifact |
| EoABR (Gemini 3 Flash Preview, mixed pop25; optional) | Evolved | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OpenRouter manifest/run artifact |

`Norway3G` is a local evaluator dataset, not a SABR paper ABRBench-4G+ test or OOD set. If it remains useful, report it in a separate local extended-evaluation appendix with locally rerun baselines and explicit artifact paths.

**Status**: Formal OpenRouter mixed-pop25 rerun pending. Before running the full campaign, verify whether the pilot `1842.5` ceiling-like values are valid simulator outcomes or an evaluation artifact.

### Formal main model set

Use multiple selected OpenRouter models as separate Table 1 rows. Each model row is an independent EoABR condition with its own manifest, run artifacts, costs, reliability statistics, and evolved heuristic. Do not pool or average across model rows.

| Role | Model ID | Table label | Inclusion rule |
|------|----------|-------------|----------------|
| Required main row | `x-ai/grok-4.3` | EoABR (Grok 4.3) | Include if smoke test shows stable routing, acceptable invalid-offspring rate, and manageable cost |
| Required main row | `deepseek/deepseek-v4-pro` | EoABR (DeepSeek V4 Pro) | Include as the second main row because it is much cheaper and gives a different model family |
| Optional main row | `google/gemini-3-flash-preview` | EoABR (Gemini 3 Flash Preview) | Include only if preview-model stability and route metadata are acceptable |
| Sensitivity-only row | `openai/gpt-5.4-mini` | Table 3 candidate | Use for backbone sensitivity unless budget supports a third or fourth Table 1 model |

For downstream ablations, choose one **reference ablation model** from the Table 1 main rows after smoke tests. The default reference ablation model is `x-ai/grok-4.3`; if Grok is unstable or too expensive, use `deepseek/deepseek-v4-pro`. Table 4 ablations should not be automatically replicated for every Table 1 model unless the paper explicitly studies model-by-ablation interactions.

---

## Formal Experiment Table 2: Zero-Shot Transfer

**Goal**: Evaluate whether OpenRouter-evolved EoABR heuristics transfer across network regimes without target-domain evolution.

### Formal design

| Transfer direction | Source heuristic | Target evaluation | Required runs | Report |
|--------------------|------------------|-------------------|---------------|--------|
| 3G -> 4G+ | Formal 3G OpenRouter mixed-pop25 heuristic for each Table 1 model row | ABRBench-4G+ | Same model-specific formal repeat set | Per-dataset QoE, derived avg, wins/losses against the sourced SABR comparator |
| 4G+ -> 3G | Formal 4G+ OpenRouter mixed-pop25 heuristic for each Table 1 model row | ABRBench-3G | Same model-specific formal repeat set | Per-dataset QoE, derived avg, wins/losses against the sourced SABR comparator |

Use the same OpenRouter model and mixed-pop25 protocol as the source Table 1 row. Transfer should be reported as secondary evidence. It should not be framed as replacing in-domain evolution unless it beats or matches the direct in-domain OpenRouter result for the same model family.

### Pilot reference ranges

| Direction | Pilot result | Use in formal design |
|-----------|--------------|----------------------|
| 3G -> 4G+ | Avg `1027.4` on local six-set 4G+ evaluator; no sourced SABR comparator for that six-set evaluator | Expect transfer to be below direct 4G+ evolution; do not report SABR win/loss until a sourced SABR reference exists |
| 4G+ -> 3G | Avg `85.5`; comparison against computed SABR avg `83.3` must be labeled derived from Tables IV/VI | Expect useful but not best-in-paper transfer |

---

## Formal Experiment Table 3: OpenRouter LLM Backbone Sensitivity

**Goal**: Measure broader LLM-family sensitivity while keeping endpoint, prompt, seed heuristic, population, generations, dataset, parser, evaluator, timeout policy, and logging fixed.

### Design

- Dataset: ABRBench-3G first; add 4G+ only if results are central to the paper.
- Relationship to Table 1: Table 1 already reports selected main models as separate EoABR rows. Table 3 is for cheaper screening, additional model families, reliability/cost comparison, and optional confirmation beyond the main Table 1 rows.
- Seed policy: QUETRA-only is acceptable for the cheap pop=5 screening sweep, because the goal is controlled model comparison rather than a main performance claim.
- Budget tier: pop=5, 10 generations for sweep.
- Confirmation tier: pop=25, 10 generations for the top 2-3 families, using the mixed-pop25 initialization if the result will support a paper claim or be promoted into Table 1.
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

The paper claim should be bounded: EoABR may be robust across several LLM families, but the table should expose performance and reliability differences rather than hiding them. Provider reliability is a systems result; timeout and invalid-offspring rates help readers separate model reasoning quality from API instability.

---

## Formal Experiment Table 4: Ablations and Diagnostics

All controlled ablations must use the selected OpenRouter reference ablation model and route policy unless the ablation explicitly studies LLM/model behavior. Diagnostic analyses should be computed from the formal OpenRouter artifacts and should not be described as independent ablations.

### 4a: Initialization dominance analysis (Table 1 diagnostic)

**Goal**: Explain which seed-family components dominate in the formal mixed-pop25 Table 1 runs.

This is not a controlled initialization ablation. It is a post-hoc diagnostic for Table 1: it documents the seed composition inside the single mixed-pop25 initialization and analyzes which seed families survive as parents, ancestors, or recognizable motifs in the final best heuristics.

Required outputs:

- Initial composition: five individuals from each built-in seed family.
- Per-generation survival counts by seed-family tag if the artifact format preserves ancestry.
- Parent/ancestor distribution for accepted offspring and final best heuristics if lineage is available.
- If explicit lineage is missing, use manual code/motif classification only as an approximate appendix analysis and label it as approximate.
- Main question: whether the final heuristic is mostly QUETRA-like, MPC-like, BB/BOLA-like, rate-based, or a hybrid.

| Seed family | Individuals in Table 1 mixed pop25 | Single-seed pop5 pilot on 3G | Diagnostic field |
|-------------|------------------------------------|-------------------------------|------------------|
| quetra | 5 | 87.0 | Survival/lineage/motif share in final artifacts |
| rate_based | 5 | 86.2 | Survival/lineage/motif share in final artifacts |
| bb | 5 | 85.9 | Survival/lineage/motif share in final artifacts |
| bola | 5 | 85.0 | Survival/lineage/motif share in final artifacts |
| robust_mpc | 5 | 84.8 | Survival/lineage/motif share in final artifacts |

Pilot data from `experiments/campaign_data/3g-seed-impact/` remains useful for context, but Table 1 should use the mixed-pop25 initialization, not five separate seed-only results averaged together.

Implementation requirement: before formal runs, ensure population artifacts preserve enough identifiers to recover the initial seed family for each individual and, where possible, parent links for generated offspring.

### 4b: Single-family initialization ablation

**Goal**: Quantify how sensitive EoABR is to the initial seed family when the evolution budget is held fixed.

This is the controlled initialization ablation. Each single-family arm starts from a pop=25 population derived from one seed family only, while the main Table 1 arm starts from the mixed pop=25 population with five individuals per seed family. Compare every single-family arm against the mixed-pop25 reference, but do not replace the Table 1 main result with a seed-selected arm.

Common setup:

- Dataset: ABRBench-3G first; extend to 4G+ only for the mixed reference and the strongest or most informative single-family arms if budget is limited.
- Population/generations: pop=25, 10 generations.
- Fitness/evaluator: same mean-QoE evaluator as Table 1.
- Model/routing: same OpenRouter reference ablation model and route policy.
- Repetition policy: one run per arm is acceptable for screening; use 3 independent repeats per arm if the paper makes a causal claim about initialization.
- Runner behavior: with a singleton selected seed and `EC_POP_SIZE=25`, `examples/user_abr/runEoH.py` expands that seed into 25 initial slots. Use unique manifest/output IDs per seed family and avoid sharing cached seed artifacts across arms.

| Setting | Initial population | Dataset priority | Formal QoE avg | Pilot reference | Purpose |
|---------|--------------------|------------------|----------------|-----------------|---------|
| Mixed-pop25 main reference | 5 each from `quetra`, `rate_based`, `bb`, `bola`, `robust_mpc` | 3G and 4G+ | TBD | mixed-pop25 pilot `87.5768` on 3G | Reviewer-robust main setting |
| BB-pop25 | 25 `bb` initial slots | 3G first | TBD | pop5 pilot `85.9` | Test buffer-based basin |
| BOLA-pop25 | 25 `bola` initial slots | 3G first | TBD | pop5 pilot `85.0` | Test BOLA-style basin |
| QUETRA-pop25 | 25 `quetra` initial slots | 3G first | TBD | A1/QUETRA pilot `88.9` | Test strongest known single-family basin |
| RobustMPC-pop25 | 25 `robust_mpc` initial slots | 3G first | TBD | pop5 pilot `84.8` | Test MPC-style basin |
| RateBased-pop25 | 25 `rate_based` initial slots | 3G first | TBD | pop5 pilot `86.2` | Test simple throughput basin |

Expected interpretation:

- If mixed-pop25 is competitive with the best single-family arm, the main protocol is robust and not seed-selected.
- If QUETRA-pop25 clearly beats mixed-pop25, report it as an initialization sensitivity result rather than using it as the main paper row.
- If a non-QUETRA single-family arm wins, the dominance analysis in 4a becomes important for explaining which heuristic family provides the useful building blocks.

### 4c: Population-size effect

**Goal**: Quantify whether larger populations improve final heuristic quality when the seed-family setup is held fixed.

This should be a matched population-size comparison, not another seed-family ablation. It has two axes:

- Single-family size effect: one seed family expanded to 5 initial slots vs the same seed family expanded to 25 initial slots.
- Mixed-family size effect: five seed families with one initial slot each vs the same five seed families with five initial slots each.

Runner interpretation:

- `ABR_SEED_NAME=quetra`, `EC_POP_SIZE=5` means five QUETRA-derived initial slots.
- `ABR_SEED_NAME=quetra`, `EC_POP_SIZE=25` means twenty-five QUETRA-derived initial slots.
- Selecting all five built-in seeds with `EC_POP_SIZE=5` means one slot each from `quetra`, `rate_based`, `bb`, `bola`, and `robust_mpc`.
- Selecting all five built-in seeds with `EC_POP_SIZE=25` means five slots per seed family.

Primary 4c table:

| Comparison | Pop=5 arm | Pop=25 arm | Reuse rule | Pilot reference |
|------------|-----------|------------|------------|-----------------|
| Single-family size effect, primary | `QUETRA-pop5`: 5 QUETRA-derived slots | `QUETRA-pop25`: 25 QUETRA-derived slots | Reuse `QUETRA-pop25` from 4b; reuse reference-model `QUETRA-pop5` from Table 3 if protocol matches, otherwise run it once | Old pilots: `87.0` vs `88.9` on 3G |
| Mixed-family size effect, primary | `Mixed-pop5`: 1 slot each from the five built-in seed families | `Mixed-pop25`: 5 slots each from the five built-in seed families | Reuse the reference-model `Mixed-pop25` from Table 1; run `Mixed-pop5` only if no matching formal OpenRouter arm exists | Old mixed-pop25 pilot: `87.5768` on 3G |

Optional appendix expansion:

| Seed family | Pop=5 arm | Pop=25 arm | Reuse rule |
|-------------|-----------|------------|------------|
| `bb` | 5 `bb`-derived slots | 25 `bb`-derived slots | Reuse `BB-pop25` from 4b; run `BB-pop5` only if needed |
| `bola` | 5 `bola`-derived slots | 25 `bola`-derived slots | Reuse `BOLA-pop25` from 4b; run `BOLA-pop5` only if needed |
| `quetra` | 5 `quetra`-derived slots | 25 `quetra`-derived slots | Reuse `QUETRA-pop25` from 4b; reuse matching Table 3 reference-model arm if possible |
| `robust_mpc` | 5 `robust_mpc`-derived slots | 25 `robust_mpc`-derived slots | Reuse `RobustMPC-pop25` from 4b; run `RobustMPC-pop5` only if needed |
| `rate_based` | 5 `rate_based`-derived slots | 25 `rate_based`-derived slots | Reuse `RateBased-pop25` from 4b; run `RateBased-pop5` only if needed |

Deduplication rule:

- Do not rerun a 4c arm if an earlier formal OpenRouter run already has the same dataset, model, route policy, seed selection, `EC_POP_SIZE`, generations, evaluator, parser, timeout policy, and manifest version.
- Table 1 supplies the formal `Mixed-pop25` arm for the selected reference ablation model.
- Table 4b supplies formal single-family `pop25` arms.
- Table 3 may supply `QUETRA-pop5` for the selected reference ablation model if the exact protocol matches.
- Previous mixed-provider results can be shown as pilot references, but they are not paper-valid 4c data because the provider route and OpenRouter metadata policy differ.

Expected interpretation:

- If `QUETRA-pop25` beats `QUETRA-pop5`, the gain is a single-family population/search-budget effect.
- If `Mixed-pop25` beats `Mixed-pop5`, the gain is a mixed-family population/search-budget effect.
- If mixed-family gains differ from single-family gains, discuss population size and seed-family diversity separately.

### 4d: Convergence curve

**Goal**: Show how quickly OpenRouter-EoABR improves over generations.

Extract per-generation best and population mean QoE from `population_generation_*.json` files for the formal campaigns. Plot mean +/- std across independent runs where possible. This should be generated only from OpenRouter runs used in the paper tables.

### 4e: Best heuristic code showcase

**Goal**: Support interpretability.

For the final selected OpenRouter heuristic:

- Include compact pseudocode or a trimmed code block in the paper.
- Explain the main control logic in ABR terms.
- Link each explanation to the actual saved heuristic file.
- Avoid using the legacy A1 code as the main showcase unless it is reproduced or closely matched by a formal OpenRouter run.

---

## Cross-table Reuse Map

Use this map before scheduling any new OpenRouter evolution run. A run can be reused only when the dataset, OpenRouter model ID, provider route policy, seed selection, `EC_POP_SIZE`, generations, evaluator, parser, timeout policy, and manifest version all match the consuming table's protocol. Otherwise, keep the older run as pilot context and schedule a new formal run.

| Source artifact/run | Can supply | Reuse condition | New run still needed when |
|---------------------|------------|-----------------|---------------------------|
| Table 1 3G mixed-pop25 formal runs | Table 2 `3G -> 4G+` source heuristics; 4a dominance analysis; 4c `Mixed-pop25` for the reference ablation model; 4d convergence curve; 4e code showcase if selected | Use the exact saved 3G best heuristic and full population artifacts for the same model row | Transfer target evaluation has not been run, lineage metadata is missing for 4a, or the run is not OpenRouter-valid |
| Table 1 4G+ mixed-pop25 formal runs | Table 2 `4G+ -> 3G` source heuristics; 4a dominance analysis; 4d convergence curve; 4e code showcase if selected | Use the exact saved 4G+ best heuristic and full population artifacts for the same model row | Transfer target evaluation has not been run, 4G+ ceiling artifact check fails, or the run is not OpenRouter-valid |
| Table 4b single-family pop25 runs | 4c single-family `pop25` arms; 4d convergence curve; appendix seed-family comparison | Same seed family, 3G dataset, reference ablation model, route policy, pop=25, 10 generations, and evaluator | 4b is run on a different model, dataset, evaluator, or manifest version |
| Table 3 reference-model pop5 run | 4c `QUETRA-pop5` arm | The selected reference ablation model is included in Table 3 and uses QUETRA, pop=5, 10 generations, 3G, and the same evaluator | Table 3 uses a non-reference model, different seed policy, or different route policy |
| Table 4c `Mixed-pop5` run | Appendix comparison against `Mixed-pop25`; 4d convergence curve | Same mixed five-seed setup, pop=5, 10 generations, reference ablation model, and evaluator | No exact mixed-pop5 formal OpenRouter run exists |
| Any formal OpenRouter evolution run | Reliability appendix and cost/token analysis | Raw OpenRouter metadata, retries, invalid offspring, timeout status, usage, and cost are logged | Metadata is missing or the run used fallback routing outside the manifest |
| SABR paper values or reruns | Table 1/Table 2 comparison rows and average-rank computation | Source is clearly labeled as paper-reported or local rerun; test/OOD sets are not silently merged | SABR rerun protocol differs from the reported paper protocol, or `Norway3G` is requested without a local SABR rerun artifact |

Practical scheduling rule:

- Run Table 1 first because it supplies the main EoABR rows, transfer source heuristics, mixed-pop25 references, convergence data, and interpretability candidates.
- Run Table 4b before expanding 4c because it supplies the single-family pop25 arms.
- Run Table 3 before scheduling `QUETRA-pop5` for 4c; if the reference-model Table 3 arm matches exactly, reuse it.
- Treat 4a, 4d, 4e, average-rank computation, reliability analysis, and cost analysis as artifact-processing tasks unless required metadata is missing.

---

## Experiment Priority Queue

| Priority | Experiment | Status | Estimated Time | Purpose |
|----------|------------|--------|----------------|---------|
| P0 | Implement OpenRouter-aware `InterfaceAPI` request/metadata support | Planned | 1-2h | Make formal runs auditable |
| P1 | Create frozen run manifest template and model snapshot script | Planned | 1h | Prevent undocumented provider/model drift |
| P2 | OpenRouter smoke tests for main model candidates | Planned | 1-2h | Select Table 1 model rows and the reference ablation model |
| P3 | Verify Solis-Wi-Fi / 4G+ ceiling-like pilot scores | Planned | 1-2h | Remove evaluation-artifact risk |
| P4 | Formal 3G main campaign per selected Table 1 model, mixed pop25, 5 individuals per seed family | Planned | 1-3 repeats per model | Main Table 1 without QUETRA-only seed selection or model averaging |
| P5 | Formal 4G+ main campaign per selected Table 1 model, mixed pop25, 5 individuals per seed family | Planned | 1-3 repeats per model | Main Table 1 without QUETRA-only seed selection or model averaging |
| P6 | Formal model-specific transfer evaluation in both directions | Planned | 2-4h after P4/P5 per model | Table 2 |
| P7 | Average-rank computation matching SABR methodology | Planned | 2h | Paper metric consistency |
| P8 | OpenRouter single-family initialization ablation, pop25 on 3G | Planned | 20-50h | Table 4 controlled seed-initialization ablation |
| P9 | Initialization dominance analysis from Table 1 artifacts | Planned | 1-2h | Table 4 diagnostic for mixed-pop25 composition |
| P10 | OpenRouter population-size comparison, reusing Table 1/4b/Table 3 arms where protocols match | Planned | 5-20h plus any missing arms | Table 4 population effect without duplicate runs |
| P11 | OpenRouter pop=5 backbone sweep | Planned | 10-20h | Table 3 |
| P12 | Pop=25 confirmation for 2-3 additional Table 3 models | Planned | 15-30h per config | Backbone robustness claim beyond Table 1 rows |
| P13 | Convergence curve and best-heuristic extraction | Planned | 1-2h | Figures and interpretability evidence |

---

## Statistical Validity

SABR reports averaged results, so final EoABR claims should not rely on a single lucky run, a single favorable seed heuristic, or a single favorable model row.

- Minimum for Table 1: one OpenRouter mixed-pop25 run per selected model and regime, initialized with five individuals from each of the five built-in seed families.
- Preferred for Table 1: 3 independent OpenRouter repeats of the same mixed-pop25 protocol per selected model and regime.
- Report Table 1 model rows separately; do not average Grok, DeepSeek, Gemini, or other model rows into one EoABR value.
- Table 4a is diagnostic only; do not use it as causal evidence about initialization.
- Minimum for Table 4b: one OpenRouter pop25 run per single-family arm on 3G, compared against the mixed-pop25 Table 1 reference.
- Preferred for Table 4b: 3 independent repeats per arm using the same random-seed schedule across arms; report mean +/- std and per-dataset wins/losses.
- Minimum for Table 4c: matched formal OpenRouter pairs for `QUETRA-pop5` vs `QUETRA-pop25` and `Mixed-pop5` vs `Mixed-pop25` on 3G.
- Table 4c reuse rule: reuse Table 1, 4b, or Table 3 runs only when the protocol and manifest fields match exactly; otherwise treat the older run as pilot context or rerun the missing arm.
- Report: mean +/- std across independent repeats, average rank, per-dataset wins/losses, and best-run heuristic separately.
- Always include the initial-population composition in the appendix; include lineage or parent-family analysis if the artifacts support it.
- Randomness: record EoABR random seed, LLM model ID, provider route, and request-level seed if used.
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

- Table IV, ABRBench-3G test: FCC-16, FCC-18, Oboe, Puffer-21, Puffer-22; SABR row `36.68 / 145.18 / 99.68 / 36.05 / 40.05`, average rank `1.8`.
- Table V, ABRBench-4G+ test: Lumos 4G, Lumos 5G, Solis Wi-Fi; SABR row `1309.65 / 1832.14 / 576.33`, average rank `1.7`.
- Table VI, OOD: HSR, Ghent, Lab; SABR row `142.20 / 1023.56 / 1561.18`, average rank `2.0`.
- The paper does not report `Norway3G`. Any `Norway3G` comparison must come from a local rerun and be labeled as local extended evaluation.
- Each method is run 10 times in the SABR paper; learning-based methods report averages over 10 trained models.

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

- SABR arXiv HTML fetched with `smart-search fetch`: https://arxiv.org/html/2509.10486v1
- Context7 library: `/websites/openrouter_ai`
- OpenRouter chat completions API: https://openrouter.ai/docs/api-reference/chat-completion
- OpenRouter provider routing: https://openrouter.ai/docs/features/provider-routing
- OpenRouter models API docs: https://openrouter.ai/docs/guides/overview/models
- OpenRouter models API endpoint: https://openrouter.ai/api/v1/models
- Local audit: exact search for the former six-set 4G+ SABR row found it only in planning/campaign narrative, not in raw local result CSV/log artifacts.
