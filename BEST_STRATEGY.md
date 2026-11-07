# Trenchfloor best strategy

**PAPER / SIMULATED. Not a live signal. No wallet. No real trades. Not financial advice.**

No out-of-sample champion yet. This file is replaced only when a strategy variant beats the current champion on the out-of-sample slice. In-sample results never replace it.

## Standing principle

Buy dips. Never top-tick.

Preferred entry zone: the coin trades at 20–45% of the window ATH (55–80% off that high), and only after a bounce bar whose high does not set the ATH. Enter on the next bar's open when that open is still inside the zone and below the high. Model AMM fees and slippage. Exit on a stop, a target, or a time limit — stop first if a bar touches both.

## Promotion rule

A variant replaces this document only when all of the following are true on the out-of-sample bars (the latest 30% of each pool's fetched history, pooled):

- at least 5 closed paper trades
- average dollar P&L per trade greater than the current champion, or greater than $0 when there is no champion
- the variant is not already in the tried or rejected registry

ATH here is the highest high in the free GeckoTerminal window that was fetched (daily candles, up to 90, plus hourly candles, up to 168). It is not a guaranteed lifetime high when the free endpoint returns a shorter window. Each simulated trade uses a fresh $100 paper notional. P&L is a sum of those tickets, not a compounded account.

## Current champion

None.
