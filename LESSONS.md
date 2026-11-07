# Trenchfloor lessons

Paper trading / research only. No wallet. No real trades. Not financial advice.

Persistent memory. Every agent reads the rules before acting. Tried and rejected strategy variants are not retested.

## Rules

- **2026-11-06T20:29:25.197404-05:00** — skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply
  - Source: Bubble Map Analyst
  - Evidence: SI276 top wallet 4.7407% (7GgLHG2hWqFKqMvfzgG5VeLgE2M4KD2GpveKZ4ZXD5hp)
  - Examples: DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump, 8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump, HMYd9tosnUXuNHmq7pXmoePRVBLBBjA3JBfydq6upump

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
- **2026-11-06T20:39:56.831359-05:00** (Bubble Map Analyst): skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply — SI276 top wallet 4.7407% (7GgLHG2hWqFKqMvfzgG5VeLgE2M4KD2GpveKZ4ZXD5hp)
- **2026-11-06T20:40:07.176550-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176561-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176567-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176571-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176575-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176583-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176588-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176592-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176596-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176600-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176604-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold8 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.176607-05:00** (Backtester): jeff paper loss $-6.3078 on dip_20_40_stop8_tp15_hold8 exit time liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198139-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198149-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198155-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198159-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198164-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198168-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198173-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198178-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198182-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198186-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198191-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198196-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp15_hold16 exit stop liq 83077.49 mcap 915018.0
- **2026-11-06T20:40:07.198202-05:00** (Backtester): jeff paper loss $-3.4958 on dip_20_40_stop8_tp15_hold16 exit time liq 83077.49 mcap 915018.0

## Tried and rejected variants

- `dip_20_40_stop8_tp15_hold8` — **champion** at 2026-11-06T20:40:07.190842-05:00. out-of-sample expectancy $0.4082 beat the previous champion
- `dip_20_40_stop8_tp15_hold16` — **rejected** at 2026-11-06T20:40:07.216295-05:00. out-of-sample expectancy $-1.7793 over 9 trades

## Rejected mints

- `CBUCKS` `DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump` — holder above 3.5% (2026-11-06T20:29:25.197557-05:00)
- `GLITCH` `8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump` — holder above 3.5% (2026-11-06T20:29:25.198061-05:00)
- `SI276` `HMYd9tosnUXuNHmq7pXmoePRVBLBBjA3JBfydq6upump` — holder above 3.5% (2026-11-06T20:39:56.831802-05:00)
