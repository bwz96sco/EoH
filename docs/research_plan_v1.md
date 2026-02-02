According to a document from **2024**, EoH’s core “hook” for a new domain is: **(1) define a task-specific score(...) function signature, (2) evaluate that code as a heuristic, and (3) use prompts that include parent heuristics’ descriptions + code to generate new heuristics via E1/E2/M1/M2/M3**.【 】【 】

So for ABR, the integration work is mostly about making **BB/BOLA/QUETRA/RobustMPC** look like *EoH-style “score functions”*, then feeding them into the EoH prompt “parent heuristics” section.



Below is a concrete integration plan and a practical way to “input the logic” of BB/BOLA/QUETRA/MPC so EoH can evolve it.



------





## **1) The key translation: “ABR action selection” → “EoH score function”**





EoH’s prompt examples are built around “score a set of options; pick argmax”; the ABR decision is exactly that: **score each bitrate level and pick the max**.【 】





### **Recommended common interface for EoH-ABR**





Define the candidate heuristic as:

```
def score(state, ctx) -> np.ndarray:
    """
    Returns scores for each bitrate action; higher is better.
    Must return shape (K,) where K = number of bitrate levels.
    """
```



- state: a **LLM-friendly** dict (or a small dataclass) extracted from SABR’s env observation.
- ctx: constants + action metadata (bitrates, chunk length, penalties, next chunk sizes, etc.)





Why dict? Because SABR (like Pensieve) uses a compact matrix state; SABR mentions a 6×8 state flattened to 48 dims for RL agents.【 】 For LLM-evolved code, giving **named fields** reduces indexing bugs dramatically.





### **Minimal state fields that cover BB/BOLA/QUETRA/MPC logic**





These four baselines draw from a small shared set of concepts:



- buffer_s: current buffer in seconds (BB/BOLA/QUETRA all use it)
- last_bitrate_idx: to compute smoothness penalties (common QoE term)
- throughput_hist_mbps: needed for QUETRA/MPC (bandwidth estimation)
- next_chunk_sizes_bytes: vector size K for “if choose bitrate k, next chunk size is …” (needed for BOLA/MPC-like scoring)
- optionally: chunks_remaining, time_since_last, etc.





SABR’s QoE uses bitrate, smoothness, and rebuffer terms (with dataset-specific rebuffer penalty).【 】



------





## **2) How to “input the logic” of BB/BOLA/QUETRA/RobustMPC into EoH**





You don’t want to hand-wave “BB/BOLA/…” in English. You want to give EoH *parents* that are:



1. **Short** “thought” (1 sentence)
2. **Executable** score(state, ctx) code
3. **Same signature** across all parents
4. **Same style** (same variable names, same helper functions) so the LLM can recombine ideas





This is exactly how EoH’s E2 prompt is structured: task description → list of “No.1…No.5 heuristic description + code” → ask to identify common backbone and produce a new heuristic.【 】





### **Step-by-step: refactor each baseline into an EoH “parent”**





In SABR’s repo, rule-based baselines are provided (QUETRA / BOLA / BB / RobustMPC, etc.).【 】 Your integration job is:





#### **(A) Make each baseline a pure function**



Take each baseline’s decision logic and refactor to something like:



- action = select_action(state, ctx)
- convert to EoH “scores” by returning a score vector





Two good wrappers:



**Wrapper option 1: expose the baseline’s internal objective as a score**

(best for evolution because it shows “why” an action wins)



**Wrapper option 2: one-hot “argmax” wrapper**

(quick to integrate; weaker for recombination)

```
scores = np.full(K, -1e9)
scores[action] = 0.0
return scores
```



#### **(B) Normalize terminology across the 4 parents**



Even if the original codes use different variable names, rewrite into a shared vocabulary:



- B = state["buffer_s"]
- R = ctx["bitrates_kbps"] (or Mbps)
- sizes = state["next_chunk_sizes_bytes"]
- mu = ctx["rebuf_penalty"], delta = ctx["smooth_penalty"]





This “semantic alignment” is one of the highest-ROI steps for making E2-style crossover work.



------





## **3) Concrete “parent heuristics” you should feed EoH**





