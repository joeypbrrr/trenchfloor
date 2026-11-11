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
- **2026-11-07T10:20:59.979769-05:00** (System): Loop error: The read operation timed out
- **2026-11-07T10:21:17.429679-05:00** (Backtester): GLITCH post-loss review. Improve entries: no red flag was measured on GLITCH. price 0.002865 → 0.002288 (-20.1%) over 375.4 minutes; entry was 55.4% of the recorded window ATH; market cap at review $2,119,417.00; recorded stop 12%. Holder, cluster, bundle, creator, liquidity, volume, and authority checks were clean. Do not add an entry filter from this close.
- **2026-11-07T17:49:53.894350-05:00** (Backtester): GATO post-loss review. Improve entries: GATO showed 3 fresh wallets in 5 sampled top holders holding 5.87% combined (block at 3 wallets, or 2+ wallets at 8%). This does not change entry gates or config thresholds.
- **2026-11-08T13:30:35.126983-05:00** (Backtester): MAGGIE post-loss review. Improve entries: MAGGIE showed liquidity $78,961.48 at entry → $56,755.74 at exit (-28.1%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked. This does not change entry gates or config thresholds.
- **2026-11-08T18:38:59.701189-05:00** (System): Loop error: The read operation timed out
- **2026-11-11T11:49:27.825655-05:00** (System): Loop error: The read operation timed out

## Post-loss reviews

- **2026-11-07T12:42:25.619991+00:00** HODL: POST-LOSS REVIEW / HODL / $-21.81 / exit stop. Contributing factors: none. Every check is listed with its result. Checks: - holder_distribution: CLEAN top-1 0.12%; top-10 1.23%; excluding pool and burn; entry snapshot top non-LP holder 0.15% - fresh_wallet_cluster: FAILED failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge… - linked_wallet_cluster: FAILED failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge… - bundle_sniper_share: FAILED failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge… - dev_creator: CLEAN creator wallets 2QRJuvWpQZa9twTahzCX4htcKyg9cdqCvUey3xkaGcV8, 9NkVW544fKy2kkU5ZxJFa1xy6C7LssPKZAW5XWbK5XG5; holding not in the top holder sample; 0 creator sell(s) totaling 0 tokens in 5 sampled pool fills - liquidity: CLEAN liquidity $164,650.47 at entry → $142,856.56 at exit (-13.2%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked - volume_profile: CLEAN volume $2,171,989.76 at entry → $2,752,271.10 at exit (26.7%). wash no wash round-trip in 5 sampled pool fills - price_mcap_path: CLEAN price 0.003965 → 0.002962 (-25.3%) over 338.8 minutes; entry was 86.1% of the recorded window ATH; market cap at review $2,949,640.00; recorded stop 12% - on_chain_anomalies: CLEAN mint authority is not active; freeze authority is not active; no extra on-chain warning Recorded exit price 0.002962. Improve entries: do not add a filter from HODL; these checks failed after retry: fresh_wallet_cluster (failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting client. Please try the request again with the following configuration parameter: "maxSupportedTransactionVersion": 1'}; https://api.mainnet-beta.solana.com: ge…); linked_wallet_cluster (failed after 2 attempts: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missin…

- **2026-11-07T15:21:17.428906+00:00** GLITCH: POST-LOSS REVIEW / GLITCH / $-14.35 / exit stop. Contributing factors: none. Every check is listed with its result. Checks: - holder_distribution: CLEAN top-1 3.59%; top-10 27.97%; excluding pool and burn; entry snapshot top non-LP holder 3.59% - fresh_wallet_cluster: CLEAN 0 fresh wallets in 5 sampled top holders holding 0.00% combined (block at 3 wallets, or 2+ wallets at 8%) - linked_wallet_cluster: CLEAN no shared funder in the sample; 0 of 5 holders had a known funder (funder reads run on complete short histories) - bundle_sniper_share: CLEAN no same-slot bundle and no sniper share at the cap in 0 known acquisition slots - dev_creator: CLEAN creator wallets 3aHjYRK99d3gBKeU3qJ6BDU7JJjcgYamEmvRoe4fuSQL, 26XjAAxuHjkampzMDErpcp9HG3QH15Ds8NufAgp7sB9S; holding not in the top holder sample; 0 creator sell(s) totaling 0 tokens in 4 sampled pool fills - liquidity: CLEAN liquidity $148,008.09 at entry → $131,881.96 at exit (-10.9%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked - volume_profile: CLEAN volume $242,131.62 at entry → $271,769.22 at exit (12.2%). wash no wash round-trip in 4 sampled pool fills - price_mcap_path: CLEAN price 0.002865 → 0.002288 (-20.1%) over 375.4 minutes; entry was 55.4% of the recorded window ATH; market cap at review $2,119,417.00; recorded stop 12% - on_chain_anomalies: CLEAN mint authority is not active; freeze authority is not active; no extra on-chain warning Recorded exit price 0.002288. Improve entries: no red flag was measured on GLITCH. price 0.002865 → 0.002288 (-20.1%) over 375.4 minutes; entry was 55.4% of the recorded window ATH; market cap at review $2,119,417.00; recorded stop 12%. Holder, cluster, bundle, creator, liquidity, volume, and authority checks were clean. Do not add an entry filter from this close.

- **2026-11-07T22:49:53.893175+00:00** GATO: POST-LOSS REVIEW / GATO / $-4.16 / exit time. Contributing factors: - 3 fresh wallets in 5 sampled top holders holding 5.87% combined (block at 3 wallets, or 2+ wallets at 8%) Checks: - holder_distribution: CLEAN top-1 3.32%; top-10 14.23%; excluding pool and burn; entry snapshot top non-LP holder 3.32% - fresh_wallet_cluster: FLAG 3 fresh wallets in 5 sampled top holders holding 5.87% combined (block at 3 wallets, or 2+ wallets at 8%) - linked_wallet_cluster: CLEAN largest shared funder uvkhfimfuMJKUDMNEUmqACWRXMG8QSQA2i2SYEdXTHn has 1 wallet(s) and 1.42%; 4 holders had a known funder - bundle_sniper_share: CLEAN no same-slot bundle and no sniper share at the cap in 3 known acquisition slots - dev_creator: FAILED failed after 2 attempts: creator 8CW4bxSMm3gLCdWgW8qSqTbQkm3jQug4xe1nmmdoCUhY, 5MVneCfDge5vtf4C7QZmczCJbBB8vfvDbMqvopvkBLJm holding 5MVneCfDge5vtf4C7QZmczCJbBB8vfvDbMqvopvkBLJm 3.32%; sells were not read: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not support… - liquidity: CLEAN liquidity $370,962.45 at entry → $366,623.46 at exit (-1.2%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked - volume_profile: FAILED failed after 2 attempts: UNKNOWN / FAIL CLOSED: getTransaction failed on all public endpoints after backoff: https://public.rpc.solanavibestation.com: getTransaction: missing result or RPC error {'code': -32015, 'message': 'Transaction version (1) is not supported by the requesting clien. Recorded volume $1,522,734.87 at entry → $2,000,812.70 at exit (31.4%) - price_mcap_path: CLEAN price 0.01241 → 0.0121 (-2.5%) over 1007.6 minutes; entry was 84.6% of the recorded window ATH; market cap at review $11,971,783.00; recorded stop 12% - on_chain_anomalies: CLEAN mint authority is not active; freeze authority is not active; no extra on-chain warning Recorded exit price 0.0121. Improve entries: GATO showed 3 fresh wallets in 5 sampled top holders holding 5.87% combined (block at 3 wallets, or 2+ wallets at 8%). This does not change entry gates or config thresholds.

- **2026-11-08T18:30:35.121628+00:00** MAGGIE: POST-LOSS REVIEW / MAGGIE / $-49.08 / exit stop. Contributing factors: - liquidity $78,961.48 at entry → $56,755.74 at exit (-28.1%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked Checks: - holder_distribution: CLEAN top-1 2.28%; top-10 15.20%; excluding pool and burn; entry snapshot top non-LP holder 2.28% - fresh_wallet_cluster: CLEAN 0 fresh wallets in 5 sampled top holders holding 0.00% combined (block at 3 wallets, or 2+ wallets at 8%) - linked_wallet_cluster: CLEAN no shared funder in the sample; 0 of 5 holders had a known funder (funder reads run on complete short histories) - bundle_sniper_share: CLEAN no same-slot bundle and no sniper share at the cap in 2 known acquisition slots - dev_creator: CLEAN creator wallets CK896YSefTonX5Yff6azHiF7T52x5bgEmqmnRU2wP6c1, 4V2jDkT2skdk23qSryjxJCmB14tY86BBws25Jm5pr9C3; holding not in the top holder sample; 0 creator sell(s) totaling 0 tokens in 0 sampled pool fills - liquidity: FLAG liquidity $78,961.48 at entry → $56,755.74 at exit (-28.1%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked - volume_profile: CLEAN volume $4,962,666.05 at entry → $5,398,069.98 at exit (8.8%). wash no wash round-trip in 0 sampled pool fills - price_mcap_path: CLEAN price 0.0006722 → 0.0003436 (-48.9%) over 111.8 minutes; entry was 52.8% of the recorded window ATH; market cap at review $334,438.00; recorded stop 12% - on_chain_anomalies: CLEAN mint authority is not active; freeze authority is not active; no extra on-chain warning Recorded exit price 0.0003436. Improve entries: MAGGIE showed liquidity $78,961.48 at entry → $56,755.74 at exit (-28.1%). LP chosen pool LP mint supply is 0 and mint authority is the pool or revoked. This does not change entry gates or config thresholds.


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
