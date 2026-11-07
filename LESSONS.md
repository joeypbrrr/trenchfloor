# Trenchfloor lessons

Paper trading / research only. No wallet. No real trades. Not financial advice.

Persistent memory. Every agent reads the rules before acting. Tried and rejected strategy variants are not retested.

## Rules

- **2026-11-06T20:29:25.197404-05:00** — skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply
  - Source: Bubble Map Analyst
  - Evidence: GLITCH top wallet 3.5852% (8DJHyX9scPUAdR3J7HRULqEiTNR8LHGkCgwnGopeEAq1)
  - Examples: DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump, 8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump

- **2026-11-06T20:29:31.564242-05:00** — skip tokens whose liquidity is under 5% of market cap after a losing paper trade with that thin book
  - Source: Risk Manager
  - Evidence: COGE lost $-10.002 with liquidity/mcap 0.027
  - Examples: 8UQdy5sHMVWUWSHeA5B3ZuuAVNumjSLPXdf19MXcpump

## Observations

- **2026-11-06T20:29:25.197417-05:00** (Bubble Map Analyst): skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply — CBUCKS top wallet 14.5407% (BwSwtsPphxFDckVvEaFcwEzG2SAxTprN19fswwe5YZbK)
- **2026-11-06T20:29:25.197943-05:00** (Bubble Map Analyst): skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply — GLITCH top wallet 3.5852% (8DJHyX9scPUAdR3J7HRULqEiTNR8LHGkCgwnGopeEAq1)
- **2026-11-06T20:29:31.564225-05:00** (Backtester): COGE paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 264988.6 mcap 9819816.0
- **2026-11-06T20:29:31.564248-05:00** (Risk Manager): skip tokens whose liquidity is under 5% of market cap after a losing paper trade with that thin book — COGE lost $-10.002 with liquidity/mcap 0.027
- **2026-11-06T20:29:31.566956-05:00** (Backtester): COGE paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 264988.6 mcap 9819816.0

## Tried and rejected variants

- `dip_20_40_stop8_tp15_hold8` — **deferred** at 2026-11-06T20:29:31.565449-05:00. only 0 out-of-sample paper trades (need 5); not rejected
- `dip_20_40_stop8_tp15_hold16` — **deferred** at 2026-11-06T20:29:31.567515-05:00. only 0 out-of-sample paper trades (need 5); not rejected

## Rejected mints

- `CBUCKS` `DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump` — holder above 3.5% (2026-11-06T20:29:25.197557-05:00)
- `GLITCH` `8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump` — holder above 3.5% (2026-11-06T20:29:25.198061-05:00)