Below are **seed versions** (not claiming exact paper-perfect implementations) written in a consistent “score vector” style. In practice you can replace each seed with the exact SABR baseline logic (since SABR already includes them).【 】





### **Parent 1: Buffer-Based (BB / BBA-style)**





Buffer-based ABR is commonly structured around a **reservoir + cushion**: below a “reservoir” you stay conservative; above you ramp up, often linearly in the “cushion”.【 】

```
import numpy as np

def score(state, ctx):
    R = np.asarray(ctx["bitrates_kbps"], dtype=float)
    B = float(state["buffer_s"])

    reservoir = float(ctx.get("reservoir_s", 5.0))
    cushion   = float(ctx.get("cushion_s", 10.0))

    if B <= reservoir:
        target = R[0]
    elif B >= reservoir + cushion:
        target = R[-1]
    else:
        x = (B - reservoir) / max(cushion, 1e-6)
        target = R[0] + x * (R[-1] - R[0])

    # score by closeness to target bitrate
    return -np.abs(R - target)
```



### **Parent 2: BOLA-like**





BOLA is based on Lyapunov optimization; it uses buffer occupancy and utility per bitrate to choose a representation (in the paper pseudocode it selects an argmax of a ratio involving utility, buffer/backlog, and chunk size).【 】



A seed “BOLA-like score” often looks like: utility + buffer term, normalized by chunk size (so “big chunks” are penalized when buffer is tight).

```
import numpy as np

def score(state, ctx):
    R = np.asarray(ctx["bitrates_kbps"], dtype=float)
    sizes = np.asarray(state["next_chunk_sizes_bytes"], dtype=float)
    B = float(state["buffer_s"])

    # Utility: monotone, concave in bitrate (one simple choice)
    u = np.log(R / max(R[0], 1e-6) + 1e-6)

    V = float(ctx.get("V", 5.0))          # aggressiveness knob
    gamma = float(ctx.get("gamma", 0.0))  # offset knob

    # "BOLA-ish": trade utility+buffer against chunk size
    return (V * u + B - gamma) / np.maximum(sizes, 1.0)
```



### **Parent 3: QUETRA-like (queueing-theoretic buffer targeting)**





QUETRA models playback buffer as a queue (paper discusses an M/D/1/K queue model) and chooses bitrate to drive buffer occupancy toward an “ideal” computed from the model, aiming for stability without heavy parameter tuning.【 】



A seed version you can use for EoH evolution: compute a **target buffer** based on throughput/bitrate “utilization”, then choose bitrate that moves buffer toward that target.

```
import numpy as np

def score(state, ctx):
    R = np.asarray(ctx["bitrates_kbps"], dtype=float)
    B = float(state["buffer_s"])
    tput = np.asarray(state["throughput_hist_mbps"], dtype=float)
    bw = float(np.median(tput[-5:])) if tput.size else 1.0  # Mbps

    # Convert Mbps -> Kbps
    bw_kbps = 1000.0 * bw

    # Utilization proxy per action (bitrate / bandwidth)
    rho = R / max(bw_kbps, 1e-6)

    # Target buffer: higher when utilization is high (riskier), lower when safe.
    # (This is a simplification inspired by “buffer as queue occupancy” thinking.)
    Bmin = float(ctx.get("buffer_min_s", 2.0))
    Bmax = float(ctx.get("buffer_max_s", 20.0))
    target = np.clip(Bmin + (Bmax - Bmin) * rho, Bmin, Bmax)

    # Prefer actions whose target is near current buffer (don’t destabilize)
    # and mildly prefer higher bitrate among those.
    return -(np.abs(target - B)) + 1e-3 * R
```



### **Parent 4: RobustMPC-like (short-horizon planning)**





SABR describes RobustMPC as maximizing a QoE metric over a horizon (e.g., 5 chunks).【 】 A common RobustMPC flavor predicts bandwidth via harmonic mean of recent throughputs and applies a robustness margin based on past error.【 】



A seed short-horizon evaluator:

