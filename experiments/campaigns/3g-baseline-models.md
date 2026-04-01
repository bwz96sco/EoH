# Series: 3g-baseline-models

> Auto-generated data by `experiments/update_series_tracker.py`.
> Analysis and Next Steps sections are manually maintained.

## Objective
对比 grok-4.20-beta / grok-4.1-expert / grok-4.1-thinking 在 3G+4G+ 上的 EoH 表现

## Baseline Reference
- RobustMPC 78.2 (3G), 975.7 (4G+)

## Experiments

| Label | Config | ABRBench-3G (avg) | vs Baseline | Run ID | Run Root |
|-------|--------|-------------------|-------------|--------|----------|
| grok-4.20-beta | grok-4.20-beta, pop=5, gen=10 | -122.1 | -200.3 | 20260325-234552-abr-rerun | /Users/zhangbowen/Projects/EoH/experiments/results/20260325-234552-abr-rerun |
| grok-4.1-expert | grok-4.1-expert, pop=5, gen=10 | -120.8 | -199.0 | 20260326-145715-grok-4.1-expert | /Users/zhangbowen/Projects/EoH/experiments/results/20260326-145715-grok-4.1-expert |
| grok-4.1-thinking | grok-4.1-thinking, pop=5, gen=10 | -122.1 | -200.3 | 20260326-202134-grok-4.1-thinking | /Users/zhangbowen/Projects/EoH/experiments/results/20260326-202134-grok-4.1-thinking |

## Per-Dataset Breakdown

| Dataset | Baseline (RMPC) | grok-4.20-beta | grok-4.1-expert | grok-4.1-thinking |
|---------|----------------|----------------|-----------------|-------------------|
| FCC-16 | 36.6 | -218.1 | -218.6 | -218.4 |
| FCC-18 | 143.3 | 43.5 | 47.4 | 40.6 |
| Oboe | 96.1 | -54.7 | -53.6 | -55.7 |
| Puffer-21 | 34.1 | -200.7 | -203.4 | -200.0 |
| Puffer-22 | 36.9 | -346.9 | -347.7 | -347.2 |
| HSR | 122.4 | 44.5 | 50.8 | 48.4 |
| Norway3G | -318.1 | -124.7 | -251.9 | -285.5 |
| Lumos4G | 1283.1 | 1354.6 | 1356.2 | 1363.5 |
| Lumos5G | 1696.8 | 1776.5 | 1798.8 | 1784.0 |
| SolisWi-Fi | 589.6 | 597.6 | 620.9 | 630.4 |
| Ghent | 1075.2 | 1054.0 | 1098.4 | 1107.5 |
| Lab | 1527.8 | 1532.3 | 1563.7 | 1564.6 |

## Analysis
- **4G+ 全部成功**：3 个模型的 EoH 均超过 RobustMPC (975.7)，达到 ~1030 水平
- **3G 全部失败**：EoH 在 3G 上 QoE 约 -122，远低于最弱 baseline BB (64.3)
- **模型间差异极小**：3 个模型结果高度一致（3G 差异 < 2, 4G+ 差异 < 5），说明瓶颈不在 LLM 能力
- **根因**：进化收敛到极端保守策略（总是选最低码率以避免 rebuffering），在 3G 训练 trace 上回避了惩罚但在测试时损失巨大

## Next Steps
→ 启动 seed impact study 和 3G improvement 系列实验
