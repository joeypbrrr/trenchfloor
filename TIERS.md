# Current owner-approved paper policy — November 7, 2026 ET

This supersedes the earlier executor brief's non-negotiable LP/holder wording.
Paper simulation only: no wallet, signed transaction, execution, or real money.
DexScreener legacy selection adapter (original GeckoTerminal assistance), $1000
account, $300 realized ET-day hard-stop latch, hourly schedule and persistent
max one new entry per rolling 3600 seconds remain unchanged.

## Common hard blocks (both tiers, unknown fails closed)

1. Unsellable/honeypot: no positive sell-route quote, unknown sell route, known
   paused/nontransferable state, or unknown pause state rejects.
2. Active mint authority rejects; missing/unknown authority rejects.
3. Active freeze authority rejects; missing/unknown authority rejects.
4. Pair age under 15 minutes, or unknown pair age, rejects.
5. Top 10 holders excluding the pool and burn addresses above 40% reject.
   A missing measurement rejects.
6. Fresh-wallet cluster among the sampled top holders rejects: 3 or more
   wallets whose full signature page starts within 24 hours, or 2 or more of
   those wallets holding 8% combined, or 2 or more sharing a SOL funder and
   holding 5% combined. An unreadable signature sample rejects. A full page is
   not called fresh.
7. Bundle / sniper share rejects: 3 or more sampled holders acquired in the
   same slot, or 3 or more acquired within 5 slots of the earliest sample and
   still holding 15% combined. Unreadable acquisition slots reject.
8. Wash trade rejects: an upstream wash flag, or a sampled signer whose
   round-trip is at least 30% of the sampled pool flow. An unreadable
   pool-trade sample rejects. A small two-sided fill inside a much larger
   sample does not.
9. LP lock/burn not visible on the chosen pool's own LP mint rejects. Pass
   requires that LP mint's supply to be zero and its mint authority to be the
   pool or revoked. A positive circulating supply rejects.
10. Global fees under 1.5 SOL reject. Verified cumulative fees can pass or
    fail. Otherwise an on-chain PumpSwap unclaimed protocol+creator balance is
    only a lower bound (sweeps remove it). A lower bound already at 1.5 SOL
    passes. A smaller or unreadable bound rejects. DexScreener volume is not
    a fee proxy and is not a skip.

Authority evidence comes directly from current parsed RPC mint data, independent
of LP/holder scans. Wallet-free Jupiter GET quotes supply route evidence, not a
signed sell simulation or guaranteed execution. There is no exact-pool routing
restriction. A transfer hook is NOT automatically a hard reject merely because
it exists: no route or a known unsellable/paused state is the hard reject.

Pair age, top-10 ex pool/burn, fresh-wallet clusters, bundle/sniper share,
wash, LP lock/burn visibility, and the 1.5 SOL global-fee rule are hard blocks
on primary and fallback. They are not fallback score penalties. Single-holder
concentration above 20%, holder-observation completeness, and risky or unknown
Token-2022 extensions still reject PRIMARY and are score penalties in FALLBACK.
Errors in those remaining soft observations must not be reported as a missing
mint or freeze authority or a missing sell route.

## Primary criteria

Pair age 15min–365d; liquidity >=$5000; 24h volume >=$2000; measured market cap
$6000–$1B; standard quote and positive measured price/pool. Current quote must
be 5–95% of the measured window ATH; green candle optional except when required
by an active checklist rule. Single sampled non-pool wallet <=20% (was 15%);
sampled top10 <=65% remains a primary criterion and is now also capped at 40%
by the shared hard gate. LP lock/burn must be visible (hard gate) and no risky/unknown token extensions;
unsupported LP locks remain unverified primary rejects. Violating any ACTIVE
checklist rule rejects primary. Missing required rule observations are violations.

## Fallback criteria and scoring

Used ONLY if there are zero fully eligible primary candidates. Consider all
untraded positive-price/pool candidates, not only those meeting soft market
floors. Every hard block above MUST pass, including the gates that used to be
soft. The old fallback market criteria (age 5min–3650d, liquidity $1000,
volume $500, mcap $6000–$10B) stay soft scoring criteria, except pair age is
now a 15-minute hard block when the timestamp is known and an unknown age
blocks. No ATH/green requirement unless it contributes a checklist penalty.
Single-holder concentration and risky extensions are still not fallback vetoes.
Top-10, LP lock/burn, fresh-wallet clusters, bundles, wash, and global fees are.

Base score: `2*log10(1+liquidity)+log10(1+volume)-topHolderPct/20`.
Subtract 3 points per failed/unknown soft-risk check (holder completeness,
single holder >20%, risky/unknown extensions), 2 for sampled top10
>65% when the hard 40% cap somehow did not already reject, 4 per active checklist predicate violation (including required unknowns),
and 2 for not meeting the soft fallback market criteria. Team votes on best
score first. Fallback single-holder concentration, extensions, and checklist
items are penalties. Top-10, LP, clusters, wash, and fees are hard vetoes.
The recorded trade includes tier, full penalty breakdown and checklist audit.

Primary ticket cap $100; fallback cap $50. Both also cap at 10% realized balance
and 10% available cash, with max 24 open positions. Daily halt and rolling-hour
entry limit remain authoritative. A minimum target cannot create a fictitious
sell route, bypass active/unknown authorities, mint money or reset the entry cap.

## Structured checklist, now CONSULTED AND APPLIED

`data/cache/paper-chat-state.json` persists canonical rule items. Each carries
allowlisted `{field, op, value, missing_violation}` predicates, an enabled flag,
source loss IDs and support count. No arbitrary text evaluation or code execution.
Consult is logged before selection; each violation logs PRIMARY REJECT / FALLBACK
SCORE PENALTY, and is applied before final ranking/vote. The old advisory status
has been removed from active UI/publisher/current rule items; historical chat
bodies remain unchanged audit records of the policy then in effect.

Loss-review mappings:
- liquidity/volume deterioration: >= -20% vs preceding persisted observation.
- stop confirmation: recently closed green hourly candle required.
- time-exit/instrumentation/legacy unknown lessons: complete market/holder entry
  evidence required. These rules do NOT shorten the approved 16h time limit.
Unknown/unsupported structured predicates are violations, not silent passes.
Rules persist and support counts deduplicate. No causal success is promised.

## Exit specification — applied to the OPEN COGE position too

12% price stop, take-profit **at least 35%** above entry, 16-hour time limit.
`paper.target_fraction=0.35`, `paper.target_floor_fraction=0.35` (was 0.25).
Existing lower snapshotted targets are upgraded with a durable policy-update
record and chat line; higher targets are not reduced. Current mark observations,
not guaranteed executable fills, drive exits. Fees/slippage still modeled.
The open COGE entry itself, balance and original entry timestamp are not reset.

## Permanent entry exclusion and schedule

`data/traded_mints.json` excludes every forward-entered mint BEFORE scoring in
both tiers, regardless of open/won/lost state. Entry journal reconstructs registry
if interrupted. Historical pre-reset backtests never seed it. Exits still run.

NO new demo cycle/trade for this policy revision. Restart only the Trenchfloor
runner and preserve next cycle exactly November 7, 2026, 1:00:09 AM ET. Position
management continues about every 60s. One push includes the tested code/policy
snapshot; hourly publication continues normally thereafter.

Measurement limits: concentration uses largest 20 token accounts aggregated by
owner, not a full wallet census. Pool exclusions require exact RPC-verified
mint/vault owner, never approximate balances. Fully burned LP is supported;
unverified locks are soft unknowns. Public API failures remain explicit.
