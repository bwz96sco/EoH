# Paper Experiment Plan: EoH vs SABR for Adaptive Bitrate Streaming

## Paper Story
**Paradigm comparison**: Interpretable evolved heuristics (EoH) vs black-box RL (SABR) for ABR streaming.

Key claims:
1. EoH produces **interpretable** heuristics that match or exceed SABR on in-domain benchmarks
2. EoH requires **zero training data** — evolution uses only the simulator
3. Evolved heuristics show **reasonable zero-shot transfer** across network regimes
4. Performance is **robust across LLM backbones** — the evolutionary framework, not the specific model, drives quality

### Review Notes

The paper story is viable, but the experiment section needs to avoid three confounds before the claims are paper-ready:

1. **Single-run vs averaged baselines**: SABR reports averaged results. EoH claims should be reported as mean±std across independent runs for the final tables, with single-run best heuristics treated as discovery evidence.
2. **Model vs provider confound**: Current LLM evidence mixes model family, provider route, timeout behavior, and API stability (`grok2api`, Vertex AI, SiliconFlow). The LLM section should become a provider-normalized OpenRouter study before making a backbone-robustness claim.
3. **OOD claim strength**: Current 3G→4G+ transfer loses to SABR on 6/6 4G+ datasets. Keep the transfer table, but frame it as "non-trivial rule-level generalization" unless the reverse transfer or reruns are stronger.

Recommended claim wording after revision:

> EoH can evolve interpretable ABR heuristics that are competitive with SABR on in-domain benchmarks, require no offline training dataset, and remain effective across several frontier and cost-efficient LLM backbones when the API/provider path is controlled.

---

## Table 1: Main Results — EoH vs SABR vs Classical Baselines

**Goal**: Demonstrate EoH competitiveness with SABR across both network regimes.

### ABRBench-3G (6 datasets: FCC-16, FCC-18, Oboe, Puffer-21, Puffer-22, HSR)

| Method | Type | FCC-16 | FCC-18 | Oboe | Puffer-21 | Puffer-22 | HSR | Avg | Ave Rank |
|--------|------|--------|--------|------|-----------|-----------|-----|-----|----------|
| BB | Rule | — | — | — | — | — | — | — | — |
| BOLA | Rule | — | — | — | — | — | — | — | — |
| QUETRA | Rule | — | — | — | — | — | — | — | — |
| RobustMPC | Rule | — | — | — | — | — | — | — | — |
| SABR | BC+RL | 36.68 | 145.18 | 99.68 | 36.05 | 40.05 | 142.20 | — | 1.8 |
| **EoH (A1)** | **Evolved** | **38.79** | **146.86** | **100.18** | **55.45** | **45.25** | **146.69** | **88.9** | **—** |

**Status**: ✅ Complete. EoH wins 6/6 datasets vs SABR.

### ABRBench-4G+ (6 datasets: Norway3G, Lumos4G, Lumos5G, SolisWi-Fi, Ghent, Lab)

| Method | Type | Norway3G | Lumos4G | Lumos5G | SolisWi-Fi | Ghent | Lab | Avg | Ave Rank |
|--------|------|----------|---------|---------|------------|-------|-----|-----|----------|
| SABR | BC+RL | 57.7 | 1711.9 | 1836.6 | 669.8 | 1188.9 | 1666.7 | 1188.6 | 1.7 |
| **EoH** | **Evolved** | ? | ? | ? | ? | ? | ? | ? | ? |

**Status**: 🏃 Running. Run ID: `20260427-081532-4gplus-a1-config-vertexflash-r1`
- Config: quetra seed, pop=25, 10 gen, gemini-2.5-flash via Vertex AI
- ETA: 5-10 hours

### Key configuration for main results

| Setting | 3G (A1) | 4G+ |
|---------|---------|-----|
| LLM | grok-4.20-beta | gemini-2.5-flash |
| Seed | quetra | quetra |
| Population | 25 | 25 |
| Generations | 10 | 10 |
| Fitness | mean | mean |

---

## Table 2: Zero-Shot Transfer

**Goal**: Evaluate cross-domain generalization without retraining.

| Direction | SABR Avg | EoH Avg | Delta | Wins |
|-----------|----------|---------|-------|------|
| 3G→4G+ (A1 heuristic evaluated on 4G+) | 1188.6 | 1027.4 | -13.6% | 0/6 |
| 4G+→3G (4G+ heuristic evaluated on 3G) | — | — | — | — |

**Status**: 3G→4G+ ✅ Complete. 4G+→3G ⬜ Optional (depends on 4G+ results).

### Detailed 3G→4G+ Transfer Results

