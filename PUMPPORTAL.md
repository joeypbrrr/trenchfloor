# PumpPortal launch research: built, OFF, and not trade-ready on free data

Everything here is paper research. There is no wallet, API key, signing,
purchase, broker, funded subscription or real order. `candidate_source` remains
`legacy`; the new collector, profit stop and RPC resilience remain disabled.
Existing research cadence is unchanged. Axiom was not used: the supplied check
returned HTTP 425 and no public feed was available. No bypass was attempted.

## Important free-tier limitation

PumpPortal's current official documentation says:

- `subscribeNewToken`: FREE.
- `subscribeMigration`: FREE.
- `subscribeTokenTrade` and `subscribeAccountTrade`: **metered at 0.01 SOL per
  10,000 events**, requiring an API key and a linked wallet funded with at least
  0.02 SOL.

Source, opened November 6, 2026: https://pumpportal.fun/data-api/real-time

Therefore the collector connects only to `wss://pumpportal.fun/api/data`, sends
only the two free subscriptions and never requests a token/account trade feed.
It reads no API keys or wallet credentials. Setting `trade_stream_enabled=true`
refuses to start, rather than incurring a charge. **The requested free per-token
trade subscriptions cannot be delivered on this service under the free-only and
no-wallet constraints.** Their subscription cap/unsubscribe behavior has not been
implemented as a pretend working free feature. There are zero active token-trade
subscriptions. A local tracking cap/expiry exists for stored launch candidates.

## What works

`pumpportal_collector.py` is a small, separate process with:

- one websocket guarded by a box-wide collector lock, including during tests;
- SQLite/WAL local storage of create/migration events and any supplied trade
  events, with mint, trader, side, SOL amount, token amount, slot if supplied,
  raw public event, time, fee rate and observed fee accounting;
- signature/economic-event deduplication, including duplicate initial create/buy
  events, address validation, capped tracking (64 mints), 60-minute expiry;
- reconnect/backoff up to 60 seconds; a disconnect/restart invalidates coverage;
- migration/post-curve venue detection invalidating coverage;
- explicit OFF-by-default startup in `start.sh`, shutdown in `stop.sh`.

Token metadata URIs are stored but never fetched. No incoming message can change
hosts, credentials, files, configuration or the collector's subscription methods.
The SQLite store and lock are ignored by git and are not in the published site.
The separate live dashboard and its event implementation were not changed.

The adapter selects from these launches, not DexScreener paid boosts. It fetches
one fresh GeckoTerminal SOL/USD quote and uses
`marketCapSol × SOL/USD`; token-event freshness is checked independently so a
fresh SOL quote cannot make a stale coin price current. DexScreener may enrich
pool identifiers and real reported liquidity, never supply discovery candidates.
Virtual bonding-curve reserves are **not** labeled as real liquidity.

## Fee accounting, not invented coverage

The current official pump.fun fee page, last updated October 17, 2026, publishes
SOL/USDC bonding-curve fees of **1.25% total**: creator 0.300%, protocol 0.95%,
LP 0%. Source, opened November 6, 2026:
https://pump.fun/docs/fees

`pumpportal.bonding_curve_fee_rate=0.0125` is configurable. For each observed
SOL bonding-curve event, scheduled fee accounting is
`abs(solAmount) × fee_rate`; rates are stored per event. This is protocol+creator
fee accounting, **not** network gas, app/platform fees, every possible routed
fee, or verification of actual on-chain fee transfers. 1.5 SOL at this rate
requires 120 SOL of cumulative covered trade notional, not 120 SOL of profit.

`global_fees_observed_sol` is kept separate from `global_fees_sol`. The latter is
only populated with complete create-to-now trade coverage, an uninterrupted live
connection, a current fee schedule and no migration. Creation alone is never
sufficient. The free collector NEVER sets `coverage_complete=1`, because it does
not have a complete trade stream. Thus free launches have **unknown global fees,
zero fee-verified candidates, and fail closed**. No volume proxy is allowed for
this source, even if the older generic proxy flag is on.

A reconnect has no replay mechanism; all existing candidates remain partial.
Migration ends coverage even if a migrated pool later appears on another site.
The configured schedule review deadline is December 6, 2026; expired or missing
review metadata invalidates verification. Future complete-trade integration
would need explicit approval and independently documented coverage; merely
flipping a local database flag is not a supported integration.

