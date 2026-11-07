# Iterative backtest

**Paper trading / research only. No wallet. No real trades. Not financial advice.**

Backtester only. Live entry gates, `config.json`, and forward paper entries are unchanged.

Train is the earlier portion of each pool's hourly bars. Out of sample is the latest oos_fraction of those bars. A rule is learned only on train trades and kept only when held-out expectancy does not fall and held-out trade count stays above the floor.

Strategy `dip_20_40_stop8_tp15_hold8`. Stopped because: no validated rules.

## Data notes

- Indexed 14 stored coins from research.json and lessons pools.
- ZEC: holder read incomplete: holder signature list was empty or unreadable; wallet age is unknown
- PUMP: holder read incomplete: holder signature list was empty or unreadable; wallet age is unknown
- ANSEM: holder read incomplete: holder signature list was empty or unreadable; wallet age is unknown
- PENGU: holder read incomplete: holder signature list was empty or unreadable; wallet age is unknown
- Research uses every train trade, wins and losses. The held-out split is not read until a rule has already been called a good predictor.
- Each coin's latest oos_fraction of hourly bars is the held-out split, the same cut the existing dip simulator uses. Rules are never relaxed to chase that split.
- Liquidity drop along the path is measured only from a real liquidity_bars series. A single liquidity or market-cap snapshot is not an entry-time drop.
- Bundle, sniper, fresh-wallet, wash, holder, and dev readings become entry rules only when they were knowable at entry. A later chain snapshot is reported and is not promoted.
- Missing readings stay missing. Trades without a reading are not treated as clean and are not treated as flagged.

## Final rules

No rule was kept.

## Rejected rules

- `bundle_supply_pct` (research, inconclusive): bundled or linked wallet supply %: no train trade fell on the flagged side of > 15. Measured values ranged from 0 to 0 (median 0, n=22). With-flag n=0, without-flag n=22, unmeasured excluded 22. Verdict: inconclusive. This reading is a later snapshot, not the book at the historical entry, so it cannot become an entry rule.
- `pair_age_hours` (research, inconclusive): pair age at entry in hours: no train trade fell on the flagged side of < 0.25. Measured values ranged from 1.18556 to 6737.12 (median 190.018, n=44). With-flag n=0, without-flag n=44, unmeasured excluded 0. Verdict: inconclusive.
- `entry_frac_of_ath` (research, inconclusive): entry price as a fraction of the window high (mcap ratio if supply is unchanged): train trades > 0.232238 won 0.2632 with expectancy -2.8856 (n=38); trades on the other side won 0.3333 with expectancy -0.1563 (n=6). Measured values ranged from 0.201068 to 0.397047 (median 0.269709, n=44). Unmeasured trades excluded from both sides: 0. One-sided Welch p≈0.2158 (normal approximation). Winners the rule would also remove on the train split: 10 ($104.696). Losers removed: 28. Verdict: inconclusive.
- `snapshot_liq_to_mcap` (research, inconclusive): snapshot liquidity divided by snapshot market cap: train trades < 0.083119 won 0.2188 with expectancy -3.2208 (n=32); trades on the other side won 0.4167 with expectancy -0.6272 (n=12). Measured values ranged from 0.020233 to 0.086874 (median 0.079364, n=44). Unmeasured trades excluded from both sides: 0. One-sided Welch p≈0.2348 (normal approximation). Winners the rule would also remove on the train split: 7 ($59.307). Losers removed: 25. Verdict: inconclusive. This reading is a later snapshot, not the book at the historical entry, so it cannot become an entry rule.
- `volume_top_share` (research, inconclusive): largest pre-entry bar's share of the prior 12 bars' volume: train trades > 0.5 won 0.5 with expectancy 5.0456 (n=2); trades on the other side won 0.2683 with expectancy -2.6995 (n=41). Measured values ranged from 0.122848 to 0.54513 (median 0.213839, n=43). Unmeasured trades excluded from both sides: 1. One-sided Welch p≈0.8469 (normal approximation). Winners the rule would also remove on the train split: 1 ($12.4975). Losers removed: 1. Verdict: inconclusive.

## Before vs after

- Train trades 44 -> 44, expectancy -2.5135 -> -2.5135, PnL -110.5920 -> -110.5920.
- Out-of-sample trades 12 -> 12, expectancy -3.9877 -> -3.9877, PnL -47.8524 -> -47.8524.

## Iterations

### Train

