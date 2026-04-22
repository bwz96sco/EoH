# Series: 4G Feedback Ablation

## Objective
在 `ABRBench-4G+` 上隔离测试 evaluator feedback 的收益，回答“当前已提交版本里，保留 `m1` 的 evaluation feedback 是否能稳定提升 4G 结果”。

## Baseline Reference
- Internal control: committed `HEAD` with feedback enabled in `get_prompt_m1`
- Comparison metric: `ABRBench-4G+ (avg)` from `analysis/results_summary.csv`

## Fixed Factors
- Evolution target: `ABRBench-4G+`
- Eval scope: default 4G+ suite
- Seed: `QUETRA`
- Fitness: `mean`
- Budget: `EC_POP_SIZE=5`, `EC_N_POP=1`, `EXP_N_PROC=1`
- Model/API config: inherit current committed `.env`

## Experiments

| Label | Key Change | 4G+ QoE | Delta vs Off | Run ID | Checkout |
|-------|------------|---------|--------------|--------|----------|
| F4G-On | committed `HEAD`, keep `m1` feedback | 1005.3625 | +17.2079 | `20260413-193844-4g-feedback-on-small` | `experiment/4g-feedback-on` |
| F4G-Off | disable evaluator feedback in `get_prompt_m1` only | 988.1546 | baseline | `20260414-084355-4g-feedback-off-small-r3` | `experiment/4g-feedback-off` |

## Per-Dataset Breakdown

| Dataset | F4G-On | F4G-Off | Delta |
|---------|--------|---------|-------|
| Norway3G | -264.8783 | -280.9956 | +16.1173 |
| Lumos4G | 1345.0007 | 1326.6809 | +18.3198 |
| Lumos5G | 1779.6081 | 1764.2297 | +15.3784 |
| SolisWi-Fi | 597.3042 | 586.5714 | +10.7328 |
| Ghent | 1052.7303 | 1063.1217 | -10.3914 |
| Lab | 1522.4098 | 1469.3197 | +53.0901 |

## Analysis

- 在这组小预算 4G ablation 里，保留 `m1` evaluator feedback 带来稳定正收益：`1005.3625 - 988.1546 = +17.2079`。
- 6 个 4G+ 子数据集里有 5 个受益，只有 `Ghent` 单点回落；最大收益来自 `Lab`（`+53.0901`）。
- 过程层面，`feedback-off` 的 `m1` 阶段最优 offspring objective 也略差于 `feedback-on`，方向与最终 eval 一致。
- 结论是：当前 committed `HEAD` 上，`m1` feedback 对 4G 不是主效应，但属于真实且可测的增益项，不建议移除。

## Next Steps

1. 保留当前 `m1` feedback 设计，不把它当成 4G 主优化方向。
2. 将后续结构性探索转向更大的搜索组织方式，例如岛屿模式。
3. 若要进一步验证稳健性，再补一个第二随机种子/重复对照。