## Filters and thresholds

All source-specific thresholds are under `pumpportal` in config.json. Failure or
unmeasured/unknown status is a rejection, not an approval. The feed publishes a
one-line explanation per filter, including when RPC checks were not reached.
`failure_counts_all_checks` is nonexclusive: one coin can fail multiple filters;
post-RPC checks on prefiltered coins are reported as unknown/unmeasured, not as
proof they are scams.

| Rule | Default | Why |
| --- | --- | --- |
| Market cap | >= $6,000 | Requested floor; fresh SOL conversion |
| Cumulative covered fees | >= 1.5 SOL | Requested floor; unknown is not zero/pass |
| Coin-event freshness | <=120 seconds | Old creation price is not a live quote |
| Observed age | >=15 minutes; <=7 days | Avoid immediate launch chasing |
| Observed buy/sell trades | >=50, excluding create | Require an activity sample |
| Unique traders | >=20 | Avoid one/few-wallet activity |
| Buy/sell count ratio | 0.25–4 inclusive | Reject one-sided/no-sell samples |
| Single-wallet SOL-volume share | <=10% | Obvious wash/dominance screen |
| Recent volume | >=20 SOL / 5 minutes | Require actual observed activity |
| Volume acceleration | >=1.2× preceding 5 minutes | Trending rather than stale activity |
| Developer holdings | <=2% of RPC supply, summed token accounts | Limit creator inventory |
| Developer dump | Reject sold-out by default or >=50% initial allocation sold | Flag creator exits; unknown coverage fails |
| Largest wallet | <=3.5% | Existing Bubble Map rule retained |
| Top-10 wallets | <=30% | Concentration cap |
| Launch burst | <=4 buys in first 2 slots | Bundle/sniper burst screen |
| Launch allocation | <=10% of supply in first 2 slots | Limit launch concentration |
| Fresh/linked early allocation | <=5% | Limit sampled connected-launch exposure |
| Wallet age evidence | a signature >=24h before creation | Lack of old history remains unknown |
| Provenance work | <=4 wallets, <=8 launch-slot transaction lookups | Bound free RPC use |

Slot data absent from the free create feed stays unknown. If complete trade
coverage is ever supplied, bounded RPC transaction lookups can recover launch
slots; failure to establish the entire configured first-slot window remains
unknown. A bounded shared-funder sample is a risk signal, not exhaustive proof
that wallets are unrelated or volume is organic.

Mint and freeze authority must be explicitly revoked in RPC data. Essential
account or owner data missing from RPC stays incomplete. Developer holdings use
`getTokenAccountsByOwner`; historical developer sale flags require complete
observations. Curve exclusion requires BOTH canonical PDA derivation for this
mint and an RPC account owned by the official Pump program. The program address
was checked against the official public Pump IDL:
https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json

Wallet balances in the largest-account sample are aggregated by owner. Rather
than assuming unobserved supply is harmless, holder/top-10 checks use conservative
upper bounds including unaccounted balances. This can reject good coins, but
cannot silently approve unknown concentration. Approximate balance matches are
not used to exclude an apparent launch whale as an LP.

Existing real-liquidity >=$12,000, reported daily volume >=$8,000, market-cap
ceiling $20m, lessons, Risk Manager/Token-2022 checks and linked-wallet vetoes
remain. Existing dip/green-bounce/no-top-tick rules, hourly candle requirement
and strategy promotion gates were not loosened. A 15-minute-old launch passing
one new prefilter would still not bypass the old history/liquidity requirements.

## Setup and exact switches (only after approval)

Dependencies are isolated from the running legacy interpreter:

```bash
python3 -m venv --system-site-packages .venv-pumpportal
.venv-pumpportal/bin/python -m pip install -r requirements-collector.txt
```

`websocket-client` provides public websocket reads. `solders` is used only for
public-key/PDA validation, never wallets or signatures. The research wrapper
uses this environment only when the selected source is `pumpportal`; legacy
startup still uses the same Python interpreter as before. Missing curve
validation support fails closed.

To enable **free ingestion/research only**, after approval:

```json
{
  "candidate_source": "pumpportal",
  "daily_stop_enabled": true,
  "daily_profit_stop_usd": 300,
  "rpc_resilience_enabled": true,
  "pumpportal": {
    "collector_enabled": true,
    "trade_stream_enabled": false,
    "db_path": "data/pumpportal.sqlite3"
  }
}
```