```
import numpy as np

def _harmonic_mean(x):
    x = np.asarray(x, dtype=float)
    x = x[x > 1e-6]
    if x.size == 0:
        return 1.0
    return float(x.size / np.sum(1.0 / x))

def score(state, ctx):
    R = np.asarray(ctx["bitrates_kbps"], dtype=float)
    sizes = np.asarray(state["next_chunk_sizes_bytes"], dtype=float)
    last = int(state["last_bitrate_idx"])
    B0 = float(state["buffer_s"])

    delta = float(ctx["smooth_penalty"])
    mu = float(ctx["rebuf_penalty"])
    chunk_len = float(ctx["chunk_len_s"])

    tput = np.asarray(state["throughput_hist_mbps"], dtype=float)
    bw_mbps = _harmonic_mean(tput[-5:]) if tput.size else 1.0

    # Robustness margin (simple)
    margin = float(ctx.get("robust_margin", 0.9))
    bw_mbps = max(bw_mbps * margin, 0.1)

    # Predict download time for next chunk for each bitrate
    bw_Bps = bw_mbps * 1e6 / 8.0
    dl = sizes / max(bw_Bps, 1.0)  # seconds

    # One-step QoE proxy (MPC would do multi-step; keep it light for evolution)
    rebuf = np.maximum(dl - B0, 0.0)
    smooth = np.abs(R - R[last])

    # Reward proxy: bitrate - smooth - rebuffer_penalty*rebuffer
    return R - delta * smooth - mu * rebuf
```

> In your real integration, you can replace the above with the exact SABR run_rmpc_* planning logic, but *keep the same function signature and naming*. SABR explicitly lists these rule-based baselines and provides scripts to run them.【 】



------





## **4) Integration plan: tasks/todos focused on** 

## **EoH ⟷ ABR wiring**





You said you already have the env and EoH implementation; this checklist is only the “glue”.





### **Phase 1 — Define the ABR heuristic API for EoH**





**Deliverable: abr_api.py**



- Implement extract_state(env_obs, env_info) -> dict

  Make sure it fills buffer_s, last_bitrate_idx, throughput_hist_mbps, next_chunk_sizes_bytes, …

- Implement make_ctx(config) -> dict

  Must include bitrates_kbps, chunk_len_s, and QoE constants (smooth_penalty, rebuf_penalty), which SABR ties to dataset configs.【 】【 】

- Decide what you allow inside evolved code:

  

  - only numpy
  - max horizon (if you allow planning)
  - no randomness (EoH emphasizes this)【 】

  







### **Phase 2 — Port BB/BOLA/QUETRA/RobustMPC into “EoH parent format”**





**Deliverable: seed_heuristics.py (or 4 separate files)**



- For each baseline: refactor into score(state, ctx) (same style, same names)

- Add a one-sentence “thought” for each (BB: reservoir/cushion; BOLA: utility+buffer; QUETRA: buffer-as-queue target; MPC: predict+penalize rebuffer)

- Sanity checks:

  

  - always return np.ndarray shape (K,)
  - return finite values; replace NaN with -1e9 fallback
  - deterministic

  







### **Phase 3 — Tell EoH to use these as** 

### **parents**

###  **(not just evaluation baselines)**





This is the crux of your question: you want EoH to **evolve the logic** of known ABR heuristics.



**Deliverables:**



- abr_prompt_templates.py
- minimal change in EoH “problem” wrapper to insert these parents into the prompt





Tasks:



- **Initialization**: you can still let EoH generate random-ish ABR heuristics from scratch, but it’s usually better to **seed** the initial population with your 4 baseline parents (+1 simple rate-based heuristic as the 5th parent, since EoH often uses p=5).【 】
- **E2 prompt**: build the parent section containing your 4 baselines (+optional 5th) in the exact “No.1…No.5” structure EoH uses.【 】
- **M2 prompt for ABR**: this is *perfect* for “tune the knobs” (reservoir/cushion, V, robustness margin, etc.) because M2 is explicitly “modify parameters of one selected heuristic.”【 】







### **Phase 4 — Feedback formatting: give the LLM “what failed”**





ABR is tricky because the same average QoE can hide totally different failure modes.



**Deliverable: abr_feedback.py**



