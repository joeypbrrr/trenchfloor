# Trenchfloor best strategy

**Paper trading / research only. No wallet. No real trades. Not financial advice.**

## Standing goal

Joey's standing goal: at least **$3,000–$5,000 extra per month**. Every agent reads this; the Strategist ranks promotions by projected monthly P&L toward it.

The goal never loosens the safety rules: a version still needs at least 5 out-of-sample paper trades, a positive out-of-sample average, and must not be previously rejected. Everything here is paper / simulated; projections are not income.

Champion `dip_20_40_stop8_tp15_hold8`, promoted 2026-11-06T20:40:07.190842-05:00 ET because it beat the previous out-of-sample record.

## Rule

Buy the dip when price is 60–80% off the window high (trading at 20–40% of that high), only after a green bar that does not set the high. Never top-tick. Stop 8% below the next open, target 15% above, time-stop after 8 hourly bars. Stop is filled first if a bar touches both.

Each simulated trade uses a fresh $100 paper notional. Entries are next-bar opens after a bounce inside the zone. A bar that sets the window high is never an entry. If a later bar touches the stop and the target, the stop is used.

## Out-of-sample result that earned the promotion

- Trades: 9
- Average P&L per trade: $0.4082
- Net P&L: $3.6742
- Win rate: 0.4444
- Profit factor: 1.0793

## Pools in that test

- DONNA `FMqWsXKaAe41Kxfji7v5cpzQmr2gKAteAi9wREmkpump` pool `7vURUpBXG3Z5qJTCSTvG3VxumXEnQfnUPJDZ3Cgw2tkT`
- jeff `HAsTKXYvv65zM7J6Cu5o5PcZsiKMQYo5oz4WPjgqwP6k` pool `JCXWfcZGjgJC8NZa5Qb6JP3cgvqW4vGUg4Tqj87G5ZnY`

ATH is the highest high in the free GeckoTerminal window fetched for each pool (daily up to 90 bars and hourly up to 168). It is not a guaranteed lifetime high when the endpoint returns less. In-sample numbers are not the promotion basis and are stored on the variant record in `data/lessons.json`.

## Goal progress

Goal $3k–5k/mo: no version qualifies with a monthly projection this cycle (need ≥5 out-of-sample trades and a positive average). Champion dip_20_40_stop8_tp15_hold8 predates the goal and has no measured trade frequency yet. Not loosening the out-of-sample rule to chase the goal.

Paper ticket: $100. Updated 2026-11-06T23:35:20.242204-05:00 ET.

| Version | Role | Status | OOS trades | Avg $/trade | Trades/mo | Projected $/mo at ticket | Ticket for low goal | Ticket for high goal | Qualifies |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dip_20_40_stop8_tp15_hold8` | champion | champion | 9 | $0.41 | — | — | — | — | yes |

Projected monthly P&L = out-of-sample average $ per trade × out-of-sample trades per month (pooled OOS trade count ÷ the OOS window length × 30.44 days). Ticket needed = $100 × goal ÷ projected monthly. Promotion requires ≥5 OOS trades, a positive average, and a variant that is not rejected; among those, the higher projected monthly P&L wins.