Merge those keys with existing config, do not replace all the threshold fields.
Then restart Trenchfloor with `./stop.sh && ./start.sh` to launch the separate
collector and pick the optional interpreter. **These switches cannot turn the
metered trade feed into a free feed; strict fees will still reject every coin.**
They are not a recommendation to enable this as a working trading strategy.
There is no minimum trade count, no expected $300/day income, and no new edge
measurement from a feed with zero qualifying trades.

## Isolated tests

A timed free collector test ignores only the OFF flag, never the free-only guard:

```bash
python3 pumpportal_collector.py --test-seconds 610 --db /workspace/trenchfloor-pumpportal-test.sqlite3
python3 research.py --dry-run --candidate-source pumpportal --pumpportal-db /workspace/trenchfloor-pumpportal-test.sqlite3 --report-json /workspace/trenchfloor-pumpportal-dry.json
.venv-pumpportal/bin/python -m unittest discover -s tests -v
```

Dry runs use a temporary copy of research state, suppress publishes/live-floor
telemetry and never alter the live ledger, lessons, config or collector store.
Test results are appended below after the required ten-minute observation.


### Measured run: November 6, 2026 (ET)

- Collection: **11:16:03 PM–11:26:14 PM ET**, about 611 seconds.
- Exactly **one connection**, two free subscription requests, no reconnects,
  no 429/rate-limit errors and no paid token/account subscriptions.
- **73 create events, six migration events, 79 total stored events**, with 64
  locally tracked mints at the cap. No buy/sell stream was requested or received.
- **Zero fee-verified candidates**. The aggregate 0.5433472234 SOL scheduled
  fee accounting on observed initial creator buys is only a partial observation
  across all launches, NOT verified cumulative fees for any coin.
- Two post-collection isolated cycles each selected 30 of 73 launches, with
  zero prefilter survivors, zero RPC reviews, zero eligible histories and
  **zero new paper trades**. SOL/USD read was about $89.755.
- Measured dry-run cycle durations: 0.247s, 0.180s.

Nonexclusive failures/unknowns in each 30-coin screen:

- `market_cap`: 30/30.
- `global_fees`: 30/30.
- `minimum_age`: 30/30.
- `observed_trades`: 30/30.
- `unique_traders`: 30/30.
- `buy_sell_balance`: 30/30.
- `wallet_volume_dominance`: 30/30.
- `recent_real_volume`: 30/30.
- `trending_volume`: 30/30.
- `launch_slot_burst`: 30/30.
- `launch_supply`: 30/30.
- `fresh_or_linked_launch`: 30/30.
- `mint_authority`: 30/30.
- `freeze_authority`: 30/30.
- `dev_holdings`: 30/30.
- `dev_dump`: 30/30.
- `top_holder`: 30/30.
- `top10_concentration`: 30/30.
- `curve_exclusion`: 30/30.
- `existing_liquidity`: 29/30.
- `existing_daily_volume`: 30/30.
- `standing_lessons`: 29/30.
- `market_data_fresh`: 20/30.

Market cap was the first rejection for all 30. Every selected launch was younger
than the configured 15-minute minimum. Authority, developer, slot, linkage and
holder checks listed above were **unmeasured/unknown because prefilters prevented
RPC review**, not 30 proven scams. Real reported liquidity failed or was
unavailable for 29/30; it was not fabricated from virtual reserves. Unknown fees alone would also block every launch.

The full offline suite passed (55 tests in the isolated optional environment),
including canonical curve derivation against a real collected launch, fee-rate
math, create/buy deduplication, cap/expiry, migration/reconnect coverage loss,
paid-stream refusal before networking, OFF-by-default behavior, unknown-risk
rejections and conservative holder upper bounds. Actual received events were
also replayed through the latest parser without claiming complete trade coverage.

Reports on the box: `/workspace/trenchfloor-pumpportal-collector-summary.json`,
`/workspace/trenchfloor-pumpportal-dry-1.json`,
`/workspace/trenchfloor-pumpportal-dry-2.json`; raw local test store:
`/workspace/trenchfloor-pumpportal-test.sqlite3`. The timed test has stopped.
The live source is still `legacy`, all new flags are OFF and no test data was
imported into the live paper ledger. These results provide no new profit edge
and cannot establish that $300/day is realistic.
