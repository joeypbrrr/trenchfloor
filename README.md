# Trenchfloor

Six paper-trading research agents work as **one team** with one memory and **one shared paper P&L**. They study Solana meme coins with free public data and write simulated trades. **Paper trading / research only. No wallet. No real trades. Not financial advice.**

There is no broker, no private key, and no paid API. GMGN is never a filter or a data source. A token page may link to `https://gmgn.ai/sol/token/<mint>` the same way it links to DexScreener.

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
| GMGN | Not requested | — |

Rate limits are spaced in `config.json`. A failed call stays an error on the site. Missing numbers are left missing.

## The site

`index.html` is one self-contained page (Three.js from jsDelivr) with the same look as the design mockup, driven only by real files: `data/research.json`, `data/feed.json`, and `data/ledger/*.json`. A black room with orange neon holds six agents at one desk (left to right in roster order), a kitchen, two treadmills, and a bathroom. Drag to rotate, pinch or scroll to zoom, and two-finger drag to pan. The Desk, Kitchen, Treadmills, and Bathroom buttons move the camera, and Reset view brings it back. Panels: goal and best strategy, the team with live agent status, the team P&L calendar with an equity curve and a day view, the team paper ledger with "Proposed by X · n/6 approve" and vote dots, the ranked watchlist, the live feed, the learning log, and sources and health. Missing data shows an empty state, never a placeholder number. There is no service worker; `sw.js` only retires old ones. Installable from a phone: `manifest.webmanifest` and Apple web-app tags.

## Limits

Window ATH is the highest high in the fetched GeckoTerminal daily (up to 90) and hourly (up to 168) candles, not a guaranteed lifetime high. Holder links use a handful of recent signatures, not a full bubble map. Many meme coins fail the 3.5% wallet rule; they are recorded as fails and are not paper-traded. Out-of-sample bars are the latest 30% of each pool. Simulated P&L is not a prediction.
