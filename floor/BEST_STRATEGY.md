# Trenchfloor best strategy

**Paper trading / research only. No wallet. No real trades. Not financial advice.**

Champion `dip_20_40_stop8_tp15_hold8`, promoted 2026-11-06T20:40:07.191067-05:00 ET because it beat the previous out-of-sample record.

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
