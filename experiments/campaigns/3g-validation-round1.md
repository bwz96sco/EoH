# Series: 3g-validation-round1

> Auto-generated data by `experiments/update_series_tracker.py`.
> Analysis and Next Steps sections are manually maintained.

## Objective
Test whether a held-out validation split during 3G evolution can reduce overfitting and beat the current best internal 3G baseline.

## Baseline Reference
- 88.8697 (20260402-3g-hardset-round2-a1-r1, QUETRA + pop25 + mean)

## Experiments

| Label | Key Change | Config | ABRBench-3G (avg) | vs Baseline | Run ID | Run Root |
|-------|------------|--------|-------------------|-------------|--------|----------|
| V1 train_validation_mean | Replace train-only mean objective with 0.5*(train_inner_qoe + validation_qoe) over a deterministic 80/20 split of 3G TRAIN_TRACES. | grok-4.20-beta, pop=25, gen=10 | 87.3 | -1.6 | 20260406-3g-validation-round1-v1-r1 | /Users/zhangbowen/Library/CloudStorage/OneDrive-Personal/ExperimentsRecord/EoH/experiments/results/20260406-3g-validation-round1-v1-r1 |
| V2 train_validation_min | Replace train-only mean objective with min(train_inner_qoe, validation_qoe) over the same deterministic 80/20 validation split. | grok-4.20-beta, pop=25, gen=10 | 87.2 | -1.7 | 20260406-3g-validation-round1-v2-r1 | /Users/zhangbowen/Library/CloudStorage/OneDrive-Personal/ExperimentsRecord/EoH/experiments/results/20260406-3g-validation-round1-v2-r1 |

## Per-Dataset Breakdown

| Dataset | Baseline (RMPC) | V1 train_validation_ | V2 train_validation_ |
|---------|----------------|----------------------|----------------------|
| FCC-16 | 36.6 | 39.2 | 38.7 |
| FCC-18 | 143.3 | 145.5 | 142.8 |
| Oboe | 96.1 | 98.9 | 98.2 |
| Puffer-21 | 34.1 | 53.4 | 54.7 |
| Puffer-22 | 36.9 | 46.3 | 44.1 |
| HSR | 122.4 | 140.4 | 144.6 |

## Analysis
- 两条 screening run 都完成并产出了 `results_summary.csv` 与 `run_report.md`。
- `V1 = train_validation_mean` 的主指标为 `87.3073`，比当前 best baseline `88.8697` 低 `1.5624`。
- `V2 = train_validation_min` 的主指标为 `87.1743`，比当前 best baseline 低 `1.6954`。
- hard-dataset 平均也没有超过 baseline：
  - baseline `A1 hard_mean = 46.4957`
  - `V1 hard_mean = 46.3294`
  - `V2 hard_mean = 45.8312`
- `V1` 在 `FCC-16` 和 `Puffer-22` 上略优于 baseline，但 `Oboe`、`Puffer-21`、`HSR` 回退。
- `V2` 把 `HSR` 拉回一些，但 `FCC-18` 和 `Puffer-22` 更差。
- 这轮的证据不支持把 held-out validation objective 作为新的 3G 主线。它更像是带来了一点 regularization，但牺牲了 overall 3G ceiling。

## Next Steps
- 不进入 repeats；这轮应作为 negative result campaign 收束。
- 继续把 `20260402-3g-hardset-round2-a1-r1` 作为当前 3G 主线 baseline。
- 如果后续还要继续做 objective 设计，优先尝试更窄的 hard-dataset shaping，而不是直接使用 train/validation blended objective。
- 如果再做 validation 相关实验，应优先验证更轻量的 selection gate，而不是让 validation 直接参与主 fitness。
