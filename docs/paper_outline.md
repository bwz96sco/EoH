# Paper Outline: EoABR vs SABR for Adaptive Bitrate Streaming

## Working Title
*"EoABR: LLM-Driven Code Evolution vs. Reinforcement Learning for Adaptive Bitrate Streaming"*

## Core Story Line
**Paradigm comparison**: EoABR offers an interpretable alternative to RL-heavy ABR design. Instead of training neural network policies from offline trajectories, it uses LLMs as search operators to evolve **readable code heuristics** directly in program space and selects them by simulator-based QoE.

Naming convention: use **EoABR** for the paper-facing ABR method. Reserve **EoH** for the original general method in related work or literal code/tool names.

### Three Core Advantages of EoABR over RL-based approaches:
1. **Interpretability**: Evolved heuristics are readable Python code with clear decision logic
2. **No expert demonstrations or offline policy-training data**: Evolution uses simulator-based fitness evaluation instead of behavior-cloning or RL-training trajectories
3. **Transferable code artifacts**: Evolved heuristics can be directly evaluated in new network regimes, though direct in-domain evolution remains necessary for best results

---

## Paper Structure

### 1. Introduction
- ABR streaming problem and the evolution from rule-based → RL → BC+RL (SABR)
- Limitations of RL-based approaches: black-box policies, large training data requirements, poor interpretability, domain-specific training
- EoABR's core idea: LLMs as search operators in program space, evolving interpretable ABR heuristics
- Key contributions:
  - First study of LLM-driven evolutionary **code-heuristic synthesis** for ABR as an interpretable alternative to BC+RL systems such as SABR
  - Competitive or superior single-run performance vs state-of-the-art BC+RL (SABR) on both ABRBench-3G and ABRBench-4G+
  - Ablation studies on seed heuristics, population size, and model/provider sensitivity, with provider-controlled LLM robustness left as a bounded claim
  - Interpretable analysis of evolved heuristics revealing novel ABR strategies

### 2. Related Work
- **ABR algorithms**: Rule-based (BB, BOLA, QUETRA, RobustMPC) → RL (Pensieve, Comyco) → BC+RL (SABR)
- **LLM for code generation / optimization**: FunSearch, EoH, AlphaEvolve, AlphaCode
- **LLMs for networking / ABR design**: LLM-ABR and related LLM-assisted network algorithm design work
- **Automated algorithm design**: Neural Architecture Search (NAS), AutoML, program synthesis
- **Evolutionary computation with LLMs**: LLM-guided mutation operators, code-level evolution

### 3. Method
#### 3.1 EoABR Framework Overview
- EoABR adapts the original EoH-style code-evolution framework to ABR heuristic synthesis
- Population initialization with seed heuristics
- Five LLM operators: E1 (evolve from one), E2 (evolve from two), M1 (mutate description), M2 (mutate code), M3 (crossover)
- Fitness evaluation via ABR simulation
- Selection: probabilistic rank-based selection with greedy population management

#### 3.2 ABR Problem Formulation for EoABR
- Score function interface: `score(state) → np.ndarray` over bitrate candidates
- State representation: buffer level, throughput history, video chunk sizes, last quality, rebuffer history
- QoE evaluation: same formula as SABR (bitrate utility - smoothness penalty - rebuffer penalty)

#### 3.3 Seed Heuristic Design
- Translating classical ABR algorithms (BB, BOLA, QUETRA, RobustMPC, Rate-based) into score function format
- Each seed provides a different "starting point" in heuristic space
- Population expansion: round-robin expansion of selected seed families to the target population size

### 4. Experimental Setup
#### 4.1 Datasets
- **ABRBench-3G**: FCC-16, FCC-18, Oboe, Puffer-21, Puffer-22, HSR (OOD)
- **ABRBench-4G+ paper protocol**: Lumos4G, Lumos5G, Solis-Wi-Fi, Ghent (OOD), Lab (OOD)
- **Local extended evaluator only**: Norway3G can be retained for appendix stress testing, but it is not reported in the SABR paper and must not be mixed into paper-sourced SABR tables
- Train/test split following SABR protocol

#### 4.2 Baselines
- Rule-based: BB, BOLA, QUETRA, RobustMPC
- RL-based: Pensieve, Comyco (from SABR paper)
- BC+RL: SABR (state-of-the-art)
- Provenance rule: SABR paper values must cite Tables IV, V, or VI; local reruns must cite run artifacts and must be labeled separately

#### 4.3 Evaluation Metrics
- Per-dataset mean QoE (averaged over all traces)
- Average Rank across trace sets (following SABR methodology)
- Win/loss count vs baselines
- For final main tables: mean±std across independent EoABR runs for each model row; do not average across LLM backbones

#### 4.4 EoABR Configuration
- Formal initialization: mixed pop=25 with five seed families and five individuals per family
- Formal LLM transport: OpenRouter chat completions with frozen model IDs, route policy, and run manifests
- Main model rows: EoABR (Grok 4.3), EoABR (DeepSeek V4 Pro), and optional EoABR (Gemini 3 Flash Preview)
- Reference ablation model: selected from the main Table 1 rows after OpenRouter smoke tests
- Canonical runner: `experiments/run_eoh_target_experiment.sh`

