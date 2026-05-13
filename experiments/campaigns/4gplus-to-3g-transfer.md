# Series: 4G+ to 3G Transfer

## Objective
补齐 `4G+ -> 3G` reverse transfer：先在 ABRBench-4G+ 上进化一个 heuristic，
再不重新训练地评估到 ABRBench-3G 六个数据集，判断 4G+ 学到的策略是否能跨网络 regime 泛化。

## Primary Metric
- `ABRBench-3G (avg)` from `collect_results.py` / `results_summary.csv`

## Baseline Reference
- 3G mainline best: `20260402-3g-hardset-round2-a1-r1`, `ABRBench-3G = 88.8697`
- 3G online RobustMPC: `78.2371`
- 3G overall BeamSearch: `96.9909`
- Existing 3G -> 4G+ transfer: `1027.4` on ABRBench-4G+, below SABR `1188.6`
- Existing 4G+ in-domain Vertex flash result: `20260427-081532-4gplus-a1-config-vertexflash-r1`, `ABRBench-4G+ = 1578.1410`

## Fixed Factors
- Runner: `experiments/run_eoh_target_experiment.sh`
- Evolution target: `ABRBench-4G+`
- Eval datasets: `FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,HSR`
- Fitness: `mean`
- Seed: `quetra`
- Phase 2: reuse existing SABR baselines; do not rerun baseline generation

## Planned Runs

| Label | Key Change | Run ID | Status |
|-------|------------|--------|--------|
| r1 | Vertex `google/gemini-2.5-pro`, `QUETRA + pop5 + gen10`, evaluate on 3G suite | `20260507-4gplus-to-3g-vertexpro-r1` | completed |

## Analysis
- `r1` completed on heyun and generated the canonical run artifacts under
  `experiments/results/20260507-4gplus-to-3g-vertexpro-r1/`.
- Reverse transfer result: `ABRBench-3G (avg) = 85.5195`.
- This is above online RobustMPC (`78.2371`) and all simple rule baselines, but below:
  - current 3G mainline best A1: `88.8697`
  - BeamSearch: `96.9909`
- Per-dataset EoH QoE:
  - `FCC-16 = 38.3321`
  - `FCC-18 = 141.2679`
  - `Oboe = 94.5479`
  - `Puffer-21 = 49.4658`
  - `Puffer-22 = 42.5896`
  - `HSR = 146.9135`
- The run finished 10/10 generations. Vertex Pro emitted intermittent `HTTP 429 RESOURCE_EXHAUSTED` responses, but retry logic recovered and the run completed.
- Remote `rclone` backup of the run root reported copy errors for live log files (`full_pipeline.log`, `launcher.log`) because their sizes changed during backup. Final artifacts were synced back locally via `rsync`, and the summary CSV was copied to `experiments/campaign_data/4gplus-to-3g-transfer/r1_vertexpro_results_summary.csv`.

## Next Steps
- Treat this as a useful but not competitive reverse-transfer signal: 4G+ evolution learned a heuristic that transfers above RobustMPC, but not enough to replace direct 3G evolution.
- If reverse transfer remains important for the paper, the fair follow-up is a stronger `pop25` 4G+ run evaluated on 3G. Otherwise, prioritize direct joint-fitness training.