| Dataset | SABR | EoH (A1) | BeamSearch |
|---------|------|----------|------------|
| Norway3G | 57.7 | -285.5 | -245.2 |
| Lumos4G | 1711.9 | 1363.5 | 1456.2 |
| Lumos5G | 1836.6 | 1784.0 | 1839.7 |
| SolisWi-Fi | 669.8 | 630.4 | 656.7 |
| Ghent | 1188.9 | 1107.5 | 1245.2 |
| Lab | 1666.7 | 1564.7 | 1636.2 |

**Narrative**: While zero-shot transfer loses to SABR (which was trained on the target domain), EoH still beats 4/6 classical baselines, demonstrating reasonable generalization from a heuristic evolved on a completely different network regime.

---

## Table 3: LLM Backbone Sensitivity via OpenRouter

**Goal**: Test whether EoH is robust to LLM backbone choice while holding the API path, prompt, seed heuristic, population size, generations, fitness, dataset, and timeout policy fixed.

### Why the current provider section should change

The existing model-sensitivity evidence is useful as a pilot, but not clean enough for a paper table:

| Existing model | Provider path | 3G QoE (avg) | Paper-readiness concern |
|----------------|---------------|-------------|--------------------------|
| grok-4.20-beta | grok2api | 84.4 | legacy proxy route; provider behavior differs from Vertex/SiliconFlow |
| gemini-2.5-flash | Vertex AI | 83.6 | strong continuity result, but direct Vertex transport differs from other models |
| gemini-2.5-pro | Vertex AI | 81.7 | same provider family as flash; less cross-family evidence |
| gemini-2.0-flash-lite | Vertex AI | 75.7 | weaker model and same provider family are both changing |
| GLM-5.1 | SiliconFlow | 75.7 | provider and model family both change |

These results can stay in the appendix as **legacy provider-mixed evidence**. The main paper should use a single OpenAI-compatible endpoint through OpenRouter for the cross-model experiment.

### OpenRouter-controlled experiment design

**Common setup**:
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Request shape: OpenAI-compatible chat completion, `stream=false`
- Fixed EoH config: `ABRBench-3G`, QUETRA seed, `pop=5`, 10 generations, mean fitness, same prompt templates, same parser/evaluator, same timeout settings
- Record for every run: model ID, provider route if available, API errors, timeout count, invalid-offspring count, wall time, token usage/cost if available, best QoE per generation, final best heuristic

**Reproducibility rule**:
- Do not use automatic model fallback for the main comparison unless the selected fallback chain is explicitly part of the experiment.
- Prefer a locked model ID and fixed provider-routing settings. If OpenRouter fallback/load balancing is enabled, report that as a provider-availability setting rather than as a pure model comparison.
- Add request metadata support before final runs if needed, because the current `InterfaceAPI` only sends `{model, stream, messages}` and does not expose OpenRouter `provider` preferences or OpenRouter-specific headers.

### Part A: OpenRouter bridge runs

**Purpose**: Separate "new provider path" effects from "new model" effects.

| Model ID | Role | Pop | Status |
|----------|------|-----|--------|
| `x-ai/grok-4.20` or `x-ai/grok-4.20-multi-agent` | bridge against A1/grok result | 5 | planned |
| `google/gemini-2.5-flash` | bridge against Vertex result | 5 | planned |

If bridge runs land near the legacy results, the OpenRouter path is credible for the full sensitivity table. If they diverge sharply, treat provider route as a first-order factor and report both "direct provider" and "OpenRouter route" separately.

### Part B: Pop=5 backbone sweep

**Purpose**: Compare families cheaply under one provider gateway.

Candidate roster checked against the OpenRouter model list on 2026-04-27:

| Family | Candidate model ID | Why include |
|--------|--------------------|-------------|
| xAI | `x-ai/grok-4.20` | continuity with the A1 result |
| Google | `google/gemini-2.5-flash` | continuity with current 4G+ and Vertex runs |
| OpenAI | `openai/gpt-5.4-mini` | GPT-family representative with controlled cost |
| Anthropic | `anthropic/claude-sonnet-4.6` | Claude-family frontier representative |
| DeepSeek | `deepseek/deepseek-v3.2` or `deepseek/deepseek-v4-flash` | strong low-cost Chinese-model representative |
| Z.ai | `z-ai/glm-5.1` | GLM-family representative, comparable to the existing GLM-5.1 pilot |
| MiniMax | `minimax/minimax-m2.7` | independent Chinese-model family |

For budget control, first run one seed per model. Promote only the strongest 2-3 non-baseline families to multi-run confirmation.

### Part C: Pop=25 confirmation

**Purpose**: Verify that the main result is not an artifact of one LLM backbone.

