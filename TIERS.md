# Owner-approved paper tiers — November 6, 2026, 11:52–11:54 PM ET

No wallet, broker, signed transaction, swap submission, or real funds. Public
DexScreener selection adapter remains `legacy` with existing GeckoTerminal
pool/OHLCV assistance. PumpPortal and fee proxy stay off. $300 realized daily
ET latch, $1000 account and rolling 3600s entry limit remain unchanged.

## Primary

Market cap $6000–$1B, liquidity >=$5000, 24h volume >=$2000, pair age
15 minutes–365 days, standard SOL/USDC/USDT quote, positive measured price.
After common hard blocks: top sampled non-pool wallet <=15%, sampled top10
<=65%; current quote 5–95% of measured historical window high. Green candle
optional. History must exist for primary ATH; future candle highs excluded.

## Fallback

Only selected when there are zero fully eligible primary candidates. Market
cap $6000–$10B, liquidity >=$1000, 24h volume >=$500, age 5min–3650 days,
positive measured price and standard quote. Top sampled non-pool wallet <=20%,
top10 <=100% (no additional soft top10 restriction), no ATH or green requirement.
Rank both tiers: `2*log10(1+liquidity)+log10(1+volume)-topHolderPct/20`.
The team votes on highest score first and picks at most one approved entry.

Primary ticket cap $100; fallback cap $50. Both also cap at 10% realized balance
and 10% currently available cash, preserving funded hourly capacity. Position
capacity expands from 1 to 24 (same 16h time-stop) so an existing position does
not prevent the next hourly entry. No borrowing or unfunded entries. 12% stop,
25% target and 16h time stop unchanged; fees/slippage still modeled. Tier is
stored on entry/closed fills and realized P&L is separately reported per tier.

## Same non-negotiable hard blocks in BOTH tiers

- Explicit revoked mint and freeze authorities; missing fields reject.
- Canonical SPL Token or canonical Token-2022 with only metadata/group/close
  extensions; transfer hooks, delegates, fees, pauses, and all unknown extensions
  reject. Custom programs reject.
- Every largest-account owner read; missing/truncated batch rejects/retries.
- A full-length successful RPC owner batch containing `null` means no native
  account at that address. That address CAN own SPL tokens; count it as an
  ordinary non-program wallet, not unknown and NEVER exclude it as a program.
- Single non-pool holder >20% rejects. Concentration is measured using the
  largest 20 token accounts, aggregated by owner. This is a SAMPLE, not proof
  of the entire wallet distribution or absence of related/split wallets.
- Pool exclusions use exact current RPC-verified pool/vault mint/owner and
  a known DEX program. Approximate balance-matching no longer excludes wallets.
- LP evidence must match the chosen DexScreener pool. Current LP mint supply
  zero, positive historical LP issuance and >=99.99% reported burn/lock are
  required. This implementation supports verified fully burned LP; nonzero
  supply/unsupported locks/unknown LP state reject conservatively.
- Honeypot/unsellable rejects. Sellability requires canonical SPL semantics,
  no active authorities/risky extensions, and a fresh wallet-free Jupiter
  sell-route quote through the exact verified pool, at the full primary cap.
  This is read-only route evidence, NOT guaranteed executable fills or a signed
  sell simulation. Missing route/evidence rejects; no execution APIs called.

RPC malformed/truncated batches fail over across existing configured endpoints
with bounded retries, rather than caching a partial response. Budget 240/cycle.
Up to 60 mints enriched and 12 deeply reviewed; enough capacity for multiple
market candidates, not a guarantee of safe candidates every market hour.

Minimum target is one funded paper entry per hour IF a qualifying coin exists.
Daily profit halt, rolling-hour cap, no cash or no known/pass hard-safe candidate
always wins. No trade is invented to satisfy a quota. Old soft lesson blacklist
(3.5% holder/min liquidity ratio) does not override the newly approved tiers;
current hard checks still apply. Shared checklist consulted before scoring;
all checklist content remains suggestion-only and is never auto-applied.

`data/traded_mints.json` permanently excludes every forward-entered mint BEFORE
scoring in BOTH tiers, including open/won/lost entries. Entry journal reconstructs
registry if interrupted between account and registry writes. Historical pre-reset
backtests never seed the registry. Account balance is NOT reset by this change.
Registry is included in each hourly Pages commit. Positions still managed/exited.

The immediate requested demo intentionally re-anchors next cycle to its completion
plus 3600s (previous anchor was Nov 7, 12:35:20 AM ET), preventing an early old-
anchor cycle from colliding with the demo's rolling-hour entry limit. One Pages
push per completed cycle, including timestamped chat and registry/checklist.
