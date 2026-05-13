# Paper Outline: EoH vs SABR for Adaptive Bitrate Streaming

## Working Title
*"Evolution of Heuristics: LLM-Driven Code Evolution vs. Reinforcement Learning for Adaptive Bitrate Streaming"*

## Core Story Line
**Paradigm comparison**: EoH offers an interpretable alternative to RL-heavy ABR design. Instead of training neural network policies from offline trajectories, it uses LLMs as search operators to evolve **readable code heuristics** directly in program space and selects them by simulator-based QoE.

### Three Core Advantages of EoH over RL-based approaches:
1. **Interpretability**: Evolved heuristics are readable Python code with clear decision logic
2. **No expert demonstrations or offline policy-training data**: Evolution uses simulator-based fitness evaluation instead of behavior-cloning or RL-training trajectories
3. **Transferable code artifacts**: Evolved heuristics can be directly evaluated in new network regimes, though direct in-domain evolution remains necessary for best results

---

## Paper Structure

### 1. Introduction
- ABR streaming problem and the evolution from rule-based → RL → BC+RL (SABR)
- Limitations of RL-based approaches: black-box policies, large training data requirements, poor interpretability, domain-specific training
- EoH's core idea: LLMs as search operators in program space, evolving interpretable heuristics
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
#### 3.1 EoH Framework Overview
- Population initialization with seed heuristics
- Five LLM operators: E1 (evolve from one), E2 (evolve from two), M1 (mutate description), M2 (mutate code), M3 (crossover)
- Fitness evaluation via ABR simulation
- Selection: probabilistic rank-based selection with greedy population management

#### 3.2 ABR Problem Formulation for EoH
- Score function interface: `score(state) → np.ndarray` over bitrate candidates
- State representation: buffer level, throughput history, video chunk sizes, last quality, rebuffer history
- QoE evaluation: same formula as SABR (bitrate utility - smoothness penalty - rebuffer penalty)

#### 3.3 Seed Heuristic Design
- Translating classical ABR algorithms (BB, BOLA, QUETRA, RobustMPC, Rate-based) into score function format
- Each seed provides a different "starting point" in heuristic space
- Population expansion: cloning best seed to fill population

### 4. Experimental Setup
#### 4.1 Datasets
- **ABRBench-3G**: FCC-16, FCC-18, Oboe, Puffer-21, Puffer-22, HSR (OOD)
- **ABRBench-4G+**: Norway3G, Lumos4G, Lumos5G, SolisWi-Fi, Ghent (OOD), Lab (OOD)
- Train/test split following SABR protocol

#### 4.2 Baselines
- Rule-based: BB, BOLA, QUETRA, RobustMPC
- RL-based: Pensieve, Comyco (from SABR paper)
- BC+RL: SABR (state-of-the-art)

#### 4.3 Evaluation Metrics
- Per-dataset mean QoE (averaged over all traces)
- Average Rank across trace sets (following SABR methodology)
- Win/loss count vs baselines
- For final main tables: mean±std across independent EoH runs; current best values are strong single-run evidence

#### 4.4 EoH Configuration
- Best config (A1): quetra seed, pop=25, 10 generations, mean fitness
- LLM backbone: grok-4.20-beta (3G), gemini-2.5-flash (4G+)
- Single-process evolution (EXP_N_PROC=1)
- Canonical runner: `experiments/run_eoh_target_experiment.sh`

### 5. Results

#### 5.1 Main Results (Table 1)
- **ABRBench-3G**: EoH vs SABR vs classical baselines (6 datasets)
  - Current result: A1 wins 6/6 vs SABR; avg QoE `88.9`
- **ABRBench-4G+**: EoH vs SABR vs classical baselines (6 datasets)
  - Current result: Vertex flash QUETRA pop25 wins 6/6 vs SABR; avg QoE `1578.1` vs SABR `1188.6` (`+32.8%`)
  - Caveat: repeat runs and Solis-Wi-Fi/ceiling-score artifact checks are required before final camera-ready claims

#### 5.2 Zero-Shot Transfer (Table 2)
- 3G-evolved heuristic evaluated on 4G+ (and vice versa)
- Comparison with SABR (which was trained on the target domain)
- Current evidence:
  - 3G→4G+: EoH avg `1027.4` vs SABR `1188.6`, loses 0/6 SABR datasets but beats several classical baselines
  - 4G+→3G: EoH avg `85.5` vs computed SABR avg `83.3`, wins 4/6 SABR datasets, but stays below direct 3G A1 `88.9`
- Analysis: transfer is non-trivial but secondary; in-domain evolution is the stronger result

#### 5.3 LLM Backbone Sensitivity (Table 3)
- **Legacy provider-mixed evidence**: grok, gemini-flash/pro/lite, GLM-5.1, sonnet-4-6-thinking, and gpt-5.4-mini runs provide useful pilot evidence
- **Main-paper caution**: model family and provider route are currently confounded by grok2api, Vertex AI, SiliconFlow, and hybgzs route behavior
- **Clean version**: use OpenRouter bridge/sweep runs if the paper needs a main-table LLM robustness claim
- Key bounded finding: results suggest the framework is not obviously tied to one LLM, but provider-controlled confirmation is still pending

#### 5.4 Ablation Studies (Table 4)
- **Seed impact**: quetra vs bb vs bola vs mpc vs rate_based
- **Population size**: pop=5 vs pop=25
- **Convergence curve**: QoE per generation

#### 5.5 Interpretability Analysis
- Showcase the best evolved heuristic's code
- Explain the decision logic (e.g., A1's "future-sustainable" strategy)
- Compare with SABR's black-box neural network
- Highlight novel algorithmic insights discovered through evolution

### 6. Discussion
- **Paradigm comparison**: When to choose EoH vs RL for algorithm design
  - EoH: rapid prototyping, interpretable solutions, no demonstration data, simulator-available domains
  - RL: high-dimensional state/action, large-scale deployment, continuous adaptation
- **Computational cost**: EoH evolution cost vs RL training cost
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

1. **Fig 1**: EoH framework overview (population → LLM operators → evaluation → selection cycle)
2. **Fig 2**: Score function interface for ABR (state → scores → bitrate selection)
3. **Fig 3**: Per-dataset QoE comparison bar chart (EoH vs SABR vs baselines)
4. **Fig 4**: Convergence curve (QoE vs generation)
5. **Fig 5**: LLM backbone sensitivity (bar chart with error bars)
6. **Fig 6**: Best evolved heuristic code snippet with annotations

---

## Target Venues (to discuss)
- **Networking**: ACM SIGCOMM, ACM CoNEXT, IEEE INFOCOM, ACM IMC
- **AI/ML applications**: AAAI, IJCAI, NeurIPS (workshop)
- **Evolutionary computation**: GECCO, IEEE CEC
- **Cross-disciplinary**: Nature Communications, IEEE TNSM, IEEE/ACM ToN
