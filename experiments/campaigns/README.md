# Experiment Campaigns

> 所有 ABR 实验系列的索引。每个系列围绕一个研究目的，包含若干次实验。
>
> 具体实验的 CSV 和 run_report 见各 run 的 `analysis/` 目录。
>
> 全局实验总记录见 [experiments_tracker.md](../experiments_tracker.md)。

## Campaign Contract

每一个 campaign 都表示“围绕同一个研究目标的一系列实验”，不是单个 run。

每一轮新的 ABR 实验系列，在真正启动 run 之前，都应该先在这里登记。

至少要记录清楚：

- 研究目的：这轮实验想回答什么问题
- 变化因素：这轮只改变什么
- 固定因素：哪些设置保持不变
- 计划执行：打算跑哪些 run / matrix
- 当前状态：planned / running / completed / blocked

推荐做法：

1. 先在这里新增一行系列索引。
2. 再创建对应的 `experiments/campaigns/<series-name>.md`，写明 objective、baseline、metric、planned runs、analysis、next steps。
3. 实验执行时优先复用已有 phase 2 baseline，除非 baseline 本身发生变化或缺失。
4. 实验完成后，再把 best result 和结论回填到这里。

| Series | Goal | Status | Best Result | Tracker |
|--------|------|--------|-------------|---------|
| 3G Baseline Models | 对比 3 个 LLM 模型在 3G+4G+ 表现 | completed | 4G+: ~1031, 3G: ~-122 | [tracker](3g-baseline-models.md) |
| 3G Seed Impact | 逐 seed 分析 EoH 在 3G 的表现差异 | completed | Quetra seed 87.0 | [tracker](3g-seed-impact.md) |
| 3G Improve Round 1 | CVaR fitness + 种群/seed 改进 | completed | D=83.2 (未超 87.0) | [tracker](3g-improve-round1.md) |
