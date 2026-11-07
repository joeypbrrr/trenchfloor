# Trenchfloor

Six paper-trading research agents work as **one team** with one memory and **one shared paper P&L**. They study Solana meme coins with free public data and write simulated trades. **Paper trading / research only. No wallet. No real trades. Not financial advice.**

There is no broker, no private key, and no paid API. The default `legacy` mode keeps GMGN link-only. Optional discovery adapters are described below; all are read-only and off by default. A GMGN key is optional and is never required for the free substitute.

Live floor (main page): https://joeypbrrr.github.io/trenchfloor/ · Design mockup with mock data: https://joeypbrrr.github.io/trenchfloor/preview/ · `/floor/` redirects to the main page.

## What the agents do

They share `data/research.json`, `data/lessons.json`, and `data/ledger/`.

| Agent | Job |
| --- | --- |
| Risk Manager | Rug research on the public Solana RPC: `getAccountInfo` (jsonParsed), `getTokenLargestAccounts`, `getTokenSupply`. Mint and freeze authority, Token-2022 extensions (`permanentDelegate`, transfer hooks, transfer fee, non-transferable, default account state), creator/dev wallets only when the mint account actually names them, liquidity versus market cap, and LP locked or burned only when that is visible. |
| Bubble Map Analyst | Fails a token when one wallet that is not the LP vault and not a program holds more than 3.5% of supply. Samples a few recent signatures for a shared SOL funding source or the same slot. Links `https://app.bubblemaps.io/sol/token/<mint>`. |
| X/Twitter Scout | Reads DexScreener token boosts and profiles, which carry X links. If `api.twitter.com` is not reachable without a key, the status says so. Tweets are never invented. |
| Data Scout | New and trending Solana pools from GeckoTerminal, plus DexScreener pair metrics. Filters are in `config.json` (liquidity, 24h volume, pair age, market cap). The preferred entry zone is 55–80% off the window ATH, meaning price at 20–45% of that high. |
| Backtester | Simulated dip buys on GeckoTerminal hourly candles. AMM fees and liquidity-based slippage are deducted. Fills are labeled `PAPER / SIMULATED` and stored by America/New_York exit date. |
| Strategist | Ranks eligible tokens, proposes two untried dip variants each cycle, and replaces `BEST_STRATEGY.md` only when a variant beats the current champion out of sample. |

A full cycle is every 30 minutes. A lighter scan (new pools and new X links, no safety review and no paper trades) runs every 5 minutes. A health check every 3 minutes refreshes heartbeats, flags stale agents, and checks the local site and the Pages URL.

## Standing goal

Joey's standing goal: at least **$3,000–$5,000 extra per month**. It lives in `config.json` (`monthly_goal_low`, `monthly_goal_high`), in every agent's start-of-cycle banner, in `BEST_STRATEGY.md` (the Strategist rewrites that file every cycle and the "Standing goal" and "Goal progress" sections are part of its template in `memory.py`), in `data/research.json` under `goal`, and on the site.

The Strategist projects monthly paper P&L for each candidate and the champion from out-of-sample results only: average $ per OOS trade × OOS trades per month (pooled OOS trade count ÷ the OOS window length × 30.44 days). It reports that at the $100 paper ticket and the ticket size that would be needed for $3k and $5k a month (P&L is linear in ticket because fees and slippage are percentages; real fills at bigger tickets would slip more). Promotion is ranked by projected monthly P&L, but the gates never move: at least 5 out-of-sample trades, a positive out-of-sample average, and not previously rejected. A champion promoted before the goal existed has no measured trade frequency, so the first challenger is compared on the old per-trade rule. Each cycle the Strategist posts one goal-status line in the feed, and says so plainly when nothing qualifies. Paper projections are not income.

## One team, one P&L

There is no per-agent P&L. Every paper trade goes into one shared team ledger, and the headline P&L and the calendar are team totals.

