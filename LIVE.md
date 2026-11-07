# Trenchfloor realtime floor (paper research only)

- Local read-only dashboard: http://127.0.0.1:8796/
- Private event receiver: http://127.0.0.1:8797/event (loopback only).
- Original local site (8795), Pages HTML, Pages links and publisher are unchanged.
- `./live_start.sh` starts auto-restarting dashboard and Cloudflare quick tunnel.
  `./live_start.sh --local-only` starts only the dashboard. `./live_stop.sh` stops both.
  These scripts are independent of research start/stop scripts.
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
No browser JSON polling. A bounded background queue in `events.py` POSTs each
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
kitchen, two treadmills, bathroom, drag/touch rotation, and P&L calendar. Only
this copy removes room-jump buttons, defaults to full-floor framing, places the
calendar directly beneath the scene, and adds live bubbles, feed, chat/checklist.
Client-side cosmetic breaks have atomic central reservations: bathroom <=1,
each treadmill <=1, kitchen <=2; walking agents count as away, so >=3 stay at desks.
Real events request a return to the desk. Reduced-motion users do not get breaks.
These animations never emit research/trade events or affect trading logic.

## Persisted chat and suggestion-only loss reviews

Recent 200 events: `data/cache/live-events.json`.
Last 1,000 chat messages, deduped reviewed trade IDs, and shared checklist:
`data/cache/live-chat-state.json`. Runtime files are ignored by Git and not included
in the existing Pages publisher allowlist. Chat entries are actual rule-based
research outputs, not invented autonomous conversation. Historical fills are
explicitly labeled as such.

**Current engine simulates historical fills. There is no forward paper position
manager yet. Consequently there are no eligible live closes and the checklist is
honestly empty.** The review consumer is implemented and tested, but it will not
pretend historical backtests are live losses.

A future forward-paper engine can emit `trade_close` with `is_live_close=True`,
`historical=False`, and a trade object containing `mode="forward:paper"`,
`realized=True`, unique id, numeric entry_ts/exit_ts/pnl_usd, and no `sample` tag.
Entries must have opened after this feature started, closes must not be future
and must have occurred within 120 seconds. Backtests/past imports never qualify.
Available facts (ATH depth, entry/exit liquidity/volume, holders, duration, exit
reason, modeled slippage) become role-specific messages; missing fields are
explicitly unknown, and no causal claims are inferred from correlations.
Strategist deduplicates suggestions and supporting-loss counts. The checklist
never modifies config, strategy, filters, or the existing lessons rules.

## Verification

`TRENCHFLOOR_EVENTS_DISABLED=1 python3 -m unittest discover -s tests -v`

The live-specific tests cover provenance exclusions, empty state, persistence,
deduplication and support counts. JS was syntax-checked and the occupancy state
machine tested through 100,000 transitions. Local curl/SSE and raw RFC WebSocket
handshake/state-frame checks passed. Full browser rendering, real-iPhone tests
and requested screenshots are not yet verified/captured.
