# Trenchfloor realtime floor (paper research only)

- Public phone preview: https://joeypbrrr.github.io/trenchfloor/live/
  Static fallback polls published data every 60 seconds; banner explicitly says
  publishes hourly, not instantly. Root now uses this design; /preview/ is preserved and /floor/ redirects to root.
- Local read-only dashboard: http://127.0.0.1:8796/
- Private event receiver: http://127.0.0.1:8797/event (loopback only).
- Original local site (8795) and Pages root now use the approved continuous-room HTML.
- `./live_start.sh` starts auto-restarting dashboard and Cloudflare quick tunnel.
  `./live_start.sh --local-only` starts only the dashboard. `./live_stop.sh` stops both.
  These scripts are independent of research start/stop scripts.
- Publisher copies only live/ page/assets plus sanitized data/live_chat.json and
  data/checklist.json snapshots; chat/checklist snapshots update on every publish.
- Install cloudflared at `/workspace/bin/cloudflared` or set `CLOUDFLARED_BIN`.
  Current tunnel address appears in `logs/live-tunnel-current.log` and changes on
  every tunnel recreation. Quick tunnels have no uptime guarantee.

## Current hosting blocker

Cloudflared 2026.10.7 obtained a quick-tunnel name, but its built-in prechecks
reported both UDP/QUIC and TCP/HTTP2 outbound port 7844 blocked/unreachable.
The allocated hostname returned HTTP 530. The unusable tunnel was stopped;
no alternate network tunnel or network-policy bypass was attempted.
The dashboard remains running locally. A permitted tunnel-capable host/network,
or another explicitly approved hosting arrangement, is needed for phone access.

## Realtime transport and safety

Cloudflare quick tunnels explicitly do not support SSE (GET streams are buffered),
so the live page uses WebSockets at `/ws`. `/events` remains an SSE diagnostic for
local curl clients. The server pushes initial state, then event deltas immediately,
with full state refreshes and genuine research heartbeat updates every ~5 seconds.
The private server uses no browser JSON polling. On github.io (or WebSocket failure),
the same page switches to a 60-second static-data fallback. A bounded background queue in `events.py` POSTs each
telemetry event with a 0.5-second timeout. Failures/drop-on-overflow never break or
block research; telemetry is best effort, not an audit-grade delivery guarantee.
Events report when research has news; scanning cadence is not changed.

Public port 8796 rejects all POSTs, has no event-ingest route, and serves only an
explicit read-only allowlist. Ingest runs separately on loopback port 8797, rejects
forwarded/tunnel requests, and is never a tunnel target. No source/config files are
served. No wallet, broker, orders, trading controls or secrets exist here.
Test runners and `TRENCHFLOOR_EVENTS_DISABLED=1` suppress telemetry.

## Same floor, separate live copy

`live/index.html` is a copy of the existing published floor with its 3D room,
kitchen, two treadmills, bathroom, drag/touch rotation, and P&L calendar. This design removes room-jump buttons, defaults to full-floor framing, places the
calendar directly beneath the scene, and adds live bubbles, feed, chat/checklist.
Client-side cosmetic breaks have atomic central reservations: bathroom <=1,
each treadmill <=1, kitchen <=2; walking agents count as away, so >=3 stay at desks.
Real events request a return to the desk. Reduced-motion users do not get breaks.
These animations never emit research/trade events or affect trading logic.

## Persisted chat and structured-rule loss reviews

Recent 200 events: `data/cache/live-events.json`.
Last 1,000 chat messages, deduped reviewed trade IDs, and shared checklist:
`data/cache/live-chat-state.json`. Runtime files are ignored by Git and not included
in the existing Pages publisher allowlist. Chat entries are actual rule-based
research outputs, not invented autonomous conversation. Historical fills are
explicitly labeled as such.

**Forward paper position management is now enabled.** The reset account uses only
current paper entries and observed exits. Historical backtests are archived and
never treated as live losses. The checklist remains empty until a forward loss closes.

The forward-paper engine emits `trade_close` with `is_live_close=True`,
`historical=False`, and a trade object containing `mode="forward:paper"`,
`realized=True`, unique id, numeric entry_ts/exit_ts/pnl_usd, and no `sample` tag.
Entries must have opened after this feature started; future closes never qualify.
Live-ingest events must be within 120 seconds; trusted local journal replay recovers
missed reviews after restarts without accepting historical/backtest imports.
Available facts (ATH depth, entry/exit liquidity/volume, holders, duration, exit
reason, modeled slippage) become role-specific messages; missing fields are
explicitly unknown, and no causal claims are inferred from correlations.
Strategist deduplicates structured rules and supporting-loss counts. The checklist is applied before each selection: a violation rejects primary
and penalizes fallback score. It does not change the 12% stop / 35% target
minimum / 16h time limit.

## Verification

`TRENCHFLOOR_EVENTS_DISABLED=1 python3 -m unittest discover -s tests -v`

The live-specific tests cover provenance exclusions, empty state, persistence,
deduplication and support counts. JS was syntax-checked and the occupancy state
machine tested through 100,000 transitions. Local curl/SSE and raw RFC WebSocket
handshake/state-frame checks passed. Full browser rendering, real-iPhone tests
and requested screenshots are not yet verified/captured.

## Approved go-live — November 6, 2026 ET

Root now serves the continuous live-room design; /live/ remains an independent
working copy, /preview/ is preserved, /floor/ redirects to root. GitHub Pages
polls JSON every 60 seconds; data is published ONCE per completed hourly cycle.
There are no websockets on Pages, and phone caches can delay the new HTML.

`candidate_source=legacy` restores the original DexScreener lists/pair adapter
(with its original GeckoTerminal pool/OHLCV assistance), not GMGN/PumpPortal.
Verified global fees are unavailable, so that filter is explicitly SKIPPED and
logged; no fee proxy. Primary market cap >=$6,000; fallback treats market
floors as score penalties. Current three-hard-check policy is specified in TIERS.md.

Forward PAPER ONLY account starts at $1,000; historical ledger/snapshots are
archived under data/archive, not credited to balance/calendar. No broker/wallet.
Entries: ranked primary/fallback under TIERS.md with applied checklist rules,
three shared hard checks and team vote; one entry per rolling 3600s, persisted.
Up to 24 open positions. Primary $100 cap / fallback $50 cap, also capped at
10% realized balance and 10% available cash. No repeat forward-entered mint.
12% stop / 35% target minimum / 16h time stop. Public DexScreener marks checked every
60s while positions are open; gap losses can exceed modeled stop. Simulation
charges 30bps fee plus 80–200bps liquidity-based slippage per side.

Exits run before any entry gate. Deduplicated realized forward closes alone
feed the persistent $300 ET-day latch. Unrealized/backtest P&L does not count.
A durable close journal replays into ledger and factual rule-based loss reviews
(`data/cache/paper-chat-state.json`), published with the structured-rule checklist.
Historical simulations never create fake live closes or checklist rules.
Runner flock prevents a duplicate runner in THIS repository only.

## Position-first display — November 7, 2026 ET
The open-position panel sits directly above the 3D floor, before marketing and
the calendar, on desktop and phone. It reads `paper_account.positions`, shows
NEW during the first hour, size, entry and exact ET open time, tier, calculated
stop/target prices, ET time-stop deadline and DexScreener. Empty state includes
the next cycle's ET clock. Team trades counts open positions and closed ledger
trades separately. Chat renders newest first: latest 24 expanded, older messages
collapsible. Historical vote/entry text stays intact; current card uses the
current account exit policy. Display only: no paper/trade/schedule changes.