Each simulated fill is a **proposal**. It is attributed to one agent (`proposed_by`): the Data Scout when it flagged the token inside the 20–45% entry zone this cycle, otherwise the Strategist, whose dip variant triggered the fill. Before the fill is written to the ledger, all six agents vote (`team.py`), each with a one-line reason taken from its own check results:

| Agent | Vote |
| --- | --- |
| Risk Manager | Rejects on any chain-safety fail, incomplete review, risky Token-2022 extension, or lesson block. **Veto.** |
| Bubble Map Analyst | Rejects when one non-LP, non-program wallet holds more than 3.5%, a linked-wallet cluster fails, or concentration was not measured. **Veto.** |
| X/Twitter Scout | Abstains while the X API is unavailable (it returns 401 without a paid key). It never invents tweets or sentiment. |
| Data Scout | Rejects when liquidity or 24h volume is under the floor, or the entry is outside the 20–45% of window ATH zone. |
| Backtester | Looks only at earlier simulated fills on the same pool and variant that closed before this entry. Rejects when there are at least 3 and they net negative. |
| Strategist | Rejects a variant that is already rejected, or an entry above the variant's dip zone (a top tick). |

The trade is taken only when a strict majority of the agents that voted (abstentions excluded) approve **and** neither the Risk Manager nor the Bubble Map Analyst rejected. Ledger rows and feed events carry `proposed_by` and `team` (`tally` such as `5/6 approve`, `rule`, `vetoes`, and every vote with its reason). Turned-down proposals are counted in the feed and not written to the ledger. Variant scoring for `BEST_STRATEGY.md` still uses every simulated fill so the out-of-sample test is not biased by the vote. Trades logged before the team vote existed have no `team` field and are shown as such.

## Learning loop

`data/lessons.json` and `LESSONS.md` are rewritten as rules are learned and are still there after a restart.

After each cycle the floor turns failed tokens and losing paper trades into dated rules, for example "skip tokens with live mint authority" or "skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply". Every agent reads those rules before acting. A mint that failed stays in `rejected_mints`, so the next cycle does not spend RPC on it. A strategy variant that was rejected or already tried is kept in the registry and is not retested. A variant with too few out-of-sample trades is deferred and may be tried up to three times.

`BEST_STRATEGY.md` is the standing dip rule until an out-of-sample result beats it. In-sample profit never replaces that file. The promotion rule is at least 5 out-of-sample paper trades and a higher average dollar P&L than the current champion.

The site renders the rules with America/New_York timestamps.

## Paper ledger and the calendar

Each closed simulation is a fresh $100 paper ticket, not a compounded account. Entry is the next candle's open after a green bar inside the zone whose high did not set the window high. Exit is the stop, the target, or the time stop. If one candle touches both stop and target, the stop is used. Entry time is the candle open. Exit time is the candle close (open plus the bar size). GeckoTerminal does not provide an intrabar fill time, and none is invented.

Files:

- `data/ledger/YYYY-MM-DD.json` — that ET day's trades and the day's total P&L
- `data/ledger/index.json` — one row per day for the calendar

A trade row, in the feed and in the day view, shows the token name and symbol, ET entry, ET exit, entry price, exit price, dollar P&L, a DexScreener link (`https://dexscreener.com/solana/<mint>`), and a GMGN link (`https://gmgn.ai/sol/token/<mint>`).

## Activity feed

Notable finds and paper trades are appended to `data/feed.json` immediately. The publisher pushes that file on its own, at most about every 45 seconds, so a burst of trades does not become a burst of git pushes. The page polls `data/feed.json` every 12 seconds and animates new rows.

GitHub Pages usually needs about a minute after the push before the new JSON is visible. The local server at `http://127.0.0.1:8795` does not have that delay.

## Run it

The always-on box needs Python 3.11+ (stdlib only), git, and credentials that can push this repo. No pip packages and no API keys.

```bash
git clone https://github.com/joeypbrrr/trenchfloor.git
cd trenchfloor
chmod +x start.sh stop.sh run_research.sh run_server.sh
./start.sh
```

`start.sh` background-starts two restart loops with `setsid`, PID files, and logs:

