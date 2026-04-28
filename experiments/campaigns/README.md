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
3. 即使实验代码在 worktree / branch / remote checkout 中隔离运行，`experiments/campaigns/` 和 `experiments/experiments_tracker.md` 也应同步维护在主仓库 checkout，避免系列记录只留在临时分支或远程副本里。
4. 实验执行时优先复用已有 phase 2 baseline，除非 baseline 本身发生变化或缺失。
5. 每一个“有改动的实验尝试”都要记录 `Key Change`，说明这次和 baseline 或同系列其他 run 相比到底改了什么。
6. 实验完成后，再把 best result 和结论回填到这里。

| Series | Goal | Status | Best Result | Tracker |
|--------|------|--------|-------------|---------|
| 3G Baseline Models | 对比 3 个 LLM 模型在 3G+4G+ 表现 | completed | 4G+: ~1031, 3G: ~-122 | [tracker](3g-baseline-models.md) |
| 3G Advanced Architectures Round 1 | 把 Gemini 提议里的 `virtual sensor` 和 `MPC predictor` 各自压成最小可跑 seed family，先验证结构化架构在 3G 上是否比自由逻辑 seed 更有信号 | completed | `virtual_sensor` beat same-provider DeepSeek `quetra` control by +1.9 but stayed below historical `QUETRA pop5`; `rmpc_predictor` grok result completed at 82.3 but is transport-contaminated | [tracker](3g-advanced-architectures-round1.md) |
| 3G Model Refresh Round 1 | 在固定 `QUETRA pop5 mean` 路线上替换新的 `.env` API/model，观察同配置下的 3G 结果变化 | completed | best tested backend is hybgzs `claude-sonnet-4-6-thinking` at 87.6, ahead of historical `QUETRA pop5` 87.0 but below A1 88.9 | [tracker](3g-model-refresh-round1.md) |
| grok2api Connection Close Probe | 验证 grok2api `BrokenPipeError` 是否来自复用 keep-alive 连接，并测试 opt-in `Connection: close` 开关 | completed | one-generation `rmpc_predictor` probe finished with `BrokenPipeError=0` vs keep-alive full run's 107 BrokenPipe retries | [tracker](grok2api-connection-close-probe.md) |
| 3G Seed Impact | 逐 seed 分析 EoH 在 3G 的表现差异 | completed | Quetra seed 87.0 | [tracker](3g-seed-impact.md) |
| 3G Seed Round 2 | 设计更强的 online seed，并筛选是否能超过 QUETRA / A1 baseline | completed | S2=87.2; no new seed beat A1=88.9 | [tracker](3g-seed-round2.md) |
| 3G Improve Round 1 | CVaR fitness + 种群/seed 改进 | completed | D=83.2 (未超 87.0) | [tracker](3g-improve-round1.md) |
| 3G Exploit Round 1 | 围绕 A1=88.9 做局部 exploitation、selection 去噪、early curriculum，测试能否继续突破 3G plateau | completed | F1=88.0; hard_mean=46.70; 未超过 A1=88.9 | [tracker](3g-exploit-round1.md) |
| 3G Hardset Round 2 | large-pop + single-seed + dataset-balanced objective 验证 3G plateau 是否可突破 | completed | A1=88.9, 超过 87.6；A3 gate 未过，不进入 Stage 2 | [tracker](3g-hardset-round2.md) |
| 3G Island Round 1 | 用 5 个 seed 各自独立演化后再汇合，测试岛屿模式能否避免 mixed-seed 早期干扰 | completed | 87.5；未超过 A1=88.9 | [tracker](3g-island-round1.md) |
| 3G Validation Round 1 | held-out validation split 是否能降低 3G 过拟合并超过 88.9 baseline | completed | V1=87.3, V2=87.2；均未超过 A1=88.9 | [tracker](3g-validation-round1.md) |
| 4G Feedback Ablation | 在 ABRBench-4G+ 上做 feedback on/off 对照，判断 evaluator feedback 是否仍有正收益 | completed | on=1005.4, off=988.2, delta=+17.2 | [tracker](4g-feedback-ablation.md) |