- When evaluating a candidate heuristic, log:

  

  - mean QoE

  - mean rebuffer seconds

  - mean bitrate

  - mean bitrate switch magnitude

  - 

    # **stalls**

    

  

- Summarize these into 3–6 lines that M1 can use:

  

  - “High QoE but stalls on low throughput traces”
  - “Very stable but too conservative (low bitrate)”

  

- Feed this summary into **M1 prompt** (modify one heuristic for better performance).【 】







### **Phase 5 — Fitness definition aligned with ABRBench evaluation**





SABR defines QoE with bitrate term, smoothness penalty, and rebuffer penalty (µ differs between ABRBench-3G and ABRBench-4G+).【 】

Also SABR’s repo shows how datasets and rule-based baselines are run/evaluated across trace sets.【 】



**Deliverable: fitness.py**



- Fitness = mean QoE over multiple trace sets (not just one) to avoid overfitting
- Optional: incorporate “average rank across sets” style scoring (SABR reports ranks across trace sets).【 】





------





## **5) Concrete EoH-ABR prompt template that includes BB/BOLA/QUETRA/MPC as parents**





EoH emphasizes a 5-part prompt structure: task description, strategy-specific prompt, expected output, note, parent heuristics.【 】



Here’s a concrete **E2** template you can drop into your “prompt factory”:

```
[Task Description]
I need help designing a new heuristic for Adaptive Bitrate (ABR) streaming.
At each video chunk, the client must choose one bitrate action a ∈ {0..K-1}.
The goal is to maximize total QoE over an episode:
QoE = Σ bitrate_kbps[a_t]  - δ * |bitrate_kbps[a_t] - bitrate_kbps[a_{t-1}]|
      - μ * rebuffer_time_seconds
Use only the information in 'state' (past observations) and 'ctx' (constants).

[Strategy-Specific Prompt: E2]
I have several existing ABR heuristics with their codes as follows.
Please help me design a new heuristic that is different from the given ones but can be motivated by them.
Firstly, identify the common idea in the provided heuristics.
Secondly, based on the backbone idea, describe your new heuristic in ONE sentence.
Thirdly, implement it in Python as a function named 'score'.

[Expected Output]
Return exactly:
1) One sentence description.
2) A Python code block that defines `def score(state, ctx):` and returns `scores` (np.ndarray shape (K,)).

[Note]
- `state` is a dict with keys:
  buffer_s: float
  last_bitrate_idx: int
  throughput_hist_mbps: np.ndarray
  next_chunk_sizes_bytes: np.ndarray shape (K,)
- `ctx` is a dict with keys:
  bitrates_kbps: np.ndarray shape (K,)
  chunk_len_s: float
  smooth_penalty (δ): float
  rebuf_penalty (μ): float
- Avoid randomness. Maintain self-consistency. Do not give additional explanations.
- Keep compute light (no loops over long horizons; if planning, horizon ≤ 5).

[Parent Heuristics]
No.1 Heuristic description: <BB one-sentence>
Code:
```python
... BB score() ...
```

No.2 Heuristic description: 

Code:

```
... BOLA score() ...
```

No.3 Heuristic description: 

Code:

```
... QUETRA score() ...
```

No.4 Heuristic description: 

Code:

```
... RobustMPC-like score() ...
```

No.5 Heuristic description: 

Code:

```
... rate-based score() ...
This is directly patterned after EoH’s E2 prompt design (identify common idea → new heuristic → implement `score`).【 [oai_citation:25‡Liu et al. - 2024 - Evolution of Heuristics Towards Efficient Automatic Algorithm Design Using Large Language Model.pdf](sediment://file_00000000d2087209b484c2905d055c26)】

### Where to put the 4 ABR baselines?
- **Initialization population**: seed them as part of initial population (so they can be selected as parents early).
- **Parent section**: when EoH selects parents, ensure your parent pack often includes these baselines (or their best evolved descendants).

---

## 6) Code skeleton for the *integration* (not env reimplementation)

EoH’s repo shows you run examples and evaluation by ensuring “function name/input/output must align with the evaluation block”.【 [oai_citation:26‡GitHub](https://github.com/FeiLiu36/EoH)】 So you just need a thin ABR “evaluation block” that:

1) loads candidate `score(state, ctx)`
2) runs SABR env episodes
3) returns fitness