- `research.py` — the 30-minute cycle, 5-minute light scan, and 3-minute health check
- `server.py` — read-only static files on `127.0.0.1:8795`

```bash
./stop.sh
touch data/cycle.requested    # ask the running loop for a cycle now
python3 research.py --once --no-publish   # one cycle, files only
python3 -m unittest tests.test_core tests.test_publish
```

Logs: `logs/research.log`, `logs/server.log`. The loop does not commit to `main`. It writes `data/` locally and publishes the site to `gh-pages`.

Filters, the paper ticket size, fees, slippage, and rate-limit spacing live in `config.json`.

## Publish and GitHub Pages

`publish_data.py` copies the static site, `BEST_STRATEGY.md`, `LESSONS.md`, and the JSON under `data/` into a separate checkout and pushes branch `gh-pages`. It uses the git credentials already on the machine. It does not take a token on the command line.

If the push is rejected, it fetches, rebases, and keeps this publisher's copy of the files (`git rebase -X theirs`, which during a rebase is the commit being replayed). It retries that up to four times.

```bash
python3 publish_data.py            # site + data
python3 publish_data.py --feed-only
python3 publish_data.py --dry-run
```

Enable Pages once, on the box or in the repo settings: **Settings → Pages → Deploy from branch → `gh-pages` → `/ (root)` → Save.** The first successful publish creates `gh-pages` if it does not exist. Add a `.nojekyll` file is already in the published tree so `data/*.json` is served as-is.

## Data sources

| Source | Used for | Key |
| --- | --- | --- |
| DexScreener token-boosts, token-profiles, tokens v1 | Discovery, X links, liquidity, volume, market cap, pair age | none |
| GeckoTerminal new pools, trending pools, pool OHLCV | Discovery and candle history | none |
| Public Solana RPC | Mint, supply, largest accounts, a short signature sample | none |
| Birdeye | Probed without a key. A 401 is recorded and the source is not used | none |
| X/Twitter | Probed without a key. A 401 is recorded. No tweets are invented | none |
| GMGN | Legacy: not requested; opt-in read-only API requires an env key; unauthenticated site blocked | See opt-in modes below |

Rate limits are spaced in `config.json`. A failed call stays an error on the site. Missing numbers are left missing.

## The site

`index.html` is one self-contained page (Three.js from jsDelivr) with the same look as the design mockup, driven only by real files: `data/research.json`, `data/feed.json`, and `data/ledger/*.json`. A black room with orange neon holds six agents at one desk (left to right in roster order), a kitchen, two treadmills, and a bathroom. Drag to rotate, pinch or scroll to zoom, and two-finger drag to pan. The Desk, Kitchen, Treadmills, and Bathroom buttons move the camera, and Reset view brings it back. Panels: goal and best strategy, the team with live agent status, the team P&L calendar with an equity curve and a day view, the team paper ledger with "Proposed by X · n/6 approve" and vote dots, the ranked watchlist, the live feed, the learning log, and sources and health. Missing data shows an empty state, never a placeholder number. There is no service worker; `sw.js` only retires old ones. Installable from a phone: `manifest.webmanifest` and Apple web-app tags.

## Limits

Window ATH is the highest high in the fetched GeckoTerminal daily (up to 90) and hourly (up to 168) candles, not a guaranteed lifetime high. Holder links use a handful of recent signatures, not a full bubble map. Many meme coins fail the 3.5% wallet rule; they are recorded as fails and are not paper-traded. Out-of-sample bars are the latest 30% of each pool. Simulated P&L is not a prediction.


## Opt-in discovery and daily profit stop (disabled by default)

**No trading or cadence settings were enabled by this change.** There is no
minimum trade count. `cycle_seconds` stays at its existing 1800, light scans at
300, health checks at 180; the 1-minute request was withdrawn. Publisher behavior
is unchanged. No broker, wallet, signatures or real orders exist.

Config defaults:

