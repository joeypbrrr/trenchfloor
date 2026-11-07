# Trenchfloor lessons

Paper trading / research only. No wallet. No real trades. Not financial advice.

Persistent memory. Every agent reads the rules before acting. Tried and rejected strategy variants are not retested.

## Rules

- **2026-11-06T20:29:25.197404-05:00** — skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply
  - Source: Bubble Map Analyst
  - Evidence: FLOAT top wallet 5.4635% (EEABWyb6xFFDq6Vc7ZprJynTnv1RzCKVk19uoPnHT52G)
  - Examples: DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump, 8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump, HMYd9tosnUXuNHmq7pXmoePRVBLBBjA3JBfydq6upump, 8THZ69JP2ErZuHVj4G5rcwkFfsQafp5mQsaoQReApump, BWJfBNeXpapG7uoqByp5KSwWgCQba8QcDmA2DQiEpump, Bv1a7cEj5aRnJQhMw4kRQqAFesMSd5LwcDnUzq52BMmr

- **2026-11-06T20:29:31.564242-05:00** — skip tokens whose liquidity is under 5% of market cap after a losing paper trade with that thin book
  - Source: Risk Manager
  - Evidence: COGE lost $-10.002 with liquidity/mcap 0.027
  - Examples: 8UQdy5sHMVWUWSHeA5B3ZuuAVNumjSLPXdf19MXcpump

## Observations

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
- **2026-11-06T23:09:24.697605-05:00** (Bubble Map Analyst): skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply — FLOAT top wallet 5.4635% (EEABWyb6xFFDq6Vc7ZprJynTnv1RzCKVk19uoPnHT52G)
- **2026-11-06T23:09:36.606032-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold8 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.606044-05:00** (Backtester): jeff paper loss $-1.3563 on dip_20_40_stop12_tp25_hold8 exit time liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.606051-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold8 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.606055-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold8 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.606060-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold8 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.606064-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold8 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.606068-05:00** (Backtester): jeff paper loss $-6.3078 on dip_20_40_stop12_tp25_hold8 exit time liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663826-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663836-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663841-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663844-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663848-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663852-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663856-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-06T23:09:36.663859-05:00** (Backtester): jeff paper loss $-13.9149 on dip_20_40_stop12_tp25_hold16 exit stop liq 85094.81 mcap 962801.0
- **2026-11-07T07:42:25.620872-05:00** (Backtester): HODL post-loss review. Improve entries: do not add a filter from HODL; these checks failed after retry: fresh_wallet_cluster (failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion":

## Post-loss reviews

- **2026-11-07T12:42:25.619991+00:00** HODL: POST-LOSS REVIEW / HODL / $-21.81 / exit stop. Contributing factors: none. Every check is listed with its result. Checks: - holder_distribution: CLEAN top-1 0.12%; top-10 1.23%; excluding pool and burn; entry snapshot top non-LP holder 0.15% - fresh_wallet_cluster: FAILED failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge… - linked_wallet_cluster: FAILED failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge… - bundle_sniper_share: FAILED failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge… - dev_creator: CLEAN creator wallets 2QRJuvWpQZa9twTahzCX4htcKyg9cdqCvUey3xkaGcV8, 9NkVW544fKy2kkU5ZxJFa1xy6C7LssPKZAW5XWbK5XG5; holding not in the top holder sample; 0 creator sell(s) totaling 0 tokens in 5 sampled pool fills - liquidity: CLEAN liquidity $164,650.47 at entry → $142,856.56 at exit (-13.2%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked - volume_profile: CLEAN volume $2,171,989.76 at entry → $2,752,271.10 at exit (26.7%). wash no wash round-trip in 5 sampled pool fills - price_mcap_path: CLEAN price 0.003965 → 0.002962 (-25.3%) over 338.8 minutes; entry was 86.1% of the recorded window ATH; market cap at review $2,949,640.00; recorded stop 12% - on_chain_anomalies: CLEAN mint authority is not active; freeze authority is not active; no extra on-chain warning Recorded exit price 0.002962. Improve entries: do not add a filter from HODL; these checks failed after retry: fresh_wallet_cluster (failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge…); linked_wallet_cluster (failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missin…


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
- `dip_20_40_stop12_tp25_hold8` — **rejected** at 2026-11-06T23:09:36.636528-05:00. out-of-sample expectancy $-0.3793 over 5 trades
- `dip_20_40_stop12_tp25_hold16` — **rejected** at 2026-11-06T23:09:36.696886-05:00. out-of-sample expectancy $-3.5759 over 5 trades

## Rejected mints

- `CBUCKS` `DtcicPCKTKeAh7TDEzTym3hXeoHAoMiBdYJhMYxZpump` — holder above 3.5% (2026-11-06T20:29:25.197557-05:00)
- `GLITCH` `8Xg89xT8Ve34sKiYqYuMs46mycREsCA2F362UscRpump` — holder above 3.5% (2026-11-06T20:29:25.198061-05:00)
- `SI276` `HMYd9tosnUXuNHmq7pXmoePRVBLBBjA3JBfydq6upump` — holder above 3.5% (2026-11-06T20:39:56.831802-05:00)
- `NETWORK` `8THZ69JP2ErZuHVj4G5rcwkFfsQafp5mQsaoQReApump` — holder above 3.5% (2026-11-06T21:12:20.169472-05:00)
- `Leonida` `BWJfBNeXpapG7uoqByp5KSwWgCQba8QcDmA2DQiEpump` — holder above 3.5% (2026-11-06T21:21:39.521179-05:00)
- `FLOAT` `Bv1a7cEj5aRnJQhMw4kRQqAFesMSd5LwcDnUzq52BMmr` — holder above 3.5% (2026-11-06T23:09:24.698744-05:00)