| Iter | Rules added | Trades | Win rate | Avg win | Avg loss | Expectancy | PnL | Max DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | — | 44 | 27.27% | 10.1495 | -7.2621 | -2.5135 | -110.5920 | 168.7651 |
| 1 | — | 44 | 27.27% | 10.1495 | -7.2621 | -2.5135 | -110.5920 | 168.7651 |

### Out of sample

| Iter | Rules added | Trades | Win rate | Avg win | Avg loss | Expectancy | PnL | Max DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | — | 12 | 16.67% | 12.4975 | -7.2847 | -3.9877 | -47.8524 | 48.9614 |
| 1 | — | 12 | 16.67% | 12.4975 | -7.2847 | -3.9877 | -47.8524 | 48.9614 |

## Research notes

### Iteration 1 — bundle_supply_pct — inconclusive

bundled or linked wallet supply %: no train trade fell on the flagged side of > 15. Measured values ranged from 0 to 0 (median 0, n=22). With-flag n=0, without-flag n=22, unmeasured excluded 22. Verdict: inconclusive. This reading is a later snapshot, not the book at the historical entry, so it cannot become an entry rule.

### Iteration 1 — pair_age_hours — inconclusive

pair age at entry in hours: no train trade fell on the flagged side of < 0.25. Measured values ranged from 1.18556 to 6737.12 (median 190.018, n=44). With-flag n=0, without-flag n=44, unmeasured excluded 0. Verdict: inconclusive.

### Iteration 1 — entry_frac_of_ath — inconclusive

entry price as a fraction of the window high (mcap ratio if supply is unchanged): train trades > 0.232238 won 0.2632 with expectancy -2.8856 (n=38); trades on the other side won 0.3333 with expectancy -0.1563 (n=6). Measured values ranged from 0.201068 to 0.397047 (median 0.269709, n=44). Unmeasured trades excluded from both sides: 0. One-sided Welch p≈0.2158 (normal approximation). Winners the rule would also remove on the train split: 10 ($104.696). Losers removed: 28. Verdict: inconclusive.

### Iteration 1 — snapshot_liq_to_mcap — inconclusive

snapshot liquidity divided by snapshot market cap: train trades < 0.083119 won 0.2188 with expectancy -3.2208 (n=32); trades on the other side won 0.4167 with expectancy -0.6272 (n=12). Measured values ranged from 0.020233 to 0.086874 (median 0.079364, n=44). Unmeasured trades excluded from both sides: 0. One-sided Welch p≈0.2348 (normal approximation). Winners the rule would also remove on the train split: 7 ($59.307). Losers removed: 25. Verdict: inconclusive. This reading is a later snapshot, not the book at the historical entry, so it cannot become an entry rule.

### Iteration 1 — volume_top_share — inconclusive

largest pre-entry bar's share of the prior 12 bars' volume: train trades > 0.5 won 0.5 with expectancy 5.0456 (n=2); trades on the other side won 0.2683 with expectancy -2.6995 (n=41). Measured values ranged from 0.122848 to 0.54513 (median 0.213839, n=43). Unmeasured trades excluded from both sides: 1. One-sided Welch p≈0.8469 (normal approximation). Winners the rule would also remove on the train split: 1 ($12.4975). Losers removed: 1. Verdict: inconclusive.

## Coverage

- `bundle_supply_pct`: 25 measured trades, timings later_snapshot
- `top10_ex_pool_burn_pct`: 0 measured trades, timings unmeasured
- `fresh_wallet_count`: 26 measured trades, timings later_snapshot
- `fresh_cluster_pct`: 26 measured trades, timings later_snapshot
- `wash_roundtrip_fraction`: 1 measured trades, timings later_snapshot
- `dev_hold_pct`: 0 measured trades, timings unmeasured
- `dev_sold_fraction`: 0 measured trades, timings unmeasured
- `dev_sold_flag`: 0 measured trades, timings unmeasured
- `pair_age_hours`: 56 measured trades, timings at_entry
- `entry_frac_of_ath`: 56 measured trades, timings at_entry
- `volume_top_share`: 55 measured trades, timings at_entry
- `liquidity_drop_pct`: 0 measured trades, timings unmeasured
- `snapshot_liq_to_mcap`: 56 measured trades, timings later_snapshot
- `snapshot_holder_pct_sum`: 26 measured trades, timings later_snapshot

## Skipped coins

- HODL: fewer than 30 hourly bars

Simulated fills only. This report does not place orders.
