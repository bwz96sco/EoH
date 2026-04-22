# EoH-ABR: Advanced Exploration Strategies (Post-88.9 Breakthrough)

**Date**: April 21, 2026  
**Status**: Research Proposal / Strategy Document  
**Objective**: To overcome the performance plateau (current best: 88.9) in ABRBench-3G/4G+ by pivoting from simple logic evolution to architectural, predictive, and adversarial co-evolution.

---

## 1. Strategy: Evolving Virtual Sensors (Neural-Symbolic Hybrid)

**The Problem**: LLMs often generate convoluted `if-else` trees that are hard to interpret and prone to overfitting local noise.
**The Solution**: Instead of evolving the *entire* decision logic, we evolve a set of **"Virtual Sensors"** (complex mathematical features) and feed them into a rigid, deterministic controller.

### Implementation Path:
*   **Target Function**: `compute_indicators(state, ctx) -> dict`
*   **Evolutionary Goal**: Evolve functions that capture "Network Stress," "Buffer Momentum," or "Stall Probability."
*   **Controller**: A fixed, human-verified policy (e.g., a simple Threshold-based logic) that uses these evolved indicators.
*   **Rationale**: By decoupling "Feature Engineering" from "Decision Logic," we leverage the LLM’s ability to find complex non-linear relationships without letting it mess up the basic physics of ABR control.

---

## 2. Strategy: Evolving Bandwidth Predictors for Robust-MPC

**The Problem**: Model Predictive Control (MPC) is highly effective but its performance is gated by the accuracy of its bandwidth predictor.
**The Solution**: Evolve the **Bandwidth Prediction Operator** within an MPC framework.

### Implementation Path:
*   **Framework**: Use a fixed `RobustMPC` implementation that takes a `predicted_bandwidth` as input.
*   **Target Function**: `predict_next_chunk_bandwidth(history, state) -> float`
*   **Evolutionary Focus**: Encourage the LLM to use historical trends, RTT variance, and buffer slope to predict the next 5-10 seconds of bandwidth.
*   **Rationale**: This addresses the "Predictive Accuracy" bottleneck directly. If EoH can evolve a predictor that is robust to 3G/4G signal fading patterns, the underlying MPC logic will naturally perform better.

---

## 3. Strategy: Co-Evolutionary Adversarial Traces (Shadow Opponent)

**The Problem**: Current heuristics are over-optimizing for the static ABRBench-3G trace set, leading to poor generalization (overfitting).
**The Solution**: Introduce a **Generative Adversarial Heuristic Search (GAHS)**.

### Implementation Path:
*   **Pop A**: Heuristics (evolved by EoH).
*   **Pop B**: "Malicious" Network Traces (evolved by a separate LLM agent).
*   **Mechanism**:
    1.  LLM-B generates synthetic network traces designed to "break" the current best Heuristics in Pop A (e.g., traces with specific oscillation frequencies).
    2.  LLM-A (EoH) must evolve Heuristics that perform well on *both* the original ABRBench and the new adversarial traces.
*   **Rationale**: This forces the evolution of **Global Robustness** rather than just local optimization.

---

## 4. Strategy: Semantic Knowledge Synthesis (Inter-Island)

**The Problem**: Merging codes from different "Island" populations (`3g-island-round1`) often results in messy, broken code.
**The Solution**: Use the LLM to perform **Concept Synthesis** instead of Code Merging.

### Implementation Path:
*   **The "Knowledge Prompt"**: 
    > "Island A discovered that tracking Buffer Slope is key for 3G stability. Island B found that RTT spikes are a leading indicator of congestion. Do not look at their code. Create a unified ABR theory that incorporates both insights into a new score function."
*   **Workflow**: Periodically extract "Thoughts" from the top 5% of each island, summarize them into a "Unified Meta-Prompt," and seed a new "Super-Island" with it.
*   **Rationale**: This replicates how human researchers combine papers—by synthesizing *ideas* rather than copy-pasting code.

---

## 5. Strategy: Invariant-Driven Evolution (Control Theory Constraints)

**The Problem**: Evolved heuristics sometimes perform "dangerous" actions (e.g., picking high bitrate when buffer is critical) that lead to massive penalties.
**The Solution**: Embed **Physical Invariants** and Control Theory constraints into the evolutionary process.

### Implementation Path:
*   **Hard Constraints**: In the system prompt and the `score()` wrapper, define **Universal Laws**:
    *   *Law of Conservation*: Bitrate must not increase if `buffer < threshold_min`.
    *   *Smoothness Invariant*: Avoid bitrate jumps > 2 levels unless bandwidth has increased by 3x.
*   **Reward Shaping**: Add heavy penalties in the `evaluate` function for any heuristic that attempts to violate these laws, forcing the LLM to search for "Stable Solutions."
*   **Rationale**: Narrowing the search space to "Physically Plausible" solutions allows the evolution to spend more budget on fine-tuning high-quality logic.

---

## Roadmap for Next Wave

1.  **Phase A (Adversarial)**: Run a small-scale test with 50 synthetic "Malicious Traces" to verify if best-at-88.9 drops in performance.
2.  **Phase B (Neural-Symbolic)**: Pivot one island to evolve *only* the `stress_indicator()` function.
3.  **Phase C (MPC-Predictor)**: Wrap the RobustMPC core and target the `predictor` function for evolution in a 4G+ environment.