Skeleton:

```python
# eoh_abr_problem/eval_candidate.py
import importlib.util
import numpy as np

from abr_api import extract_state, make_ctx
# from sabr_env_wrapper import make_env  # you’ll wrap SABR env here

def load_score_fn(py_path: str):
    spec = importlib.util.spec_from_file_location("candidate_heuristic", py_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.score

def evaluate_candidate(py_path: str, env, config, traces):
    score_fn = load_score_fn(py_path)
    ctx = make_ctx(config)

    qoes = []
    for trace in traces:
        obs, info = env.reset(trace=trace)
        done = False
        last_action = 0
        while not done:
            state = extract_state(obs, info, last_action=last_action, ctx=ctx)
            scores = score_fn(state, ctx)
            action = int(np.argmax(scores))
            obs, reward, done, info = env.step(action)
            last_action = action

        qoes.append(info["episode_qoe"])  # or compute from logged terms

    return float(np.mean(qoes)), {"qoes": qoes}
```

**Tip:** keep extract_state(...) outside the candidate heuristic so the LLM doesn’t have to do brittle indexing.



------





## **7) Experimental protocol aligned with SABR/ABRBench**





From SABR’s repo: you download ABRBench and can evaluate across test and OOD sets; rule-based baselines are included (QUETRA/BOLA/BB/RobustMPC).【 】

From SABR’s paper: QoE uses bitrate, smoothness penalty, and rebuffer penalty, with µ set differently for ABRBench-3G vs ABRBench-4G+.【 】



A clean protocol:





### **Datasets / splits**





- **Train (for evolution fitness):** ABRBench-3G *train* trace sets (or a subset of trace sets for speed)

- **Validation (selection / early stopping):** held-out trace sets from ABRBench-3G

- **Test (final):**

  

  - ABRBench-3G test + OOD
  - ABRBench-4G+ test + OOD (true generalization)

  







### **Metrics to report**





- Mean QoE (primary)
- Mean rebuffer seconds (and stall rate)
- Mean bitrate
- Mean |Δ bitrate| (smoothness)
- Also report average rank across trace sets (SABR does rank-based comparisons across sets).【 】







### **Baselines**





- Rule-based: BB, BOLA, QUETRA, RobustMPC (already in SABR)【 】
- Learning-based (optional): Pensieve / Comyco / SABR (SABR repo provides)【 】







### **Ablations (important for a paper)**





Because EoH’s paper shows performance depends on prompt strategies and thoughts+codes,【 】 you can do ABR analogs:



- EoH-ABR (full)
- EoH-ABR without E2 (only E1)
- EoH-ABR without M2 (no parameter tuning)
- Code-only variant (no “thought”) analogous to EoC【 】
- With vs without **baseline seeding** (BB/BOLA/QUETRA/MPC as initial population)





------





## **8) Practical advice: how to make evolution “actually evolve the logic” (not just random tweaks)**





If you just paste raw baseline codes, you’ll often get tiny surface mutations. To push real “logic evolution”:



1. **Expose knobs explicitly**

   e.g., reservoir_s, cushion_s, V, robust_margin, etc.

   Then M2 (“modify parameters”) becomes very effective.【 】

2. **Force common scaffolding**

   Give all parents the same skeleton: compute bw_est, compute dl_time, compute rebuf_proxy, compute smooth_proxy, combine.

   Then E2 can mix-and-match pieces.

3. **Make “safe fallback” a shared idiom**

   e.g., if throughput history empty → pick lowest bitrate.

   This avoids brittle heuristics that fail frequently and waste evaluation budget.

4. **Feed failure-mode summaries into M1**

   M1 is explicitly “modify one heuristic for better performance”.【 】

   Give it *why it failed* (stall-heavy, oscillation-heavy, too conservative).





------



If you want, I can also propose a **fifth parent heuristic** that’s intentionally “orthogonal” (pure rate-based with safety factor) so E2 has a broader backbone than just buffer-driven methods—this tends to help exploration when the parent set is small (only 4).