```json
{
  "candidate_source": "legacy",
  "daily_profit_stop_usd": 300,
  "daily_stop_enabled": false,
  "rpc_resilience_enabled": false,
  "fee_proxy_enabled": false,
  "new_source_min_market_cap_usd": 6000,
  "new_source_min_global_fees_sol": 1.5
}
```

After approval only: select `candidate_source="gmgn_substitute"`, set
`daily_stop_enabled=true` and `rpc_resilience_enabled=true`. Leave
`fee_proxy_enabled=false` for the requested strict rule. **This strict substitute
currently yields NO trades because actual global fees are unavailable.** It is
not a way around that safety requirement. The baseline legacy filters remain
unchanged when `candidate_source` is `legacy`.

`candidate_sources.py` supplies:

- `gmgn_substitute`: clearly labeled GeckoTerminal trending/new **Solana** pools;
  no DexScreener boosted/profile candidate discovery. Reported DEX volume is
  observed, but cannot prove it is organic rather than wash trading.
- `gmgn`: optional key-only read access at `openapi.gmgn.ai`, using only
  `GET /v1/market/rank` and read-only `POST /v1/trenches`; the key comes from
  `GMGN_API_KEY` in the process environment, never a file, log, command argument
  or git. Missing key fails closed, with no automatic fallback or website
  requests. DexScreener may supply pool/quote identifiers for GMGN candidates
  only. Authentication/request schema follows the published gmgn-cli 1.7.1.
  This adapter is untested against an authenticated account. The public website
  was blocked with Cloudflare 403 in the parallel connectivity check; no bypass
  or load test was attempted. Free API access requires a free-tier key; no paid
  plan or private/signing key is requested.

### Filters in the new modes

- Verified market cap >= $6,000 and <= $20m; unknown market cap fails, and FDV is
  **not** silently substituted for market cap.
- Global cumulative fees >= 1.5 SOL; unknown actual global fees FAIL CLOSED.
  GMGN `gas_fee` is average gas per transaction, not cumulative SOL global fees.
  The free docs do not establish units/coverage for raw `total_fee`, so the adapter
  does not mislabel it as verified SOL fees. GeckoTerminal exposes no such field.
- Existing liquidity >= $12,000, reported 24h volume >= $8,000, pair age 6 hours
  to 60 days, SOL/USDC/USDT quote, standing lessons, mint/freeze/Token-2022 checks,
  and 3.5% single-holder/linked-wallet veto remain. Known wash trading is rejected.
  Missing essential holder/account data stays incomplete in new modes.
- Dip rules are not loosened: the standing zone is 20–45% of window ATH; the
  champion's narrower 20–40% band, green bounce, stop/target/hold rules remain.
  A new pool appearing in discovery is not an immediate buy. 30 hourly bars are
  still required. This intentionally excludes very young launches.
- An **independent experimental flag** `fee_proxy_enabled=true` explicitly
  replaces missing fees with a labeled proxy: reported 24h volume × assumed
  0.3% DEX fee / a fresh SOL USD quote. This is **not** network/global cumulative
  fees, does not prove real volume, and is not equivalent to Joey's strict filter.
  It is OFF by default and needs separate approval. Missing SOL quote still fails.
  Proxy and strict results use separate mode namespaces.

### Daily stop semantics and limitations

`daily_stop.py:DailyStop.status` recalculates mode-specific ET-day realized P&L,
using `exit_time` (candle **close**, not the older `exit_ts` candle open). It
excludes future exits and deduplicates the same mint/entry/exit/price/notional
across strategy variants. State is latched in `data/daily_stop.json` per mode and
ET calendar day, survives restart and later losses, and resets at ET midnight.

`research.py:cycle` checks it every cycle and logs it in the feed. The entry gate
in `run_variants` is checked **before every team vote**, and approved fills are
recorded one at a time, so a batch cannot skip over the threshold. `team.py`'s
optional pre-vote hook preserves the Backtester's earlier-fill history and the
existing six-agent veto rules. The main page displays OFF / ARMED / HALTED,
realized P&L, target and mode. Scanning and exit processing are not halted.

