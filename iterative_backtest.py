#!/usr/bin/env python3
"""Iterative paper backtester.

Learns entry filters from losing historical paper trades, checks each idea on
the train split, and keeps it only when the held-out split is not worse.
This module is not used by the live research loop, forward paper entries, or
config.json gates.

No number is invented. A feature that was not read stays unmeasured and cannot
become a rule. Chain snapshots taken after the historical entry are reported
and are not promoted.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from backtest import metrics, simulate, variant_catalog
from entry_gates import gather_entry_evidence, measure_entry_signals

DISCLAIMER = "Paper trading / research only. No wallet. No real trades. Not financial advice."
P_MAX = 0.10

# Screens below are research starting points. They are not written back to
# config.json and they do not change assess_entry_gates.
FEATURE_SPECS = {
    "bundle_supply_pct": {
        "op": ">",
        "default": 15.0,
        "floor": 5.0,
        "standing": True,
        "label": "bundled or linked wallet supply %",
        "rule": "skip bundled coins whose bundled or linked wallets hold more than {threshold:g}% of supply",
    },
    "top10_ex_pool_burn_pct": {
        "op": ">",
        "default": 40.0,
        "floor": 10.0,
        "label": "top-10 holders ex pool and burn %",
        "rule": "skip coins whose top-10 non-pool non-burn holders exceed {threshold:g}% of supply",
    },
    "fresh_wallet_count": {
        "op": ">",
        "default": 2.0,
        "floor": 1.0,
        "label": "fresh wallets in the top-holder sample",
        "rule": "skip coins with more than {threshold:g} fresh wallets in the top-holder sample",
    },
    "fresh_cluster_pct": {
        "op": ">",
        "default": 8.0,
        "floor": 4.0,
        "label": "fresh-wallet cluster supply %",
        "rule": "skip coins whose fresh-wallet cluster holds more than {threshold:g}% of supply",
    },
    "wash_roundtrip_fraction": {
        "op": ">",
        "default": 0.30,
        "floor": 0.15,
        "label": "wash round-trip fraction of sampled flow",
        "rule": "skip coins whose largest sampled round-trip exceeds {threshold:g} of pool flow",
    },
    "dev_hold_pct": {
        "op": ">",
        "default": 2.0,
        "floor": 1.0,
        "label": "dev or creator holding %",
        "rule": "skip coins whose dev or creator wallet holds more than {threshold:g}% of supply",
    },
    "dev_sold_fraction": {
        "op": ">",
        "default": 0.50,
        "floor": 0.20,
        "label": "fraction of dev supply sold",
        "rule": "skip coins whose dev wallet has sold more than {threshold:g} of its supply",
    },
    "dev_sold_flag": {
        "op": ">",
        "default": 0.5,
        "floor": 0.5,
        "label": "dev sold out (1 = yes)",
        "rule": "skip coins whose dev wallet has sold out",
    },
    "pair_age_hours": {
        "op": "<",
        "default": 0.25,
        "ceiling": 24.0,
        "label": "pair age at entry in hours",
        "rule": "skip entries where the pair is younger than {threshold:g} hours",
    },
    "entry_frac_of_ath": {
        "op": ">",
        "default": 0.45,
        "floor": 0.20,
        "ceiling": 0.95,
        "label": "entry price as a fraction of the window high (mcap ratio if supply is unchanged)",
        "rule": "skip entries above {threshold:g} of the window high",
    },
    "volume_top_share": {
        "op": ">",
        "default": 0.50,
        "floor": 0.30,
        "label": "largest pre-entry bar's share of the prior 12 bars' volume",
        "rule": "skip entries where one of the prior 12 bars holds more than {threshold:g} of that volume",
    },
    "liquidity_drop_pct": {
        "op": ">",
        "default": 50.0,
        "floor": 20.0,
        "label": "liquidity drop from the prior-window peak into the entry bar, %",
        "rule": "skip entries after a liquidity drop of more than {threshold:g}%",
    },
    "snapshot_liq_to_mcap": {
        "op": "<",
        "default": 0.05,
        "ceiling": 0.20,
        "snapshot_only": True,
        "label": "snapshot liquidity divided by snapshot market cap",
        "rule": "skip coins whose snapshot liquidity is under {threshold:g} of market cap",
    },
    "snapshot_holder_pct_sum": {
        "op": ">",
        "default": 40.0,
        "floor": 10.0,
        "snapshot_only": True,
        "label": "sum of stored non-pool human holder percents",
        "rule": "skip coins whose stored human holders sum to more than {threshold:g}%",
    },
}

EVIDENCE_FEATURES = (
    "bundle_supply_pct",
    "top10_ex_pool_burn_pct",
    "fresh_wallet_count",
    "fresh_cluster_pct",
    "wash_roundtrip_fraction",
    "dev_hold_pct",
    "dev_sold_fraction",
    "dev_sold_flag",
)


def _round(value, digits=4):
    if value is None:
        return None
    return round(float(value), digits)


def _mean(values):
    return sum(values) / len(values) if values else None


def _variance(values):
    if len(values) < 2:
        return None
    mid = _mean(values)
    return sum((value - mid) ** 2 for value in values) / (len(values) - 1)


def welch_p_flagged_worse(flagged, clean):
    """One-sided normal approximation of Welch's t.

    Small p means the flagged trades' average P&L is lower than the unflagged
    trades'. Returns None when either side has fewer than two observations.
    """
    if len(flagged) < 2 or len(clean) < 2:
        return None
    var_flagged = _variance(flagged)
    var_clean = _variance(clean)
    if var_flagged is None or var_clean is None:
        return None
    se2 = var_flagged / len(flagged) + var_clean / len(clean)
    diff = _mean(flagged) - _mean(clean)
    if se2 <= 1e-18:
        if diff < 0:
            return 0.0
        if diff > 0:
            return 1.0
        return 0.5
    stat = diff / math.sqrt(se2)
    return 0.5 * (1.0 + math.erf(stat / math.sqrt(2.0)))


def summarize_trades(trades):
    base = metrics(trades)
    wins = [float(trade["pnl_usd"]) for trade in trades if trade["pnl_usd"] > 0]
    losses = [float(trade["pnl_usd"]) for trade in trades if trade["pnl_usd"] <= 0]
    ordered = sorted(trades, key=lambda trade: (trade.get("exit_ts") or 0, str(trade.get("id") or "")))
    peak = 0.0
    cum = 0.0
    max_dd = 0.0
    for trade in ordered:
        cum += float(trade["pnl_usd"])
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    return {
        "trades": base["trades"],
        "wins": base["wins"],
        "losses": base["losses"],
        "win_rate": base["win_rate"],
        "avg_win_usd": _round(_mean(wins)) if wins else None,
        "avg_loss_usd": _round(_mean(losses)) if losses else None,
        "expectancy_usd": base["expectancy_usd"],
        "pnl_usd": base["net_usd"],
        "net_usd": base["net_usd"],
        "profit_factor": base["profit_factor"],
        "max_drawdown_usd": _round(max_dd),
    }


def volume_top_share(bars, entry_ts, lookback=12):
    prior = [bar for bar in bars if bar.get("t") is not None and bar["t"] < entry_ts]
    window = prior[-lookback:]
    if len(window) < 3:
        return None
    vols = []
    for bar in window:
        if "v" not in bar or bar.get("v") is None:
            return None
        vols.append(float(bar["v"]))
    total = sum(vols)
    if total <= 0:
        return None
    return max(vols) / total


def liquidity_drop_pct(series, entry_ts):
    if not series:
        return None
    prior = []
    for row in series:
        if not isinstance(row, dict) or row.get("t") is None or row.get("liquidity_usd") is None:
            continue
        if row["t"] < entry_ts and float(row["liquidity_usd"]) > 0:
            prior.append(float(row["liquidity_usd"]))
    if len(prior) < 2:
        return None
    window = prior[-24:]
    peak = max(window)
    last = window[-1]
    if peak <= 0:
        return None
    return (peak - last) / peak * 100.0


def _signal_map(candidate):
    if candidate.get("signals") is not None:
        return dict(candidate["signals"]), candidate.get("signal_timing") or "later_snapshot"
    evidence = candidate.get("evidence")
    if not isinstance(evidence, dict):
        return {}, "unmeasured"
    measured = measure_entry_signals(evidence, now=candidate.get("evidence_now"))
    signals = {key: measured.get(key) for key in EVIDENCE_FEATURES}
    if candidate.get("evidence_at_entry") is True:
        timing = "at_entry"
    else:
        timing = candidate.get("signal_timing") or "later_snapshot"
    return signals, timing


def annotate_trade(trade, candidate, bars):
    features = {}
    timing = {}
    signals, signal_timing = _signal_map(candidate)
    for key in EVIDENCE_FEATURES:
        value = signals.get(key)
        spec = FEATURE_SPECS[key]
        if value is None or signal_timing == "unmeasured":
            features[key] = None
            timing[key] = "unmeasured"
        elif spec.get("snapshot_only"):
            features[key] = value
            timing[key] = "later_snapshot"
        else:
            features[key] = value
            timing[key] = signal_timing

    frac = trade.get("entry_frac_of_ath")
    features["entry_frac_of_ath"] = frac
    timing["entry_frac_of_ath"] = "at_entry" if frac is not None else "unmeasured"

    share = volume_top_share(bars, trade.get("entry_ts") or 0)
    features["volume_top_share"] = _round(share, 6) if share is not None else None
    timing["volume_top_share"] = "at_entry" if share is not None else "unmeasured"

    drop = liquidity_drop_pct(candidate.get("liquidity_bars"), trade.get("entry_ts") or 0)
    features["liquidity_drop_pct"] = _round(drop, 6) if drop is not None else None
    timing["liquidity_drop_pct"] = "at_entry" if drop is not None else "unmeasured"

    created = candidate.get("created_ts")
    entry_ts = trade.get("entry_ts")
    if created is not None and entry_ts is not None and float(entry_ts) >= float(created):
        features["pair_age_hours"] = _round((float(entry_ts) - float(created)) / 3600.0, 6)
        timing["pair_age_hours"] = "at_entry"
    else:
        features["pair_age_hours"] = None
        timing["pair_age_hours"] = "unmeasured"

    liq = candidate.get("liquidity_usd")
    mcap = candidate.get("market_cap_usd")
    if liq is not None and mcap not in (None, 0) and float(mcap) > 0 and float(liq) >= 0:
        features["snapshot_liq_to_mcap"] = _round(float(liq) / float(mcap), 6)
        timing["snapshot_liq_to_mcap"] = candidate.get("liquidity_timing") or "later_snapshot"
    else:
        features["snapshot_liq_to_mcap"] = None
        timing["snapshot_liq_to_mcap"] = "unmeasured"

    listed = candidate.get("listed_holder_pct_sum")
    features["snapshot_holder_pct_sum"] = listed if listed is not None else None
    timing["snapshot_holder_pct_sum"] = "later_snapshot" if listed is not None else "unmeasured"

    trade["features"] = features
    trade["feature_timing"] = timing
    return trade


def simulate_book(candidates, variant, paper):
    min_bars = int(paper.get("min_hourly_bars", 30))
    trades = []
    skipped = []
    prepared = []
    for candidate in candidates:
        bars = list(candidate.get("bars") or [])
        row = {
            "mint": candidate.get("mint"),
            "symbol": candidate.get("symbol"),
            "pool": candidate.get("pool"),
            "hourly_bars": len(bars),
            "history_error": candidate.get("history_error"),
            "source": candidate.get("source"),
            "chain_note": candidate.get("chain_note") or candidate.get("evidence_note"),
        }
        signals, signal_timing = _signal_map(candidate)
        if signals:
            row["signal_timing"] = signal_timing
            row["signals"] = {
                key: value for key, value in signals.items()
                if key in EVIDENCE_FEATURES and value is not None
            }
        if len(bars) < min_bars:
            row["skipped"] = f"fewer than {min_bars} hourly bars"
            skipped.append(row)
            continue
        produced = simulate(bars, variant, candidate, paper, seed_ath=candidate.get("seed_ath"))
        for trade in produced:
            annotate_trade(trade, candidate, bars)
        trades.extend(produced)
        row["trades"] = len(produced)
        prepared.append(row)
    return trades, prepared, skipped


def _fmt(value):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _closeness(value, spec):
    default = float(spec["default"])
    scale = abs(default) + 1.0
    if spec["op"] == ">":
        return (float(value) - default) / scale
    return (default - float(value)) / scale


def _measured_numbers(trade):
    numbers = {}
    for key in FEATURE_SPECS:
        value = (trade.get("features") or {}).get(key)
        if value is not None:
            numbers[key] = value
    return numbers


def finding_for_loss(trade):
    """One concrete reading for a losing trade. Missing features stay missing."""
    measured = []
    for key, spec in FEATURE_SPECS.items():
        value = (trade.get("features") or {}).get(key)
        timing = (trade.get("feature_timing") or {}).get(key) or "unmeasured"
        if value is None or timing == "unmeasured":
            continue
        measured.append((key, float(value), timing, spec, _closeness(value, spec)))
    numbers = _measured_numbers(trade)
    symbol = trade.get("symbol") or trade.get("mint")
    pnl = float(trade.get("pnl_usd") or 0)
    base = {
        "trade_id": trade.get("id"),
        "mint": trade.get("mint"),
        "symbol": trade.get("symbol"),
        "pnl_usd": _round(pnl),
        "exit_reason": trade.get("exit_reason"),
        "strategy_id": trade.get("strategy_id"),
        "standing": False,
        "numbers": numbers,
    }
    if not measured:
        base.update({
            "feature": None,
            "op": None,
            "value": None,
            "suggested_threshold": None,
            "timing": "unmeasured",
            "breached": False,
            "text": (
                f"{symbol} lost ${pnl:.4f} on {trade.get('strategy_id')} exit {trade.get('exit_reason')}. "
                "No holder, bundle, sniper, fresh-wallet, dev, wash, liquidity-path, volume, pair-age, "
                "or entry-fraction reading was available. Nothing was filled in."
            ),
        })
        return base
    breached = [row for row in measured if row[4] > 0]
    at_entry = [row for row in measured if row[2] == "at_entry"]
    pool = breached or at_entry or measured
    pool.sort(key=lambda row: row[4], reverse=True)
    key, value, timing, spec, _score = pool[0]
    readings = "; ".join(f"{FEATURE_SPECS[name]['label']} {_fmt(num)}" for name, num in numbers.items())
    screen = "crossed" if _score > 0 else "did not cross"
    base.update({
        "feature": key,
        "op": spec["op"],
        "value": value,
        "suggested_threshold": value,
        "timing": timing,
        "breached": _score > 0,
        "text": (
            f"{symbol} lost ${pnl:.4f} on {trade.get('strategy_id')} exit {trade.get('exit_reason')}. "
            f"Primary reading {spec['label']} = {_fmt(value)} ({screen} the screen {spec['op']} {_fmt(spec['default'])}, "
            f"timing {timing}). Readings: {readings}."
        ),
    })
    return base


def standing_bundle_finding():
    spec = FEATURE_SPECS["bundle_supply_pct"]
    return {
        "feature": "bundle_supply_pct",
        "op": spec["op"],
        "value": None,
        "suggested_threshold": spec["default"],
        "timing": None,
        "standing": True,
        "breached": False,
        "trade_id": None,
        "mint": None,
        "symbol": None,
        "pnl_usd": None,
        "numbers": {},
        "text": (
            "Owner rule: avoid bundled coins, meaning supply heavily concentrated in bundled or linked wallets. "
            f"The research screen starts at {spec['default']:g}% (the entry-gate sniper cap) and the cutoff is swept "
            "on the train split. The rule is kept only if that research calls it a good predictor and the held-out "
            "book is not worse."
        ),
    }


def _split_feature(trades, feature, op, threshold):
    flagged = []
    clean = []
    unmeasured = 0
    for trade in trades:
        value = (trade.get("features") or {}).get(feature)
        timing = (trade.get("feature_timing") or {}).get(feature) or "unmeasured"
        if value is None or timing == "unmeasured":
            unmeasured += 1
            continue
        number = float(value)
        hit = number > threshold if op == ">" else number < threshold
        (flagged if hit else clean).append(trade)
    return flagged, clean, unmeasured


def _group_stats(trades):
    pnls = [float(trade["pnl_usd"]) for trade in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    return {
        "n": len(pnls),
        "win_rate": _round(len(wins) / len(pnls), 4) if pnls else None,
        "expectancy_usd": _round(_mean(pnls), 4) if pnls else None,
        "net_usd": _round(sum(pnls), 4) if pnls else 0.0,
        "wins": len(wins),
        "losses": len(pnls) - len(wins),
    }


def _timing_of(trades, feature):
    seen = set()
    for trade in trades:
        value = (trade.get("features") or {}).get(feature)
        timing = (trade.get("feature_timing") or {}).get(feature) or "unmeasured"
        if value is None or timing == "unmeasured":
            continue
        seen.add(timing)
    if not seen:
        return "unmeasured"
    if seen == {"at_entry"}:
        return "at_entry"
    return "later_snapshot"


def _cutoffs(values, spec, suggestions):
    cuts = set()
    for suggestion in suggestions:
        if suggestion is not None:
            cuts.add(float(suggestion))
    cuts.add(float(spec["default"]))
    ordered = sorted(float(value) for value in values)
    if ordered:
        for quantile in (0.1, 0.25, 0.5, 0.75, 0.9):
            index = min(len(ordered) - 1, int(quantile * (len(ordered) - 1)))
            cuts.add(ordered[index])
        unique = sorted(set(ordered))
        for left, right in zip(unique, unique[1:]):
            cuts.add((left + right) / 2.0)
        for suggestion in suggestions:
            if suggestion is None:
                continue
            if spec["op"] == ">":
                below = [value for value in unique if value < float(suggestion)]
                if below:
                    cuts.add(below[-1])
            else:
                above = [value for value in unique if value > float(suggestion)]
                if above:
                    cuts.add(above[0])
    floor = spec.get("floor")
    ceiling = spec.get("ceiling")
    kept = []
    for cutoff in cuts:
        if floor is not None and cutoff < float(floor) - 1e-12:
            continue
        if ceiling is not None and cutoff > float(ceiling) + 1e-12:
            continue
        kept.append(round(cutoff, 6))
    return sorted(set(kept))


def _side_row(trades, feature, spec, cutoff):
    flagged, clean, unmeasured = _split_feature(trades, feature, spec["op"], cutoff)
    flagged_stats = _group_stats(flagged)
    clean_stats = _group_stats(clean)
    flagged_pnls = [float(trade["pnl_usd"]) for trade in flagged]
    clean_pnls = [float(trade["pnl_usd"]) for trade in clean]
    winners_removed = [trade for trade in flagged if trade["pnl_usd"] > 0]
    losers_removed = [trade for trade in flagged if trade["pnl_usd"] < 0]
    return {
        "threshold": cutoff,
        "op": spec["op"],
        "n_flagged": flagged_stats["n"],
        "n_clean": clean_stats["n"],
        "unmeasured": unmeasured,
        "win_rate_flagged": flagged_stats["win_rate"],
        "win_rate_clean": clean_stats["win_rate"],
        "expectancy_flagged": flagged_stats["expectancy_usd"],
        "expectancy_clean": clean_stats["expectancy_usd"],
        "winners_removed": len(winners_removed),
        "winners_removed_pnl": _round(sum(float(trade["pnl_usd"]) for trade in winners_removed)),
        "losers_removed": len(losers_removed),
        "losers_removed_pnl": _round(sum(float(trade["pnl_usd"]) for trade in losers_removed)),
        "p_one_sided": _round(welch_p_flagged_worse(flagged_pnls, clean_pnls), 6),
        "p_method": "one-sided normal approximation of Welch's t",
    }


def research_feature(feature, train_trades, suggestions, min_side):
    spec = FEATURE_SPECS[feature]
    timing = _timing_of(train_trades, feature)
    known = []
    for trade in train_trades:
        value = (trade.get("features") or {}).get(feature)
        trade_timing = (trade.get("feature_timing") or {}).get(feature) or "unmeasured"
        if value is None or trade_timing == "unmeasured":
            continue
        known.append(float(value))
    note = {
        "feature": feature,
        "label": spec["label"],
        "op": spec["op"],
        "timing": timing,
        "standing": bool(spec.get("standing")),
        "train_trades": len(train_trades),
        "measured_trades": len(known),
        "unmeasured_trades": len(train_trades) - len(known),
        "min_side": min_side,
        "threshold": None,
        "verdict": "inconclusive",
        "sweep": [],
        "flagged": None,
        "clean": None,
        "winners_removed": None,
        "winners_removed_pnl": None,
        "losers_removed": None,
        "losers_removed_pnl": None,
        "p_one_sided": None,
        "examples": [],
    }
    if timing == "unmeasured" or not known:
        note["text"] = (
            f"{spec['label']} was not measured on this train split "
            f"({note['unmeasured_trades']} of {len(train_trades)} trades). "
            "The candidate rule was not added. No value was invented."
        )
        if feature == "bundle_supply_pct":
            note["text"] += (
                " The avoid-bundled-coins rule needs acquire-slot or linked-funder supply, "
                "and this history does not have it."
            )
        return note

    ordered_known = sorted(known)
    note["value_min"] = ordered_known[0]
    note["value_max"] = ordered_known[-1]
    note["value_median"] = ordered_known[len(ordered_known) // 2]
    cutoffs = _cutoffs(known, spec, suggestions)
    rows = [_side_row(train_trades, feature, spec, cutoff) for cutoff in cutoffs]
    note["sweep"] = rows[:16]
    eligible = [
        row for row in rows
        if row["n_flagged"] >= min_side and row["n_clean"] >= min_side
        and row["expectancy_flagged"] is not None and row["expectancy_clean"] is not None
        and row["expectancy_flagged"] < row["expectancy_clean"] - 1e-9
    ]

    def rank(row):
        return (
            row["expectancy_clean"],
            row["expectancy_clean"] - row["expectancy_flagged"],
            -row["winners_removed"],
        )

    chosen = max(eligible, key=rank) if eligible else None
    reference = chosen
    if reference is None and rows:
        default_rows = [row for row in rows if abs(row["threshold"] - float(spec["default"])) < 1e-6]
        reference = default_rows[0] if default_rows else rows[0]
    if reference is not None:
        note.update({
            "threshold": reference["threshold"],
            "flagged": {
                "n": reference["n_flagged"],
                "win_rate": reference["win_rate_flagged"],
                "expectancy_usd": reference["expectancy_flagged"],
            },
            "clean": {
                "n": reference["n_clean"],
                "win_rate": reference["win_rate_clean"],
                "expectancy_usd": reference["expectancy_clean"],
            },
            "winners_removed": reference["winners_removed"],
            "winners_removed_pnl": reference["winners_removed_pnl"],
            "losers_removed": reference["losers_removed"],
            "losers_removed_pnl": reference["losers_removed_pnl"],
            "p_one_sided": reference["p_one_sided"],
        })
    large = (
        reference is not None
        and reference["n_flagged"] >= min_side
        and reference["n_clean"] >= min_side
    )
    separates = (
        large
        and reference["expectancy_flagged"] is not None
        and reference["expectancy_clean"] is not None
        and reference["expectancy_flagged"] < reference["expectancy_clean"] - 1e-9
    )
    wrong_way = (
        large
        and reference["expectancy_flagged"] is not None
        and reference["expectancy_clean"] is not None
        and reference["expectancy_flagged"] >= reference["expectancy_clean"] - 1e-9
    )
    significant = reference is not None and reference["p_one_sided"] is not None and reference["p_one_sided"] <= P_MAX
    if separates and significant and timing == "at_entry" and chosen is not None:
        note["verdict"] = "good predictor"
        note["threshold"] = chosen["threshold"]
    elif wrong_way and timing != "unmeasured":
        note["verdict"] = "bad predictor"
    else:
        note["verdict"] = "inconclusive"

    losses = [trade for trade in train_trades if trade["pnl_usd"] < 0]
    examples = []
    for trade in losses:
        value = (trade.get("features") or {}).get(feature)
        if value is None:
            continue
        examples.append({
            "symbol": trade.get("symbol"),
            "mint": trade.get("mint"),
            "pnl_usd": _round(trade["pnl_usd"]),
            "value": value,
            "exit_reason": trade.get("exit_reason"),
        })
        if len(examples) >= 6:
            break
    note["examples"] = examples
    note["text"] = _note_text(note, spec)
    return note


def _timing_sentence(note):
    if note["timing"] == "later_snapshot":
        return (
            " This reading is a later snapshot, not the book at the historical entry, "
            "so it cannot become an entry rule."
        )
    if note["timing"] != "at_entry":
        return " Timing is not at-entry, so the rule was not added."
    return ""


def _range_sentence(note):
    if note.get("value_min") is None:
        return ""
    return (
        f" Measured values ranged from {_fmt(note['value_min'])} to {_fmt(note['value_max'])} "
        f"(median {_fmt(note['value_median'])}, n={note['measured_trades']})."
    )


def _note_text(note, spec):
    if note["flagged"] is None or note["clean"] is None:
        return note.get("text") or f"{spec['label']} could not be compared."
    flagged = note["flagged"]
    clean = note["clean"]
    timing_sentence = _timing_sentence(note)
    if flagged["n"] == 0 or clean["n"] == 0:
        empty = "flagged" if flagged["n"] == 0 else "unflagged"
        return (
            f"{spec['label']}: no train trade fell on the {empty} side of {spec['op']} {note['threshold']:g}."
            f"{_range_sentence(note)} "
            f"With-flag n={flagged['n']}, without-flag n={clean['n']}, "
            f"unmeasured excluded {note['unmeasured_trades']}. "
            f"Verdict: {note['verdict']}.{timing_sentence}"
        )
    p_text = "n/a" if note["p_one_sided"] is None else f"{note['p_one_sided']:.4f}"
    winners = note["winners_removed"]
    winner_pnl = note["winners_removed_pnl"]
    return (
        f"{spec['label']}: train trades {spec['op']} {note['threshold']:g} "
        f"won {_fmt(flagged['win_rate'])} with expectancy {_fmt(flagged['expectancy_usd'])} "
        f"(n={flagged['n']}); trades on the other side won {_fmt(clean['win_rate'])} "
        f"with expectancy {_fmt(clean['expectancy_usd'])} (n={clean['n']})."
        f"{_range_sentence(note)} "
        f"Unmeasured trades excluded from both sides: {note['unmeasured_trades']}. "
        f"One-sided Welch p≈{p_text} (normal approximation). "
        f"Winners the rule would also remove on the train split: {winners} "
        f"(${_fmt(winner_pnl)}). Losers removed: {note['losers_removed']}. "
        f"Verdict: {note['verdict']}.{timing_sentence}"
    )


def rule_from_note(note):
    spec = FEATURE_SPECS[note["feature"]]
    threshold = float(note["threshold"])
    op_name = "gt" if spec["op"] == ">" else "lt"
    threshold_token = f"{threshold:g}".replace(".", "p").replace("-", "m")
    return {
        "id": f"{note['feature']}_{op_name}_{threshold_token}",
        "feature": note["feature"],
        "op": spec["op"],
        "threshold": threshold,
        "timing": "at_entry",
        "rule": spec["rule"].format(threshold=threshold),
        "source": "iterative backtest",
        "research_verdict": note["verdict"],
        "p_one_sided": note.get("p_one_sided"),
        "winners_removed_train": note.get("winners_removed"),
    }


def rule_matches(rule, trade):
    feature = rule["feature"]
    timing = (trade.get("feature_timing") or {}).get(feature) or "unmeasured"
    if timing != "at_entry":
        return False
    value = (trade.get("features") or {}).get(feature)
    if value is None:
        return False
    number = float(value)
    if rule["op"] == ">":
        return number > float(rule["threshold"])
    if rule["op"] == "<":
        return number < float(rule["threshold"])
    raise ValueError(f"unsupported op {rule['op']}")


def apply_rules(trades, rules):
    return [trade for trade in trades if not any(rule_matches(rule, trade) for rule in rules)]


def evaluate_oos(rule, oos_trades, min_oos_trades, min_remaining_fraction):
    before = summarize_trades(oos_trades)
    removed = [trade for trade in oos_trades if rule_matches(rule, trade)]
    kept = [trade for trade in oos_trades if not rule_matches(rule, trade)]
    after = summarize_trades(kept)
    winners_removed = [trade for trade in removed if trade["pnl_usd"] > 0]
    info = {
        "before": before,
        "after": after,
        "removed": len(removed),
        "winners_removed": len(winners_removed),
    }
    if before["trades"] < min_oos_trades:
        return False, (
            f"held-out sample has {before['trades']} trades, under the standing minimum of {min_oos_trades}"
        ), info
    if not removed:
        return False, (
            "the flag did not occur on any held-out trade, so the out-of-sample check cannot confirm it"
        ), info
    relative = math.ceil(before["trades"] * float(min_remaining_fraction) - 1e-12)
    floor = max(int(min_oos_trades), relative)
    if after["trades"] < floor:
        return False, (
            f"rule cuts held-out trades from {before['trades']} to {after['trades']} "
            f"(floor {floor}; near-zero books are rejected)"
        ), info
    if after["expectancy_usd"] is None or before["expectancy_usd"] is None:
        return False, "held-out expectancy is not measurable", info
    if after["expectancy_usd"] + 1e-9 < before["expectancy_usd"]:
        return False, (
            f"held-out expectancy falls from {before['expectancy_usd']} to {after['expectancy_usd']}; "
            "out-of-sample rules are never loosened, so a rule that hurts the held-out book is rejected"
        ), info
    return True, (
        f"held-out expectancy {before['expectancy_usd']} -> {after['expectancy_usd']}, "
        f"trades {before['trades']} -> {after['trades']}, winners removed {len(winners_removed)}"
    ), info


def _research_plan(losses, accepted, blocked):
    plan = []
    if "bundle_supply_pct" not in accepted and "bundle_supply_pct" not in blocked:
        plan.append("bundle_supply_pct")
    seen = set(plan)
    for trade in losses:
        for feature, spec in FEATURE_SPECS.items():
            if feature in seen or feature in accepted or feature in blocked:
                continue
            value = (trade.get("features") or {}).get(feature)
            timing = (trade.get("feature_timing") or {}).get(feature) or "unmeasured"
            if value is None or timing == "unmeasured":
                continue
            if timing == "at_entry" or _closeness(value, spec) > 0:
                plan.append(feature)
                seen.add(feature)
    return plan


def _suggestions(feature, losses):
    spec = FEATURE_SPECS[feature]
    values = [float(spec["default"])]
    for trade in losses:
        value = (trade.get("features") or {}).get(feature)
        timing = (trade.get("feature_timing") or {}).get(feature) or "unmeasured"
        if value is None or timing == "unmeasured":
            continue
        values.append(float(value))
    return values


def run_iterative_backtest(
    candidates,
    variant,
    paper,
    *,
    max_iterations=8,
    min_side=5,
    min_oos_trades=None,
    min_remaining_fraction=0.25,
):
    """Learn filters on train trades. Keep a filter only when held-out expectancy does not fall."""
    if min_oos_trades is None:
        min_oos_trades = int(paper.get("min_oos_trades", 5))
    max_iterations = int(max_iterations)
    min_side = int(min_side)
    base_trades, prepared, skipped = simulate_book(candidates, variant, paper)
    rules = []
    accepted = set()
    blocked = set()
    rejected = []
    notes_all = []

    def split(active):
        train = [trade for trade in active if trade.get("sample") != "out_of_sample"]
        oos = [trade for trade in active if trade.get("sample") == "out_of_sample"]
        return train, oos

    baseline_trades = apply_rules(base_trades, rules)
    base_train, base_oos = split(baseline_trades)
    iterations = [{
        "iteration": 0,
        "rules_added": [],
        "rules_rejected": [],
        "findings": [],
        "research_notes": [],
        "train": summarize_trades(base_train),
        "out_of_sample": summarize_trades(base_oos),
        "active_rules": [],
    }]
    stopped = "max_iterations"
    for iteration in range(1, max_iterations + 1):
        active = apply_rules(base_trades, rules)
        train, oos = split(active)
        before_train = summarize_trades(train)
        before_oos = summarize_trades(oos)
        losses = [trade for trade in train if trade["pnl_usd"] < 0]
        plan = _research_plan(losses, accepted, blocked)
        findings = [finding_for_loss(trade) for trade in losses]
        if "bundle_supply_pct" in plan:
            findings.append(standing_bundle_finding())
        row = {
            "iteration": iteration,
            "rules_added": [],
            "rules_rejected": [],
            "findings": findings,
            "research_notes": [],
            "before_train": before_train,
            "before_out_of_sample": before_oos,
            "active_rules": [rule["id"] for rule in rules],
        }
        if not plan:
            row["train"] = before_train
            row["out_of_sample"] = before_oos
            iterations.append(row)
            stopped = "no new findings"
            break
        candidates_for_rules = []
        for feature in plan:
            note = research_feature(feature, train, _suggestions(feature, losses), min_side)
            row["research_notes"].append(note)
            notes_all.append({"iteration": iteration, **note})
            if note["verdict"] != "good predictor" or note["timing"] != "at_entry" or note["threshold"] is None:
                blocked.add(feature)
                rejected.append({
                    "id": feature,
                    "feature": feature,
                    "rule": FEATURE_SPECS[feature]["rule"].format(threshold=note["threshold"] or FEATURE_SPECS[feature]["default"]),
                    "stage": "research",
                    "verdict": note["verdict"],
                    "reason": note["text"],
                    "iteration": iteration,
                })
                row["rules_rejected"].append(rejected[-1])
                continue
            rule = rule_from_note(note)
            kept_train = [trade for trade in train if not rule_matches(rule, trade)]
            if len(kept_train) < min_side:
                blocked.add(feature)
                rejected.append({
                    "id": rule["id"],
                    "feature": feature,
                    "rule": rule["rule"],
                    "stage": "train",
                    "verdict": note["verdict"],
                    "reason": f"rule leaves {len(kept_train)} train trades, under the floor of {min_side}",
                    "iteration": iteration,
                })
                row["rules_rejected"].append(rejected[-1])
                continue
            lift = (note["clean"]["expectancy_usd"] or 0) - (before_train["expectancy_usd"] or 0)
            candidates_for_rules.append((lift, rule, note))
        candidates_for_rules.sort(key=lambda item: item[0], reverse=True)
        added_any = False
        running = list(rules)
        for _lift, rule, note in candidates_for_rules:
            current_oos = apply_rules(base_trades, running)
            current_oos = [trade for trade in current_oos if trade.get("sample") == "out_of_sample"]
            keep, reason, info = evaluate_oos(rule, current_oos, min_oos_trades, min_remaining_fraction)
            record = {
                "id": rule["id"],
                "feature": rule["feature"],
                "rule": rule["rule"],
                "threshold": rule["threshold"],
                "op": rule["op"],
                "stage": "out_of_sample",
                "verdict": note["verdict"],
                "reason": reason,
                "oos": info,
                "iteration": iteration,
            }
            if keep:
                running.append(rule)
                rules.append(rule)
                accepted.add(rule["feature"])
                blocked.discard(rule["feature"])
                rule["oos_reason"] = reason
                row["rules_added"].append(dict(rule))
                added_any = True
            else:
                blocked.add(rule["feature"])
                rejected.append(record)
                row["rules_rejected"].append(record)
        after = apply_rules(base_trades, rules)
        after_train, after_oos = split(after)
        row["train"] = summarize_trades(after_train)
        row["out_of_sample"] = summarize_trades(after_oos)
        row["active_rules"] = [rule["id"] for rule in rules]
        iterations.append(row)
        if not added_any:
            stopped = "no validated rules"
            break
        blocked.clear()
    else:
        stopped = "max_iterations"

    coverage = {}
    for feature in FEATURE_SPECS:
        measured = 0
        timings = set()
        for trade in base_trades:
            value = (trade.get("features") or {}).get(feature)
            timing = (trade.get("feature_timing") or {}).get(feature) or "unmeasured"
            if value is None or timing == "unmeasured":
                continue
            measured += 1
            timings.add(timing)
        coverage[feature] = {"measured_trades": measured, "timings": sorted(timings)}

    train0 = iterations[0]["train"]
    oos0 = iterations[0]["out_of_sample"]
    thin = []
    tradable = [row for row in prepared if not row.get("skipped")]
    min_bars = int(paper.get("min_hourly_bars", 30))
    if len(tradable) < 5:
        thin.append(f"Only {len(tradable)} coins had at least {min_bars} hourly bars.")
    if train0["trades"] < min_side:
        thin.append(f"Train trades are {train0['trades']}, under the research minimum of {min_side} per side.")
    if oos0["trades"] < min_oos_trades:
        thin.append(
            f"Held-out trades are {oos0['trades']}, under the standing minimum of {min_oos_trades}. "
            "A new rule cannot be confirmed out of sample on this history."
        )
    data_notes = [
        "Research uses every train trade, wins and losses. The held-out split is not read until a rule has already been called a good predictor.",
        "Each coin's latest oos_fraction of hourly bars is the held-out split, the same cut the existing dip simulator uses. Rules are never relaxed to chase that split.",
        "Liquidity drop along the path is measured only from a real liquidity_bars series. A single liquidity or market-cap snapshot is not an entry-time drop.",
        "Bundle, sniper, fresh-wallet, wash, holder, and dev readings become entry rules only when they were knowable at entry. A later chain snapshot is reported and is not promoted.",
        "Missing readings stay missing. Trades without a reading are not treated as clean and are not treated as flagged.",
    ]
    last = iterations[-1]
    return {
        "label": "PAPER / SIMULATED",
        "disclaimer": DISCLAIMER,
        "generated": datetime.now(timezone.utc).isoformat(),
        "strategy_id": variant.get("id"),
        "strategy_name": variant.get("name"),
        "max_iterations": max_iterations,
        "min_side": min_side,
        "min_oos_trades": min_oos_trades,
        "min_remaining_fraction": min_remaining_fraction,
        "stopped_because": stopped,
        "split": (
            "Train is the earlier portion of each pool's hourly bars. "
            "Out of sample is the latest oos_fraction of those bars. "
            "A rule is learned only on train trades and kept only when held-out expectancy does not fall "
            "and held-out trade count stays above the floor."
        ),
        "final_rules": rules,
        "rejected_rules": rejected,
        "iterations": iterations,
        "before": {"train": train0, "out_of_sample": oos0},
        "after": {"train": last["train"], "out_of_sample": last["out_of_sample"]},
        "coverage": coverage,
        "candidates": prepared,
        "skipped": skipped,
        "data_notes": data_notes,
        "thin_data": bool(thin),
        "thin_data_reason": " ".join(thin) if thin else "",
        "research_notes": notes_all,
    }


def _cell(value):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _metric_table(iterations, key, title):
    header = (
        f"| Iter | Rules added | Trades | Win rate | Avg win | Avg loss | Expectancy | PnL | Max DD |\n"
        f"| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    lines = [f"### {title}", "", header]
    for row in iterations:
        stats = row.get(key) or {}
        added = ", ".join(rule.get("id") or rule.get("rule", "") for rule in row.get("rules_added") or []) or "—"
        win_rate = stats.get("win_rate")
        win_text = "—" if win_rate is None else f"{win_rate * 100:.2f}%"
        lines.append(
            "| {iter} | {added} | {trades} | {win} | {aw} | {al} | {exp} | {pnl} | {dd} |".format(
                iter=row.get("iteration"),
                added=added.replace("|", "/"),
                trades=_cell(stats.get("trades")),
                win=win_text,
                aw=_cell(stats.get("avg_win_usd")),
                al=_cell(stats.get("avg_loss_usd")),
                exp=_cell(stats.get("expectancy_usd")),
                pnl=_cell(stats.get("pnl_usd")),
                dd=_cell(stats.get("max_drawdown_usd")),
            )
        )
    return "\n".join(lines)


def render_markdown(report):
    lines = [
        "# Iterative backtest",
        "",
        f"**{report.get('disclaimer') or DISCLAIMER}**",
        "",
        "Backtester only. Live entry gates, `config.json`, and forward paper entries are unchanged.",
        "",
        report.get("split") or "",
        "",
        f"Strategy `{report.get('strategy_id') or '—'}`. Stopped because: {report.get('stopped_because')}.",
        "",
    ]
    if report.get("thin_data"):
        lines += ["## Thin history", "", report.get("thin_data_reason") or "The historical sample is too thin to confirm a rule.", ""]
    lines += ["## Data notes", ""]
    for note in report.get("data_notes") or []:
        lines.append(f"- {note}")
    lines += ["", "## Final rules", ""]
    final_rules = report.get("final_rules") or []
    if not final_rules:
        lines.append("No rule was kept.")
    for rule in final_rules:
        lines.append(f"- `{rule.get('id')}` — {rule.get('rule')}")
    lines += ["", "## Rejected rules", ""]
    rejected = report.get("rejected_rules") or []
    if not rejected:
        lines.append("None.")
    for rule in rejected:
        lines.append(f"- `{rule.get('id')}` ({rule.get('stage')}, {rule.get('verdict')}): {rule.get('reason')}")
    before = report.get("before") or {}
    after = report.get("after") or {}
    lines += [
        "",
        "## Before vs after",
        "",
        f"- Train trades { _cell((before.get('train') or {}).get('trades')) } -> { _cell((after.get('train') or {}).get('trades')) }, "
        f"expectancy { _cell((before.get('train') or {}).get('expectancy_usd')) } -> { _cell((after.get('train') or {}).get('expectancy_usd')) }, "
        f"PnL { _cell((before.get('train') or {}).get('pnl_usd')) } -> { _cell((after.get('train') or {}).get('pnl_usd')) }.",
        f"- Out-of-sample trades { _cell((before.get('out_of_sample') or {}).get('trades')) } -> { _cell((after.get('out_of_sample') or {}).get('trades')) }, "
        f"expectancy { _cell((before.get('out_of_sample') or {}).get('expectancy_usd')) } -> { _cell((after.get('out_of_sample') or {}).get('expectancy_usd')) }, "
        f"PnL { _cell((before.get('out_of_sample') or {}).get('pnl_usd')) } -> { _cell((after.get('out_of_sample') or {}).get('pnl_usd')) }.",
        "",
        "## Iterations",
        "",
        _metric_table(report.get("iterations") or [], "train", "Train"),
        "",
        _metric_table(report.get("iterations") or [], "out_of_sample", "Out of sample"),
        "",
        "## Research notes",
        "",
    ]
    notes = report.get("research_notes") or []
    if not notes:
        lines.append("No finding was researched.")
    for note in notes:
        lines.append(f"### Iteration {note.get('iteration')} — {note.get('feature')} — {note.get('verdict')}")
        lines.append("")
        lines.append(note.get("text") or "")
        lines.append("")
    lines += ["## Coverage", ""]
    for feature, row in (report.get("coverage") or {}).items():
        lines.append(
            f"- `{feature}`: {row.get('measured_trades')} measured trades, timings {', '.join(row.get('timings') or []) or 'unmeasured'}"
        )
    if report.get("skipped"):
        lines += ["", "## Skipped coins", ""]
        for row in report["skipped"]:
            lines.append(
                f"- {row.get('symbol') or row.get('mint')}: {row.get('skipped') or row.get('history_error') or 'skipped'}"
            )
    lines += ["", "Simulated fills only. This report does not place orders.", ""]
    return "\n".join(lines).rstrip() + "\n"


def write_report(report, json_path, md_path):
    json_path = Path(json_path)
    md_path = Path(md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    tmp.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, json_path)
    md_tmp = md_path.with_suffix(md_path.suffix + ".tmp")
    md_tmp.write_text(render_markdown(report))
    os.replace(md_tmp, md_path)


def champion_variant(lessons):
    for row in (lessons or {}).get("variants") or []:
        params = row.get("params") or {}
        if row.get("status") == "champion" and {"zone_low", "zone_high", "stop", "target", "hold_bars"} <= set(params):
            return {
                "id": row.get("id"),
                "zone_low": params["zone_low"],
                "zone_high": params["zone_high"],
                "stop": params["stop"],
                "target": params["target"],
                "hold_bars": params["hold_bars"],
                "name": row.get("name") or row.get("id"),
            }
    for variant in variant_catalog():
        if variant["id"] == "dip_20_40_stop8_tp15_hold8":
            return variant
    return variant_catalog()[0]


def indexed_candidates(research, lessons):
    """Coins already stored by the floor. Does not invent candles or holders."""
    rows = {}

    def add(row, source):
        if not isinstance(row, dict):
            return
        mint = row.get("mint")
        pool = row.get("pool")
        if not mint or not pool or mint in rows:
            return
        safety = row.get("safety") if isinstance(row.get("safety"), dict) else {}
        humans = safety.get("humans") if isinstance(safety.get("humans"), list) else []
        listed = []
        kept_humans = []
        for human in humans:
            if not isinstance(human, dict) or not human.get("owner"):
                continue
            kept_humans.append({
                "owner": human.get("owner"),
                "token_account": human.get("token_account"),
                "pct": human.get("pct"),
            })
            if isinstance(human.get("pct"), (int, float)):
                listed.append(float(human["pct"]))
        rows[mint] = {
            "mint": mint,
            "symbol": row.get("symbol"),
            "name": row.get("name") or row.get("symbol"),
            "pool": pool,
            "liquidity_usd": row.get("liquidity_usd"),
            "market_cap_usd": row.get("market_cap_usd"),
            "created_ts": row.get("created_ts"),
            "listed_holder_pct_sum": round(sum(listed), 6) if listed else None,
            "top10_snapshot": safety.get("top10_measured_pct"),
            "humans": kept_humans,
            "source": source,
            "liquidity_timing": "later_snapshot" if row.get("liquidity_usd") is not None else "unmeasured",
        }

    research = research or {}
    lessons = lessons or {}
    for row in research.get("watchlist") or []:
        add(row, "research.watchlist")
    for row in research.get("rejected_review") or []:
        add(row, "research.rejected_review")
    for variant in lessons.get("variants") or []:
        for pool in variant.get("pools") or []:
            add(pool, "lessons.pools")
    return list(rows.values())


def _seed_ath(daily_bars, hourly_bars):
    if not hourly_bars or not daily_bars:
        return None
    first = hourly_bars[0]["t"]
    prior = [bar["h"] for bar in daily_bars if bar.get("t") is not None and bar["t"] < first]
    return max(prior) if prior else None


def attach_history(candidates, market, config, *, chain=True):
    """Fill candles and, when asked, a present-time holder snapshot. Failures stay errors."""
    from sources import SourceError

    limits = (config or {}).get("limits") or {}
    notes = []
    by_mint = {}
    mints = [row["mint"] for row in candidates if row.get("mint")]
    if market is not None and mints:
        try:
            found, errors = market.dexscreener_pairs(mints)
        except (SourceError, OSError, TypeError, ValueError) as exc:
            found, errors = [], [str(exc)]
        for pair in found or []:
            if isinstance(pair, dict) and pair.get("mint"):
                by_mint.setdefault(pair["mint"], []).append(pair)
        if errors:
            notes.append("DexScreener pair lookup errors: " + "; ".join(str(err) for err in errors)[:500])
    prepared = []
    for raw in candidates:
        cand = dict(raw)
        match = next((pair for pair in by_mint.get(cand["mint"], []) if pair.get("pool") == cand.get("pool")), None)
        if match:
            if cand.get("created_ts") is None and match.get("created_ts"):
                cand["created_ts"] = match["created_ts"]
                cand["created_ts_source"] = "dexscreener pairCreatedAt"
            if cand.get("liquidity_usd") is None and match.get("liquidity_usd") is not None:
                cand["liquidity_usd"] = match["liquidity_usd"]
                cand["liquidity_timing"] = "later_snapshot"
            if cand.get("market_cap_usd") is None and match.get("market_cap_usd") is not None:
                cand["market_cap_usd"] = match["market_cap_usd"]
            if not cand.get("symbol") and match.get("symbol"):
                cand["symbol"] = match["symbol"]
            if not cand.get("name") and match.get("name"):
                cand["name"] = match["name"]
        if market is not None and cand.get("pool"):
            print(f"ohlcv {cand.get('symbol') or cand['mint']}", flush=True)
            try:
                hourly = market.gecko_ohlcv(cand["pool"], "hour", limits.get("hourly_bars", 168))
                daily = market.gecko_ohlcv(cand["pool"], "day", limits.get("daily_bars", 90))
                cand["bars"] = hourly.get("bars") or []
                cand["seed_ath"] = _seed_ath(daily.get("bars") or [], cand["bars"])
                cand["history_source"] = "geckoterminal hourly and daily ohlcv"
            except (SourceError, OSError, TypeError, ValueError, KeyError) as exc:
                cand["bars"] = []
                cand["history_error"] = str(exc)[:300]
                notes.append(f"{cand.get('symbol') or cand['mint']}: history failed: {cand['history_error']}")
        prepared.append(cand)

    min_bars = int(((config or {}).get("paper") or {}).get("min_hourly_bars", 30))
    if chain and market is not None:
        for cand in prepared:
            if len(cand.get("bars") or []) < min_bars:
                continue
            humans = cand.get("humans") or []
            if not humans:
                cand["chain_note"] = "no stored holder accounts; bundle, fresh-wallet, and sniper share were not read"
                continue
            print(f"holders {cand.get('symbol') or cand['mint']}", flush=True)
            try:
                evidence = gather_entry_evidence(
                    {"mint": cand["mint"], "pool": cand.get("pool"), "created_ts": cand.get("created_ts")},
                    market,
                    {"humans": humans[:5], "status": "pass", "top10_measured_pct": cand.get("top10_snapshot")},
                    config,
                    now=time.time(),
                )
            except (SourceError, OSError, TypeError, ValueError, KeyError) as exc:
                cand["chain_note"] = "holder snapshot failed: " + str(exc)[:240]
                notes.append(f"{cand.get('symbol') or cand['mint']}: {cand['chain_note']}")
                continue
            measured = measure_entry_signals(evidence, config=config, now=evidence.get("now"))
            cand["signals"] = {key: measured.get(key) for key in EVIDENCE_FEATURES}
            cand["signal_timing"] = "later_snapshot"
            cand["evidence_note"] = (
                "Holder, bundle, sniper, fresh-wallet, wash, and dev readings are a chain snapshot "
                "taken when this backtest ran, not the holder set at the historical entry. "
                "They are researched and are not eligible to become entry rules."
            )
            if evidence.get("holder_read_error"):
                cand["chain_note"] = str(evidence.get("holder_read_error"))[:240]
                notes.append(f"{cand.get('symbol') or cand['mint']}: holder read incomplete: {cand['chain_note']}")
    return prepared, notes


def _print_summary(report):
    before = report["before"]["out_of_sample"]
    after = report["after"]["out_of_sample"]
    print(
        f"stopped={report['stopped_because']} rules={len(report['final_rules'])} "
        f"rejected={len(report['rejected_rules'])} "
        f"oos_trades {before['trades']}->{after['trades']} "
        f"oos_expectancy {before['expectancy_usd']}->{after['expectancy_usd']}"
    )
    if report.get("thin_data"):
        print("thin_data:", report.get("thin_data_reason"))
    for rule in report["final_rules"]:
        print("kept:", rule["rule"])
    for note in report.get("research_notes") or []:
        if note.get("feature") == "bundle_supply_pct":
            print("bundle verdict:", note.get("verdict"))
            print(note.get("text"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Iterative paper backtest. Does not change live entry rules.")
    parser.add_argument("--max-iterations", type=int, default=8)
    parser.add_argument("--min-side", type=int, default=5)
    parser.add_argument("--min-remaining-fraction", type=float, default=0.25)
    parser.add_argument("--out", default="data/backtest_iterations.json")
    parser.add_argument("--md", default="data/backtest_iterations.md")
    parser.add_argument("--candidates", help="JSON file of candidates that already include bars. Skips the network.")
    parser.add_argument("--no-fetch", action="store_true", help="Do not request candles or chain data.")
    parser.add_argument("--no-chain", action="store_true", help="Fetch candles but skip the present-time holder snapshot.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    config = json.loads((root / "config.json").read_text())
    lessons_path = root / "data" / "lessons.json"
    research_path = root / "data" / "research.json"
    lessons = json.loads(lessons_path.read_text()) if lessons_path.exists() else {}
    research = json.loads(research_path.read_text()) if research_path.exists() else {}
    notes = []
    if args.candidates:
        payload = json.loads(Path(args.candidates).read_text())
        candidates = payload["candidates"] if isinstance(payload, dict) and "candidates" in payload else payload
        notes.append(f"Candidates loaded from {args.candidates}. No network fetch.")
    else:
        candidates = indexed_candidates(research, lessons)
        notes.append(f"Indexed {len(candidates)} stored coins from research.json and lessons pools.")
        if args.no_fetch:
            notes.append("Network fetch disabled. Coins without stored hourly bars were not simulated.")
        else:
            from sources import MarketData

            market = MarketData(config, root / "data" / "cache" / "http.json")
            candidates, fetch_notes = attach_history(candidates, market, config, chain=not args.no_chain)
            notes.extend(fetch_notes)
    variant = champion_variant(lessons)
    paper = dict(config.get("paper") or {})
    report = run_iterative_backtest(
        candidates,
        variant,
        paper,
        max_iterations=args.max_iterations,
        min_side=args.min_side,
        min_remaining_fraction=args.min_remaining_fraction,
    )
    report["data_notes"] = notes + report["data_notes"]
    out = root / args.out if not Path(args.out).is_absolute() else Path(args.out)
    md = root / args.md if not Path(args.md).is_absolute() else Path(args.md)
    write_report(report, out, md)
    _print_summary(report)
    print(f"wrote {out}")
    print(f"wrote {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
