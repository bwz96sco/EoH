# Experiments Tracker

> Global experiment log. Updated when experiment status changes. Git tracked.
> See [campaigns/README.md](campaigns/README.md) for research series details.

| Run ID                                                       | Campaign           | Target                    | Status    | Started    | Completed  | Key Result            | Notes                                                    |
|--------------------------------------------------------------|--------------------|---------------------------|-----------|------------|------------|-----------------------|----------------------------------------------------------|
| 20260402-3g-hardset-round2-a2-r1                             | 3g-hardset-round2  | ABRBench-3G               | running   | 2026-04-02 |            |                       | quetra, pop=5, dataset_balanced_mean                     |
| 20260402-3g-hardset-round2-a1-r1                             | 3g-hardset-round2  | ABRBench-3G               | running   | 2026-04-02 |            |                       | quetra, pop=25, mean                                     |
| 20260401-132132-mixed-pop25-exp12                            | 3g-hardset-round2  | ABRBench-3G               | completed | 2026-04-01 | 2026-04-01 | 3G:87.6, 4G+:1562.2   | mixed seeds, pop=25, 12 operators                        |
| 20260331-121909-exp-f-cvar-adaptive-seed                     | 3g-improve-round1  | ABRBench-3G               | completed | 2026-03-31 | 2026-03-31 | 3G:54.7               | CVaR-25, pop=6, adaptive_regime seed                     |
| 20260331-121909-exp-d-cvar-large-pop                         | 3g-improve-round1  | ABRBench-3G               | completed | 2026-03-31 | 2026-03-31 | 3G:83.2               | CVaR-25, pop=15, 6 seeds incl evolved_best               |
| 20260331-085334-3g-improve-pop-diversity-r2                  | 3g-improve-round1  | ABRBench-3G               | completed | 2026-03-31 | 2026-03-31 | 3G:85.5               | NSGA-II crowding, behavior descriptors, pop=5, quetra    |
| 20260331-085318-3g-improve-fitness-constraint-r2             | 3g-improve-round1  | ABRBench-3G               | completed | 2026-03-31 | 2026-03-31 | 3G:86.0               | mean_util fitness, anti-conservatism, pop=5, quetra      |
| 20260331-085304-3g-improve-enhanced-feedback-r2              | 3g-improve-round1  | ABRBench-3G               | completed | 2026-03-31 | 2026-03-31 | 3G:86.5               | enhanced feedback, all-operator injection, pop=5, quetra |
| 20260330-140417-seed-impact-pop5-seed-abrbench-3g-robust_mpc | 3g-seed-impact     | ABRBench-3G               | completed | 2026-03-30 | 2026-03-30 | 3G:84.8               | robust_mpc seed, pop=5                                   |
| 20260330-140417-seed-impact-pop5-seed-abrbench-3g-rate_based | 3g-seed-impact     | ABRBench-3G               | completed | 2026-03-30 | 2026-03-30 | 3G:86.2               | rate_based seed, pop=5                                   |
| 20260330-140417-seed-impact-pop5-seed-abrbench-3g-quetra     | 3g-seed-impact     | ABRBench-3G               | completed | 2026-03-30 | 2026-03-30 | 3G:87.0               | quetra seed, pop=5                                       |
| 20260330-140417-seed-impact-pop5-seed-abrbench-3g-bola       | 3g-seed-impact     | ABRBench-3G               | completed | 2026-03-30 | 2026-03-30 | 3G:85.0               | bola seed, pop=5                                         |
| 20260330-140417-seed-impact-pop5-seed-abrbench-3g-bb         | 3g-seed-impact     | ABRBench-3G               | completed | 2026-03-30 | 2026-03-30 | 3G:85.9               | bb seed, pop=5                                           |
| 20260326-202134-grok-4.1-thinking                            | 3g-baseline-models | ABRBench-3G, ABRBench-4G+ | completed | 2026-03-26 | 2026-03-26 | 3G:-122.1, 4G+:1027.4 | grok-4.1-thinking                                        |
| 20260326-145715-grok-4.1-expert                              | 3g-baseline-models | ABRBench-3G, ABRBench-4G+ | completed | 2026-03-26 | 2026-03-26 | 3G:-120.8, 4G+:1031.0 | grok-4.1-expert                                          |
| 20260325-234552-abr-rerun                                    | 3g-baseline-models | ABRBench-3G, ABRBench-4G+ | completed | 2026-03-25 | 2026-03-25 | 3G:-122.1, 4G+:1031.7 | grok-4.20-beta                                           |