**Important:** this repository is a historical backtest ledger, not a forward
paper position manager. It has no open-position lifecycle to manage. The gate
limits newly recorded simulation entries and excludes unclosed backtest candles;
it does not turn backtests into actual forward realized trading income. Any
future forward-paper execution engine must call this entry gate with its own
mode-specific closed-fill ledger and keep its exit manager outside the gate.
It is impossible to guarantee exactly $300, and open positions could subsequently
reduce P&L. A profit stop does not create a positive trading edge.

### RPC resilience (also opt-in)

`rpc_resilience_enabled=true` creates a fresh bounded RPC client each full cycle,
resetting stale caches, budgets and failure state. It enumerates each configured
public endpoint in a stable order, retries once after backoff and never exceeds
the configured 64-call budget. It uses existing free mainnet/publicnode/vibestation
fallbacks, no API keys. All three answered a parsed mint read during testing.
The tested drpc endpoint refused Solana on its free plan, so it was **not** added.
A final read-only token review completed 7 RPC requests in 7.790s but returned
`incomplete: one or more holder owners could not be read` (zero transport errors),
so RPC connectivity is improved, not a guarantee of complete holder coverage.
Partial/failed safety results never become passes in the new modes. The old
client's rotating index could repeat endpoints within one attempt sequence, and
its lifetime budget/cache/failure state was never reset between cycles.

### Isolated verification

These commands copy data to a temporary sandbox and never publish, alter live
ledgers/lessons, change live config, or send live-floor telemetry:

```bash
python3 research.py --dry-run --candidate-source gmgn_substitute --report-json /workspace/trenchfloor-dry-strict.json
python3 research.py --dry-run --candidate-source gmgn_substitute --fee-proxy --report-json /workspace/trenchfloor-dry-proxy.json
python3 -m unittest discover -s tests -v
```

Tests run November 6, 2026, about 11:07–11:10 PM ET:

- Two strict-fee cycles: each discovered 38 unique mints, capped at 30 rows,
  skipped one prior rejection, rejected all 29 remaining for unknown global
  fees, zero eligible/trades. Measured scan duration 2.135s and 2.140s.
- Labeled-proxy experiment: 38 discovered / 30 rows / 1 known rejection;
  1 passed filters, 1 safety review, failed holder concentration, zero eligible
  or trades. 12 RPC requests; measured duration about 18s. A later proxy cycle
  discovered 39 mints, capped at 30, skipped 2 existing rejections and had zero
  survivors or trades in 4.180s. This is **not** evidence
  that a qualifying new-source strategy is profitable.
- Discovery uses two GeckoTerminal requests per cycle; the optional proxy adds
  one fresh SOL quote; history adds at most six OHLCV requests. Existing 2.05s
  spacing stays in force. No attempt was made to find a maximum rate by flooding
  providers. At unchanged 30-minute full cycles, discovery averages 0.067 req/min,
  plus unchanged light scans. GMGN public-site polling has no demonstrated safe
  rate (403); authenticated API capacity was not tested.
- Legacy champion: only 9 OOS trades, +$0.4082/trade at $100, 44.44% win rate.
  Last 24h: 4 deduplicated closed champion simulations, -$13.8143, 25% wins.
  At that tiny measured OOS edge, a **hypothetical** 3 fills/day would imply about
  $24,498 per ticket to average $300/day; $100 tickets would need ~735 fills/day.
  Neither is a realistic income forecast in thin coins. There is no minimum
  trade count, no new-source measured edge, and no promise of $300/day.


## PumpPortal launch collector (OFF; free-tier limitation)

See [PUMPPORTAL.md](PUMPPORTAL.md) for the source, official 1.25% bonding-curve
fee schedule, conservative launch-risk thresholds and test results. Creates and
migrations are free; per-token trades are documented as metered and require a
funded wallet, so this free-only build does not subscribe to them. No complete
trade history means no verified global fees and no qualifying trades. All new
flags remain OFF; existing source and cycle spacing are unchanged.
