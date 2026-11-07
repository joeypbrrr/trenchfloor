"""Paper dip-buyer. Historical bars only. Fees and slippage are modelled.

Never top-ticks: a bar that sets the running window high cannot be an entry
signal, and the next bar's open is skipped when it has left the zone or
printed at the high.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

ZONE_GRID = (0.20, 0.25, 0.30)
ZONE_HIGHS = (0.40, 0.45)
STOPS = (0.08, 0.12, 0.18)
TARGETS = (0.15, 0.25, 0.40)
HOLDS = (8, 16, 24)


def et_iso(ts):
    return datetime.fromtimestamp(ts, ET).isoformat()


def dollar_pnl(entry, exit_price, notional, cost_rate):
    """cost_rate is the fractional fee+slippage charged on each side."""
    if entry <= 0 or exit_price <= 0 or notional <= 0:
        raise ValueError("prices and notional must be positive")
    qty = notional / (entry * (1.0 + cost_rate))
    proceeds = qty * exit_price * (1.0 - cost_rate)
    return proceeds - notional


def slippage_bps(liquidity_usd, paper):
    bps = int(paper.get("base_slippage_bps", 80))
    liq = liquidity_usd or 0
    if liq < 25000:
        bps += int(paper.get("slippage_extra_below_25k_bps", 40))
    if liq < 12000:
        bps += int(paper.get("slippage_extra_below_12k_bps", 80))
    return bps


def variant_catalog():
    catalog = []
    for lo in ZONE_GRID:
        for hi in ZONE_HIGHS:
            if hi <= lo:
                continue
            for stop in STOPS:
                for target in TARGETS:
                    for hold in HOLDS:
                        vid = f"dip_{int(lo * 100)}_{int(hi * 100)}_stop{int(stop * 100)}_tp{int(target * 100)}_hold{hold}"
                        catalog.append({
                            "id": vid,
                            "zone_low": lo,
                            "zone_high": hi,
                            "stop": stop,
                            "target": target,
                            "hold_bars": hold,
                            "name": describe_variant(lo, hi, stop, target, hold),
                        })
    return catalog


def describe_variant(lo, hi, stop, target, hold):
    off_lo = int(round((1 - hi) * 100))
    off_hi = int(round((1 - lo) * 100))
    return (
        f"Buy the dip when price is {off_lo}–{off_hi}% off the window high "
        f"(trading at {int(lo * 100)}–{int(hi * 100)}% of that high), only after a green bar that does not set the high. "
        f"Never top-tick. Stop {int(stop * 100)}% below the next open, target {int(target * 100)}% above, "
        f"time-stop after {hold} hourly bars. Stop is filled first if a bar touches both."
    )


def trade_id(mint, strategy_id, entry_ts, exit_ts):
    raw = f"{mint}|{strategy_id}|{int(entry_ts)}|{int(exit_ts)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def simulate(bars, variant, token, paper, seed_ath=None):
    """Walk hourly bars. Returns paper trades. Does not look ahead of the signal bar except the traded path.

    seed_ath, when given, is a high from older daily candles that closed before
    the first hourly bar. It is not taken from the future.
    """
    if len(bars) < 3:
        return []
    notional = float(paper.get("notional_usd", 100))
    fee = int(paper.get("fee_bps_per_side", 30)) / 10000.0
    slip = slippage_bps(token.get("liquidity_usd"), paper) / 10000.0
    cost = fee + slip
    oos_cut_index = int(len(bars) * (1.0 - float(paper.get("oos_fraction", 0.30))))
    oos_cut_index = min(max(oos_cut_index, 1), len(bars) - 1)
    cut_ts = bars[oos_cut_index]["t"]
    lo = float(variant["zone_low"])
    hi = float(variant["zone_high"])
    stop_pct = float(variant["stop"])
    target_pct = float(variant["target"])
    hold = int(variant["hold_bars"])
    ath = bars[0]["h"]
    if seed_ath and seed_ath > ath:
        ath = seed_ath
    deltas = [bars[i]["t"] - bars[i - 1]["t"] for i in range(1, min(8, len(bars))) if bars[i]["t"] > bars[i - 1]["t"]]
    bar_seconds = int(sorted(deltas)[len(deltas) // 2]) if deltas else 3600
    trades = []
    i = 1
    while i < len(bars) - 1:
        bar = bars[i]
        prior = ath
        bounce = bar["c"] > bar["o"]
        frac = bar["c"] / prior if prior else 1.0
        # A bar that prints a new window high is a top tick and is never a signal.
        if lo <= frac <= hi and bounce and bar["h"] < prior:
            entry_i = i + 1
            entry = bars[entry_i]["o"]
            if entry > 0 and entry < prior and (entry / prior) <= hi:
                stop = entry * (1.0 - stop_pct)
                target = entry * (1.0 + target_pct)
                last = min(len(bars) - 1, entry_i + hold)
                exit_i = last
                exit_px = bars[last]["c"]
                reason = "time"
                for j in range(entry_i, last + 1):
                    touched_stop = bars[j]["l"] <= stop
                    touched_target = bars[j]["h"] >= target
                    if touched_stop:
                        exit_i = j
                        exit_px = stop
                        reason = "stop"
                        break
                    if touched_target:
                        exit_i = j
                        exit_px = target
                        reason = "target"
                        break
                pnl = dollar_pnl(entry, exit_px, notional, cost)
                entry_ts = bars[entry_i]["t"]
                exit_ts = bars[exit_i]["t"]
                mint = token["mint"]
                trades.append({
                    "id": trade_id(mint, variant["id"], entry_ts, exit_ts),
                    "label": "PAPER / SIMULATED",
                    "mint": mint,
                    "name": token.get("name") or token.get("symbol") or mint,
                    "symbol": token.get("symbol") or "?",
                    "pair": token.get("pool"),
                    "dex_url": f"https://dexscreener.com/solana/{mint}",
                    "gmgn_url": f"https://gmgn.ai/sol/token/{mint}",
                    "bubble_url": f"https://app.bubblemaps.io/sol/token/{mint}",
                    "entry_time": et_iso(entry_ts),
                    "exit_time": et_iso(exit_ts + bar_seconds),
                    "time_basis": "Entry is the next candle open. Exit is that candle's end (open plus the bar size). Free OHLCV has no intrabar fill time.",
                    "entry_ts": entry_ts,
                    "exit_ts": exit_ts,
                    "entry_price": entry,
                    "exit_price": exit_px,
                    "notional_usd": notional,
                    "pnl_usd": round(pnl, 4),
                    "pnl_pct": round(pnl / notional * 100.0, 4),
                    "side": "long",
                    "exit_reason": reason,
                    "strategy_id": variant["id"],
                    "strategy_name": variant["name"],
                    "sample": "out_of_sample" if entry_ts >= cut_ts else "in_sample",
                    "fees_bps_per_side": int(paper.get("fee_bps_per_side", 30)),
                    "slippage_bps_per_side": int(round(slip * 10000)),
                    "liquidity_usd": token.get("liquidity_usd"),
                    "market_cap_usd": token.get("market_cap_usd"),
                    "ath_price": prior,
                    "entry_frac_of_ath": round(entry / prior, 6) if prior else None,
                    "ath_note": token.get("ath_note"),
                })
                for k in range(i, exit_i + 1):
                    ath = max(ath, bars[k]["h"])
                i = exit_i + 1
                continue
        ath = max(prior, bar["h"])
        i += 1
    return trades


def metrics(trades):
    if not trades:
        return {"trades": 0, "net_usd": 0.0, "expectancy_usd": None, "win_rate": None, "profit_factor": None, "wins": 0, "losses": 0}
    pnls = [t["pnl_usd"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_loss = sum(losses)
    pf = None
    if gross_loss < 0:
        pf = round(sum(wins) / abs(gross_loss), 4)
    return {
        "trades": len(pnls),
        "net_usd": round(sum(pnls), 4),
        "expectancy_usd": round(sum(pnls) / len(pnls), 4),
        "win_rate": round(len(wins) / len(pnls), 4),
        "profit_factor": pf,
        "wins": len(wins),
        "losses": len(losses),
    }


def split_samples(trades):
    ins = [t for t in trades if t.get("sample") != "out_of_sample"]
    oos = [t for t in trades if t.get("sample") == "out_of_sample"]
    return ins, oos


def beats(oos_metrics, champion_oos, min_trades):
    if not oos_metrics or oos_metrics["trades"] < min_trades:
        return False
    if oos_metrics["expectancy_usd"] is None or oos_metrics["expectancy_usd"] <= 0:
        return False
    if not champion_oos or champion_oos.get("expectancy_usd") is None:
        return True
    return oos_metrics["expectancy_usd"] > float(champion_oos["expectancy_usd"]) + 0.01


DAYS_PER_MONTH = 30.44


def oos_window_seconds(tokens, paper):
    """Length of the out-of-sample slice: the longest last-30% window across the tested pools.

    Pools are traded side by side, so trades per month is the pooled OOS trade
    count divided by this one shared window, not by the sum of the windows.
    """
    frac = float(paper.get("oos_fraction", 0.30))
    best = 0
    for token in tokens:
        bars = token.get("bars") or []
        if len(bars) < 3:
            continue
        cut = min(max(int(len(bars) * (1.0 - frac)), 1), len(bars) - 1)
        deltas = [bars[i]["t"] - bars[i - 1]["t"] for i in range(1, min(8, len(bars))) if bars[i]["t"] > bars[i - 1]["t"]]
        bar_seconds = int(sorted(deltas)[len(deltas) // 2]) if deltas else 3600
        best = max(best, bars[-1]["t"] - bars[cut]["t"] + bar_seconds)
    return best


def goal_projection(oos_metrics, window_seconds, notional, goal_low, goal_high):
    """Projected monthly paper P&L from out-of-sample results.

    monthly = average $ per OOS trade x OOS trades per month. P&L is linear in
    the ticket because fees and slippage are percentages, so the ticket needed
    for a goal is notional x goal / monthly. Real fills at bigger tickets would
    slip more; this does not model that.
    """
    trades = int((oos_metrics or {}).get("trades") or 0)
    exp = (oos_metrics or {}).get("expectancy_usd")
    out = {
        "notional_usd": notional,
        "oos_trades": trades,
        "oos_window_days": round(window_seconds / 86400.0, 2) if window_seconds else None,
        "trades_per_month": None,
        "expectancy_usd": exp,
        "monthly_usd": None,
        "ticket_for_low_usd": None,
        "ticket_for_high_usd": None,
        "goal_low_usd": goal_low,
        "goal_high_usd": goal_high,
    }
    if not trades or not window_seconds or exp is None:
        return out
    per_month = trades / (window_seconds / 86400.0) * DAYS_PER_MONTH
    monthly = exp * per_month
    out["trades_per_month"] = round(per_month, 1)
    out["monthly_usd"] = round(monthly, 2)
    if monthly > 0:
        out["ticket_for_low_usd"] = round(notional * goal_low / monthly, 0)
        out["ticket_for_high_usd"] = round(notional * goal_high / monthly, 0)
    return out


def beats_goal(oos_metrics, projection, champion, min_trades):
    """Promotion toward the monthly goal. The out-of-sample gates in beats() always apply first."""
    if not beats(oos_metrics, None, min_trades):
        return False
    champ_proj = (champion or {}).get("goal") or {}
    if champion and champ_proj.get("monthly_usd") is not None:
        return (projection.get("monthly_usd") or 0) > float(champ_proj["monthly_usd"]) + 0.01
    # Legacy champion without a monthly projection: fall back to the old per-trade rule.
    return beats(oos_metrics, (champion or {}).get("oos"), min_trades)
