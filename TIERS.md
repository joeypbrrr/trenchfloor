# Current owner-approved paper policy — November 7, 2026 ET

This supersedes the earlier executor brief's non-negotiable LP/holder wording.
Paper simulation only: no wallet, signed transaction, execution, or real money.
DexScreener legacy selection adapter (original GeckoTerminal assistance), $1000
account, $300 realized ET-day hard-stop latch, hourly schedule and persistent
max one new entry per rolling 3600 seconds remain unchanged.

## EXACTLY THREE common hard blocks

1. Unsellable/honeypot: no positive sell-route quote, unknown sell route, known
   paused/nontransferable state, or unknown pause state rejects.
2. Active mint authority rejects; missing/unknown authority rejects.
3. Active freeze authority rejects; missing/unknown authority rejects.

Authority evidence comes directly from current parsed RPC mint data, independent
of LP/holder scans. Wallet-free Jupiter GET quotes supply route evidence, not a
signed sell simulation or guaranteed execution. There is no exact-pool routing
restriction. A transfer hook is NOT automatically a hard reject merely because
it exists: no route or a known unsellable/paused state is the hard reject.

LP lock/burn, wallet concentration, holder observation completeness, and risky
or unknown Token-2022 extensions are NOT hard blocks. They reject PRIMARY, and
are score penalties in FALLBACK. Errors/unknowns in these soft observations must
not be falsely reported as missing mint/freeze authority or missing sell route.

## Primary criteria

Pair age 15min–365d; liquidity >=$5000; 24h volume >=$2000; measured market cap
$6000–$1B; standard quote and positive measured price/pool. Current quote must
be 5–95% of the measured window ATH; green candle optional except when required
by an active checklist rule. Single sampled non-pool wallet <=20% (was 15%);
sampled top10 <=65%. LP lock/burn verified and no risky/unknown token extensions;
unsupported LP locks remain unverified primary rejects. Violating any ACTIVE
checklist rule rejects primary. Missing required rule observations are violations.

## Fallback criteria and scoring

Used ONLY if there are zero fully eligible primary candidates. Consider all
untraded positive-price/pool candidates, not only those meeting soft market
floors. The three hard checks above MUST all pass. The old fallback market
criteria (age 5min–3650d, liquidity $1000, volume $500, mcap $6000–$10B) are now
soft scoring criteria rather than vetoes. No ATH/green requirement unless it
contributes a checklist penalty. No concentration, LP, or risky-extension veto.

Base score: `2*log10(1+liquidity)+log10(1+volume)-topHolderPct/20`.
Subtract 3 points per failed/unknown soft-risk check (holder completeness,
single holder >20%, LP evidence, risky/unknown extensions), 2 for sampled top10
>65%, 4 per active checklist predicate violation (including required unknowns),
and 2 for not meeting the soft fallback market criteria. Team votes on best
score first; fallback concentration/LP/extensions/checklist cannot be hard vetoes.
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