### 5. Results

#### 5.1 Main Results (Table 1)
- **ABRBench-3G**: EoABR model rows vs SABR vs classical baselines, keeping five test sets and HSR OOD separated
  - Planned rows: EoABR (Grok 4.3), EoABR (DeepSeek V4 Pro), and optional EoABR (Gemini 3 Flash Preview)
  - Pilot reference: A1 local six-set avg QoE `88.9`; any win count must cite the exact comparator source and is not a final OpenRouter result
- **ABRBench-4G+**: EoABR model rows vs SABR vs classical baselines, using Lumos4G/Lumos5G/Solis-Wi-Fi plus Ghent/Lab OOD from the SABR paper
  - Pilot reference: Vertex flash QUETRA pop25 reaches local six-set avg QoE `1578.1`, but this local six-set average has no sourced SABR comparator
  - Caveat: OpenRouter reruns and Solis-Wi-Fi/ceiling-score artifact checks are required before final camera-ready claims

#### 5.2 Zero-Shot Transfer (Table 2)
- 3G-evolved heuristic evaluated on 4G+ (and vice versa)
- Comparison with SABR (which was trained on the target domain)
- Current evidence:
  - 3G→4G+: pilot EoABR avg `1027.4` on the local six-set evaluator; do not compare it with SABR unless a local SABR rerun artifact is found
  - 4G+→3G: pilot EoABR avg `85.5` vs computed SABR avg `83.3`; label `83.3` as derived from SABR Tables IV/VI, not a paper-reported average
- Analysis: transfer is non-trivial but secondary; in-domain evolution is the stronger result

#### 5.3 LLM Backbone Sensitivity (Table 3)
- **Legacy provider-mixed evidence**: grok, gemini-flash/pro/lite, GLM-5.1, sonnet-4-6-thinking, and gpt-5.4-mini runs provide useful pilot evidence
- **Main-paper caution**: model family and provider route are currently confounded by grok2api, Vertex AI, SiliconFlow, and hybgzs route behavior
- **Clean version**: Table 1 reports selected main models separately; Table 3 provides additional OpenRouter screening and reliability/cost evidence for broader model families
- Key bounded finding: results suggest the framework is not obviously tied to one LLM, but provider-controlled confirmation is still pending

#### 5.4 Ablation Studies (Table 4)
- **Initialization dominance analysis**: post-hoc analysis of which seed families dominate the mixed-pop25 Table 1 artifacts
- **Single-family initialization ablation**: `bb`, `bola`, `quetra`, `robust_mpc`, and `rate_based` pop25 starts
- **Population size**: matched `QUETRA-pop5` vs `QUETRA-pop25` and `Mixed-pop5` vs `Mixed-pop25`
- **Convergence curve**: QoE per generation from formal OpenRouter artifacts

#### 5.5 Interpretability Analysis
- Showcase the best evolved heuristic's code
- Explain the decision logic (e.g., A1's "future-sustainable" strategy)
- Compare with SABR's black-box neural network
- Highlight novel algorithmic insights discovered through evolution

### 6. Discussion
- **Paradigm comparison**: When to choose EoABR vs RL for algorithm design
  - EoABR: rapid prototyping, interpretable solutions, no demonstration data, simulator-available domains
  - RL: high-dimensional state/action, large-scale deployment, continuous adaptation
- **Computational cost**: EoABR evolution cost vs RL training cost
- **LLM dependency**: model/provider stability, API cost, invalid offspring, timeout behavior
- **Limitations**: 
  - Current main results are mostly single-run and need mean±std confirmation
  - Single-step decision (no explicit temporal planning)
  - Population diversity management
  - Dependence on seed quality
  - Provider-controlled LLM-backbone robustness not yet established

### 7. Conclusion
- Summary of contributions
- Future work: multi-objective evolution, online adaptation, larger action spaces

---

## Figure Plan

1. **Fig 1**: EoABR framework overview (population → LLM operators → evaluation → selection cycle)
2. **Fig 2**: Score function interface for ABR (state → scores → bitrate selection)
3. **Fig 3**: Per-dataset QoE comparison bar chart (EoABR model rows vs SABR vs baselines)
4. **Fig 4**: Convergence curve (QoE vs generation)
5. **Fig 5**: LLM backbone sensitivity (bar chart with error bars)
6. **Fig 6**: Best evolved heuristic code snippet with annotations

---

## Target Venues (to discuss)
- **Networking**: ACM SIGCOMM, ACM CoNEXT, IEEE INFOCOM, ACM IMC
- **AI/ML applications**: AAAI, IJCAI, NeurIPS (workshop)
- **Evolutionary computation**: GECCO, IEEE CEC
- **Cross-disciplinary**: Nature Communications, IEEE TNSM, IEEE/ACM ToN