| Model group | Candidate | Pop | Runs | Purpose |
|-------------|-----------|-----|------|---------|
| A1 anchor | best available Grok route or already completed A1 | 25 | existing + rerun if needed | main anchor |
| OpenRouter strong model | best of GPT/Claude/Gemini sweep | 25 | 3+ | cross-family confirmation |
| OpenRouter cost-efficient model | best of DeepSeek/GLM/MiniMax sweep | 25 | 3+ | cost/performance confirmation |

### Expected narrative

- The main LLM claim should be **bounded**, not absolute: "EoH is not tied to a single proprietary model family when the provider path is controlled."
- Population size can still be discussed, but only after comparing like-for-like model/provider settings.
- Provider reliability is itself a useful systems result: report timeout and invalid-offspring rates so readers can distinguish model reasoning quality from API instability.

---

## Table 4: Ablation Studies

### 4a: Seed Heuristic Impact (3G, pop=5)

| Seed | 3G QoE (avg) |
|------|-------------|
| quetra | 87.0 |
| robust_mpc | — |
| bola | — |
| bb | — |
| rate_based | — |

**Status**: ✅ Complete. Data in `experiments/campaign_data/3g-seed-impact/`.

### 4b: Population Size Effect

| Pop Size | Model | 3G QoE (avg) |
|----------|-------|-------------|
| 5 | grok | 84.4 |
| 25 | grok | 88.9 |
| 5 | gemini-flash | 83.6 |
| 25 | gemini-flash | ? |

**Status**: Partial. Pop=25 gemini-flash is queued.

### 4c: Convergence Curve

Extract per-generation best QoE from `population_generation_*.json` files.
Shows how quickly EoH converges and whether more generations would help.

**Status**: ⬜ Data available in population files, needs extraction script.

---

## Experiment Priority Queue

| Priority | Experiment | Status | Estimated Time |
|----------|-----------|--------|----------------|
| P0 | OpenRouter smoke + request metadata support | ⬜ Planned | 1-2h |
| P1 | 4G+ in-domain evolution (gemini-flash, pop=25) | 🏃 Running | 5-10h |
| P2 | OpenRouter bridge runs: Grok + Gemini pop=5 | ⬜ Planned | 2-4h |
| P3 | OpenRouter pop=5 backbone sweep | ⬜ Planned | 10-20h |
| P4 | Pop=25 confirmation for 2-3 selected models | ⬜ Planned | 15-30h per config |
| P5 | Multiple runs for mean±std (≥3 independent runs) | ⬜ Planned | 15-30h per config |
| P6 | Convergence curve extraction | ⬜ Planned | 1h (script) |
| P7 | Average Rank computation (match SABR methodology) | ⬜ Planned | 2h (script) |
| P8 | Best heuristic code showcase | ⬜ Planned | 1h |

### Statistical Validity
SABR reports results averaged over 10 runs. For the paper:
- Minimum: 3 independent runs for mean±std
- Ideal: 5+ runs for robust statistics
- Each run: 5-10 hours with current setup (gemini-flash, pop=25, 10 gen)

---

## SABR Paper Reference (arXiv:2509.10486)

### QoE Formula
```
QoE = Σ q(R_n) - δ|q(R_{n+1})-q(R_n)| - μΣT_n
where q(R)=R, δ=1, μ=4.3 (3G) / 40 (4G+), N=49
```

### SABR Reported Results
- 3G Ave Rank: 1.8
- 4G+ Ave Rank: 1.7
- OOD Ave Rank: 2.0
- Each method run 10 times, average reported

### Baselines in SABR paper
- Rule-based: BB, BOLA, QUETRA, RobustMPC
- RL-based: Pensieve, Comyco
- BC+RL: SABR

---

## Key Technical Details

### A1 Best Heuristic
- Algorithm: "future-sustainable heuristic"
- 5th-percentile conservative throughput, 0.7 derating after rebuffer
- Myopic QoE + proximity bonus to sustainable bitrate (scaled by 4.0)
- Model: grok-4.20-beta, quetra seed, pop=25, mean fitness, 10 gen

### Infrastructure
- Remote server: `ssh heyun`
- Primary checkout: `/root/code/EoH-repro/`
- Current API: Vertex AI (gemini-2.5-flash), direct connection
- Planned multi-model API: OpenRouter, OpenAI-compatible chat completions endpoint
- Hard timeout fix applied to `eoh/src/eoh/llm/api_general.py`
- Canonical experiment runner: `experiments/run_eoh_target_experiment.sh`

### OpenRouter References Checked
- API reference: https://openrouter.ai/docs/api/reference/overview/
- Provider routing: https://openrouter.ai/docs/guides/routing/provider-selection
- FAQ / OpenAI-compatible API behavior: https://openrouter.ai/docs/faq
- Model list API: https://openrouter.ai/api/v1/models
