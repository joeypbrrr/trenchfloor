# Trenchfloor lessons

Paper trading / research only. No wallet. No real trades. Not financial advice.

Persistent memory. Every agent reads the rules before acting. Tried and rejected strategy variants are not retested.

## Rules

- **2026-11-06T20:29:25.197404-05:00** — skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply
  - Source: Bubble Map Analyst
  - Evidence: Leonida top wallet 4.3107% (FodHiggUGYku3MVHv6k14trHYk2V6nFi6qdHmcsKaQat)
  - Examples: DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump, 8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump, HMYd9tosnUXuNHmq7pXmoePRVBLBBjA3JBfydq6upump, 8THZ69JP2ErZuHVj4G5rcwkFfsQafp5mQsaoQReApump, BWJfBNeXpapG7uoqByp5KSwWgCQba8QcDmA2DQiEpump

- **2026-11-06T20:29:31.564242-05:00** — skip tokens whose liquidity is under 5% of market cap after a losing paper trade with that thin book
  - Source: Risk Manager
  - Evidence: COGE lost $-10.002 with liquidity/mcap 0.027
  - Examples: 8UQdy5sHMVWUWSHeA5B3ZuuAVNumjSLPXdf19MXcpump

## Observations

- **2026-11-06T21:12:30.706750-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold8 exit stop liq 85693.47 mcap 971199.0
- **2026-11-06T21:12:30.706755-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold8 exit stop liq 85693.47 mcap 971199.0
- **2026-11-06T21:12:30.706760-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold8 exit stop liq 85693.47 mcap 971199.0
- **2026-11-06T21:12:30.706765-05:00** (Backtester): jeff paper loss $-6.3078 on dip_20_40_stop8_tp25_hold8 exit time liq 85693.47 mcap 971199.0
- **2026-11-06T21:21:39.520720-05:00** (Bubble Map Analyst): skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply — Leonida top wallet 4.3107% (FodHiggUGYku3MVHv6k14trHYk2V6nFi6qdHmcsKaQat)
- **2026-11-06T21:21:50.072434-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072458-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072466-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072473-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072480-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072487-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072494-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072511-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072518-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072526-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072533-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.072539-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold16 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.170993-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171005-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171012-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171019-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171026-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171032-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171042-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171048-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171054-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171060-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171066-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:21:50.171072-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp25_hold24 exit stop liq 86674.09 mcap 992799.0
- **2026-11-06T21:40:03.002511-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold8 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.002527-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold8 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.002543-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold8 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.002548-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold8 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.002553-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold8 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.002558-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold8 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.002565-05:00** (Backtester): jeff paper loss $-1.9031 on dip_20_40_stop8_tp40_hold8 exit time liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.002570-05:00** (Backtester): jeff paper loss $-6.3078 on dip_20_40_stop8_tp40_hold8 exit time liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056019-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056031-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056037-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056041-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056046-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056051-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056055-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056060-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:40:03.056064-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold16 exit stop liq 86458.87 mcap 988397.0
- **2026-11-06T21:45:20.846250-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846274-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846284-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846291-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846296-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846301-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846306-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846311-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.846316-05:00** (Backtester): jeff paper loss $-10.002 on dip_20_40_stop8_tp40_hold24 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923847-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold8 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923860-05:00** (Backtester): jeff paper loss $-1.3563 on dip_20_40_stop12_tp15_hold8 exit time liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923866-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold8 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923871-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold8 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923875-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold8 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923878-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold8 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923883-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold8 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923887-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold8 exit stop liq 87155.25 mcap 1005599.0
- **2026-11-06T21:45:20.923891-05:00** (Backtester): jeff paper loss $-6.3078 on dip_20_40_stop12_tp15_hold8 exit time liq 87155.25 mcap 1005599.0
- **2026-11-06T22:19:53.920645-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:53.920677-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:53.920683-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:53.920687-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:53.920704-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:53.920717-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:53.920721-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:53.920725-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold16 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017381-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017393-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017399-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017415-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017421-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017425-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017430-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0
- **2026-11-06T22:19:54.017433-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp15_hold24 exit stop liq 86690.11 mcap 997963.0

## Tried and rejected variants

- `dip_20_40_stop8_tp15_hold8` — **champion** at 2026-11-06T20:40:07.190842-05:00. out-of-sample expectancy $0.4082 beat the previous champion
- `dip_20_40_stop8_tp15_hold16` — **rejected** at 2026-11-06T20:40:07.216295-05:00. out-of-sample expectancy $-1.7793 over 9 trades
- `dip_20_40_stop8_tp15_hold24` — **rejected** at 2026-11-06T21:12:30.694496-05:00. out-of-sample expectancy $-2.9165 over 8 trades
- `dip_20_40_stop8_tp25_hold8` — **rejected** at 2026-11-06T21:12:30.749213-05:00. out-of-sample expectancy $-0.2509 over 7 trades
- `dip_20_40_stop8_tp25_hold16` — **rejected** at 2026-11-06T21:21:50.142866-05:00. out-of-sample expectancy $-3.2919 over 7 trades
- `dip_20_40_stop8_tp25_hold24` — **rejected** at 2026-11-06T21:21:50.241672-05:00. out-of-sample expectancy $-3.2919 over 7 trades
- `dip_20_40_stop8_tp40_hold8` — **rejected** at 2026-11-06T21:40:03.039550-05:00. out-of-sample expectancy $-0.0333 over 6 trades
- `dip_20_40_stop8_tp40_hold16` — **rejected** at 2026-11-06T21:40:03.089745-05:00. out-of-sample expectancy $-7.638 over 6 trades
- `dip_20_40_stop8_tp40_hold24` — **rejected** at 2026-11-06T21:45:20.896829-05:00. out-of-sample expectancy $-6.9554 over 6 trades
- `dip_20_40_stop12_tp15_hold8` — **tried** at 2026-11-06T21:45:20.982637-05:00. out-of-sample expectancy $0.1365 projects $9.5/mo at $100 tickets and did not beat the champion
- `dip_20_40_stop12_tp15_hold16` — **rejected** at 2026-11-06T22:19:53.987458-05:00. out-of-sample expectancy $-0.7087 over 6 trades
- `dip_20_40_stop12_tp15_hold24` — **rejected** at 2026-11-06T22:19:54.073183-05:00. out-of-sample expectancy $-0.7087 over 6 trades

## Rejected mints

- `CBUCKS` `DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump` — holder above 3.5% (2026-11-06T20:29:25.197557-05:00)
- `GLITCH` `8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump` — holder above 3.5% (2026-11-06T20:29:25.198061-05:00)
- `SI276` `HMYd9tosnUXuNHmq7pXmoePRVBLBBjA3JBfydq6upump` — holder above 3.5% (2026-11-06T20:39:56.831802-05:00)
- `NETWORK` `8THZ69JP2ErZuHVj4G5rcwkFfsQafp5mQsaoQReApump` — holder above 3.5% (2026-11-06T21:12:20.169472-05:00)
- `Leonida` `BWJfBNeXpapG7uoqByp5KSwWgCQba8QcDmA2DQiEpump` — holder above 3.5% (2026-11-06T21:21:39.521179-05:00)
