"""Iterative backtester: research a finding, then keep it only when held-out expectancy holds."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from backtest import simulate
from entry_gates import assess_entry_gates, measure_entry_signals
from iterative_backtest import (
    FEATURE_SPECS,
    annotate_trade,
    evaluate_oos,
    indexed_candidates,
    render_markdown,
    research_feature,
    rule_matches,
    run_iterative_backtest,
    welch_p_flagged_worse,
)

ROOT = Path(__file__).resolve().parents[1]
PAPER = {
    "notional_usd": 100,
    "fee_bps_per_side": 30,
    "base_slippage_bps": 0,
    "slippage_extra_below_25k_bps": 0,
    "slippage_extra_below_12k_bps": 0,
    "oos_fraction": 0.30,
    "min_hourly_bars": 30,
    "min_oos_trades": 5,
}
VARIANT = {
    "id": "dip_20_40_stop8_tp15_hold8",
    "zone_low": 0.20,
    "zone_high": 0.40,
    "stop": 0.08,
    "target": 0.15,
    "hold_bars": 8,
    "name": "champion dip",
}


def bar(ts, o, h, l, c, v=5):
    return {"t": ts, "o": o, "h": h, "l": l, "c": c, "v": v}


def path(start, signal_index, win, length=40):
    bars = [bar(start, 10, 10, 9.5, 9.8, 5)]
    for i in range(1, length):
        t = start + i * 3600
        if i == signal_index:
            bars.append(bar(t, 2.9, 3.3, 2.8, 3.2, 5))
        elif i == signal_index + 1:
            bars.append(bar(t, 3.0, 3.6, 2.85, 3.5, 5) if win else bar(t, 3.0, 3.2, 2.4, 2.5, 5))
        else:
            bars.append(bar(t, 8, 8.2, 7.5, 7.8, 5))
    return bars


def coin(mint, symbol, signal_index, win, bundle, timing="at_entry", start=1_700_000_000):
    return {
        "mint": mint,
        "symbol": symbol,
        "name": symbol,
        "pool": "pool-" + mint,
        "liquidity_usd": 80000,
        "market_cap_usd": 900000,
        "bars": path(start, signal_index, win),
        "signals": {"bundle_supply_pct": bundle},
        "signal_timing": timing,
    }


def book(oos_bundled_win, timing="at_entry"):
    rows = []
    n = 0
    for _ in range(6):
        n += 1
        rows.append(coin(f"BL{n}", f"BL{n}", 10, False, 40, timing, 1_700_000_000 + n))
    n += 1
    rows.append(coin(f"BW{n}", f"BW{n}", 10, True, 40, timing, 1_700_000_000 + n))
    for _ in range(6):
        n += 1
        rows.append(coin(f"CW{n}", f"CW{n}", 10, True, 1, timing, 1_700_000_000 + n))
    for _ in range(5):
        n += 1
        rows.append(coin(f"OL{n}", f"OL{n}", 30, oos_bundled_win, 40, timing, 1_800_000_000 + n))
    for _ in range(6):
        n += 1
        rows.append(coin(f"OC{n}", f"OC{n}", 30, not oos_bundled_win, 1, timing, 1_800_000_000 + n))
    return rows


def fake(pnl, bundle, timing="at_entry", name="T"):
    return {
        "id": f"{name}-{pnl}-{bundle}-{timing}",
        "pnl_usd": pnl,
        "sample": "in_sample",
        "symbol": name,
        "mint": name,
        "exit_reason": "stop" if pnl < 0 else "target",
        "strategy_id": "dip",
        "exit_ts": 1,
        "features": {"bundle_supply_pct": bundle},
        "feature_timing": {"bundle_supply_pct": timing},
    }


class SignalMeasure(unittest.TestCase):
    def test_same_slot_bundle_is_measured_and_gate_decision_is_unchanged(self):
        now = 1_700_000_000
        holders = [{
            "owner": f"B{i}", "pct": 6, "history_complete": True, "oldest_ts": now - 10 * 86400,
            "funders": [f"F{i}"], "funder_known": True, "acquire_slot": 77, "acquire_known": True,
        } for i in range(3)]
        evidence = {
            "now": now,
            "created_ts": now - 48 * 3600,
            "top10_ex_pool_burn_pct": 18,
            "holders": holders,
            "holder_read_ok": True,
            "trade_read_ok": True,
            "trades": [{"signer": "A", "side": "buy", "amount": 3}, {"signer": "B", "side": "sell", "amount": 1}],
            "lp_visible": True,
            "lp_burned_or_locked": True,
            "global_fees_verified": True,
            "global_fees_sol": 2,
        }
        gates = {row["name"]: row["pass"] for row in assess_entry_gates(evidence, now=now)}
        measured = measure_entry_signals(evidence, now=now)
        self.assertEqual({row["name"]: row["pass"] for row in measured["checks"]}, gates)
        self.assertIs(gates["bundle_sniper_share"], False)
        self.assertEqual(measured["bundle_supply_pct"], 18)
        self.assertEqual(measured["fresh_wallet_count"], 0)

    def test_missing_acquire_slots_do_not_become_a_zero_bundle(self):
        evidence = {
            "now": 1_700_000_000,
            "created_ts": 1_699_000_000,
            "holders": [{"owner": "A", "pct": 4}, {"owner": "B", "pct": 3}],
            "holder_read_ok": True,
        }
        measured = measure_entry_signals(evidence, now=evidence["now"])
        self.assertIsNone(measured["bundle_supply_pct"])
        self.assertIsNone(measured["fresh_wallet_count"])
        self.assertIsNone(measured["wash_roundtrip_fraction"])
        self.assertFalse(measured["bundle_measured"])

    def test_linked_funder_supply_counts_as_bundled(self):
        now = 1_700_000_000
        holders = [
            {"owner": "A", "pct": 12, "history_complete": True, "oldest_ts": now - 10 * 86400, "funders": ["Same"], "funder_known": True},
            {"owner": "B", "pct": 9, "history_complete": True, "oldest_ts": now - 10 * 86400, "funders": ["Same"], "funder_known": True},
        ]
        measured = measure_entry_signals({
            "now": now, "holders": holders, "holder_read_ok": True,
        }, now=now)
        self.assertEqual(measured["bundle_supply_pct"], 21)
        self.assertEqual(measured["linked_funder_wallets"], 2)


class ResearchStep(unittest.TestCase):
    def _split(self, flagged_pnl, clean_pnl, flagged_n=6, clean_n=6, bundle_flagged=40, bundle_clean=1):
        trades = [fake(flagged_pnl, bundle_flagged, name=f"F{i}") for i in range(flagged_n)]
        trades += [fake(clean_pnl, bundle_clean, name=f"C{i}") for i in range(clean_n)]
        return trades

    def test_good_predictor_names_the_cutoff_and_winners_removed(self):
        trades = self._split(-10, 12)
        trades.append(fake(12, 40, name="WINB"))
        note = research_feature("bundle_supply_pct", trades, [40, 15], min_side=5)
        self.assertEqual(note["verdict"], "good predictor")
        self.assertGreaterEqual(note["threshold"], 5)
        self.assertLess(note["threshold"], 40)
        self.assertEqual(note["winners_removed"], 1)
        self.assertGreater(note["losers_removed"], note["winners_removed"])
        self.assertLessEqual(note["p_one_sided"], 0.10)
        self.assertIn("good predictor", note["text"])
        self.assertGreater(note["flagged"]["n"], 0)
        self.assertGreater(note["clean"]["n"], 0)
        self.assertLess(note["flagged"]["expectancy_usd"], note["clean"]["expectancy_usd"])

    def test_bad_predictor_when_bundled_coins_win(self):
        note = research_feature("bundle_supply_pct", self._split(12, -10), [15], min_side=5)
        self.assertEqual(note["verdict"], "bad predictor")
        self.assertIn("bad predictor", note["text"])

    def test_thin_sample_is_inconclusive(self):
        note = research_feature("bundle_supply_pct", self._split(-10, 12, 2, 2), [15], min_side=5)
        self.assertEqual(note["verdict"], "inconclusive")
        self.assertIn("inconclusive", note["text"])

    def test_later_snapshot_is_not_a_good_predictor(self):
        trades = []
        for i in range(6):
            trades.append(fake(-10, 40, timing="later_snapshot", name=f"F{i}"))
            trades.append(fake(12, 1, timing="later_snapshot", name=f"C{i}"))
        note = research_feature("bundle_supply_pct", trades, [15], min_side=5)
        self.assertEqual(note["verdict"], "inconclusive")
        self.assertIn("later snapshot", note["text"])

    def test_unmeasured_bundle_is_inconclusive_and_not_zero(self):
        trades = []
        for i in range(8):
            trade = fake(-10 if i < 4 else 10, None, name=f"U{i}")
            trade["features"] = {"bundle_supply_pct": None}
            trade["feature_timing"] = {"bundle_supply_pct": "unmeasured"}
            trades.append(trade)
        note = research_feature("bundle_supply_pct", trades, [15], min_side=5)
        self.assertEqual(note["verdict"], "inconclusive")
        self.assertIsNone(note["threshold"])
        self.assertIn("not measured", note["text"])
        self.assertIn("No value was invented", note["text"])

    def test_missing_path_features_stay_missing(self):
        trade = {"entry_ts": 50_000, "entry_frac_of_ath": 0.31, "pnl_usd": -4}
        annotate_trade(trade, {"signals": {}, "signal_timing": "at_entry"}, [
            {"t": 1000, "o": 1, "h": 1, "l": 1, "c": 1},
            {"t": 2000, "v": 0},
            {"t": 3000, "v": 0},
            {"t": 4000, "v": 0},
        ])
        self.assertIsNone(trade["features"]["liquidity_drop_pct"])
        self.assertIsNone(trade["features"]["volume_top_share"])
        self.assertIsNone(trade["features"]["bundle_supply_pct"])
        self.assertEqual(trade["feature_timing"]["entry_frac_of_ath"], "at_entry")
        series = [{"t": 1000, "liquidity_usd": 100}, {"t": 2000, "liquidity_usd": 40}]
        annotate_trade(trade, {"liquidity_bars": series, "signals": {}, "signal_timing": "at_entry"}, [])
        self.assertAlmostEqual(trade["features"]["liquidity_drop_pct"], 60.0)

    def test_all_zero_bundle_has_no_flagged_group(self):
        trades = [fake(-10, 0, name=f"A{i}") for i in range(6)]
        trades += [fake(5, 0, name=f"B{i}") for i in range(6)]
        note = research_feature("bundle_supply_pct", trades, [15], min_side=5)
        self.assertEqual(note["verdict"], "inconclusive")
        self.assertEqual(note["flagged"]["n"], 0)
        self.assertEqual(note["value_min"], 0)
        self.assertEqual(note["value_max"], 0)
        self.assertIn("no train trade", note["text"])

    def test_welch_p_is_small_only_when_flagged_trades_are_worse(self):
        self.assertLess(welch_p_flagged_worse([-10, -9, -11, -8, -12], [8, 9, 10, 11, 7]), 0.01)
        self.assertGreater(welch_p_flagged_worse([8, 9, 10, 11, 7], [-10, -9, -11, -8, -12]), 0.9)


class OutOfSampleGuard(unittest.TestCase):
    def rule(self, threshold=15):
        return {"feature": "bundle_supply_pct", "op": ">", "threshold": threshold}

    def trades(self, specs):
        rows = []
        for i, (pnl, bundle, timing) in enumerate(specs):
            row = fake(pnl, bundle, timing=timing, name=f"O{i}")
            row["sample"] = "out_of_sample"
            rows.append(row)
        return rows

    def test_rejects_a_rule_that_hurts_held_out_expectancy(self):
        rows = self.trades([(12, 40, "at_entry")] * 6 + [(-10, 1, "at_entry")] * 6)
        keep, reason, _info = evaluate_oos(self.rule(), rows, 5, 0.25)
        self.assertFalse(keep)
        self.assertIn("falls", reason)

    def test_rejects_a_rule_that_cuts_the_book_toward_zero(self):
        rows = self.trades([(-10, 40, "at_entry")] * 6 + [(12, 1, "at_entry")] * 6)
        keep, reason, _info = evaluate_oos(self.rule(), rows, 5, 0.9)
        self.assertFalse(keep)
        self.assertIn("floor", reason)

    def test_keeps_a_rule_that_does_not_hurt(self):
        rows = self.trades([(-10, 40, "at_entry")] * 6 + [(12, 1, "at_entry")] * 6)
        keep, reason, info = evaluate_oos(self.rule(), rows, 5, 0.25)
        self.assertTrue(keep)
        self.assertGreater(info["after"]["expectancy_usd"], info["before"]["expectancy_usd"])
        self.assertGreaterEqual(info["after"]["trades"], 5)

    def test_snapshot_timing_never_matches(self):
        trade = fake(-10, 40, timing="later_snapshot")
        self.assertFalse(rule_matches(self.rule(), trade))
        missing = fake(-10, None)
        missing["features"] = {"bundle_supply_pct": None}
        self.assertFalse(rule_matches(self.rule(), missing))


class Loop(unittest.TestCase):
    def test_path_produces_one_expected_fill(self):
        sample = coin("M", "M", 10, False, 40)
        trades = simulate(sample["bars"], VARIANT, sample, PAPER)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["exit_reason"], "stop")
        self.assertLess(trades[0]["pnl_usd"], 0)
        self.assertEqual(trades[0]["sample"], "in_sample")
        late = coin("N", "N", 30, True, 1)
        late_trades = simulate(late["bars"], VARIANT, late, PAPER)
        self.assertEqual(late_trades[0]["exit_reason"], "target")
        self.assertEqual(late_trades[0]["sample"], "out_of_sample")
        self.assertGreater(late_trades[0]["pnl_usd"], 0)

    def test_keeps_bundled_rule_only_when_train_and_held_out_agree(self):
        before_config = (ROOT / "config.json").read_bytes()
        before_lessons = (ROOT / "data" / "lessons.json").read_bytes()
        report = run_iterative_backtest(book(False), VARIANT, PAPER, max_iterations=3, min_side=5)
        self.assertEqual((ROOT / "config.json").read_bytes(), before_config)
        self.assertEqual((ROOT / "data" / "lessons.json").read_bytes(), before_lessons)
        self.assertEqual(len(report["final_rules"]), 1)
        rule = report["final_rules"][0]
        self.assertEqual(rule["feature"], "bundle_supply_pct")
        self.assertGreaterEqual(rule["threshold"], FEATURE_SPECS["bundle_supply_pct"]["floor"])
        self.assertLess(rule["threshold"], 40)
        self.assertIn("bundled", rule["rule"])
        note = next(row for row in report["research_notes"] if row["feature"] == "bundle_supply_pct" and row["verdict"] == "good predictor")
        self.assertEqual(note["winners_removed"], 1)
        train_losses = 6
        first = report["iterations"][1]
        self.assertGreaterEqual(sum(1 for finding in first["findings"] if not finding.get("standing")), train_losses)
        self.assertGreater(report["after"]["out_of_sample"]["expectancy_usd"], report["before"]["out_of_sample"]["expectancy_usd"])
        self.assertGreaterEqual(report["after"]["out_of_sample"]["trades"], 5)
        self.assertIn(report["stopped_because"], {"no validated rules", "no new findings", "max_iterations"})
        text = render_markdown(report)
        self.assertIn("Out of sample", text)
        self.assertIn("good predictor", text)
        self.assertIn("Rejected", text)

    def test_rejects_bundled_rule_when_held_out_book_gets_worse(self):
        report = run_iterative_backtest(book(True), VARIANT, PAPER, max_iterations=2, min_side=5)
        self.assertEqual(report["final_rules"], [])
        rejected = [row for row in report["rejected_rules"] if row["feature"] == "bundle_supply_pct"]
        self.assertTrue(any(row["stage"] == "out_of_sample" and "falls" in row["reason"] for row in rejected))
        self.assertEqual(report["before"]["out_of_sample"]["expectancy_usd"], report["after"]["out_of_sample"]["expectancy_usd"])

    def test_later_snapshot_bundle_is_not_kept(self):
        report = run_iterative_backtest(book(False, timing="later_snapshot"), VARIANT, PAPER, max_iterations=2, min_side=5)
        self.assertEqual(report["final_rules"], [])
        note = next(row for row in report["research_notes"] if row["feature"] == "bundle_supply_pct")
        self.assertEqual(note["verdict"], "inconclusive")
        self.assertIn("later snapshot", note["text"])

    def test_unmeasured_history_does_not_invent_the_bundle_rule(self):
        rows = []
        for i in range(8):
            item = coin(f"U{i}", f"U{i}", 10, i % 2 == 0, 40)
            item["signals"] = {}
            item["signal_timing"] = "unmeasured"
            rows.append(item)
        report = run_iterative_backtest(rows, VARIANT, PAPER, max_iterations=2, min_side=5)
        self.assertEqual(report["final_rules"], [])
        note = next(row for row in report["research_notes"] if row["feature"] == "bundle_supply_pct")
        self.assertEqual(note["verdict"], "inconclusive")
        self.assertIn("not measured", note["text"])
        self.assertTrue(report["thin_data"])

    def test_max_iterations_stops_the_loop(self):
        report = run_iterative_backtest(book(False), VARIANT, PAPER, max_iterations=1, min_side=5)
        self.assertEqual(report["stopped_because"], "max_iterations")
        self.assertEqual(len([row for row in report["iterations"] if row["iteration"] > 0]), 1)
        self.assertEqual(len(report["final_rules"]), 1)

    def test_indexed_candidates_do_not_invent_bundle_data(self):
        research = {"watchlist": [{
            "mint": "MintA",
            "symbol": "AAA",
            "pool": "PoolA",
            "liquidity_usd": 1000,
            "market_cap_usd": 5000,
            "safety": {"humans": [{"owner": "W", "pct": 1.5, "token_account": "TA"}]},
        }]}
        lessons = {"variants": [{"pools": [{"mint": "MintB", "symbol": "BBB", "pool": "PoolB"}]}]}
        rows = {row["mint"]: row for row in indexed_candidates(research, lessons)}
        self.assertEqual(set(rows), {"MintA", "MintB"})
        self.assertIsNone(rows["MintB"].get("signals"))
        self.assertIsNone(rows["MintB"]["listed_holder_pct_sum"])
        self.assertEqual(rows["MintA"]["listed_holder_pct_sum"], 1.5)
        self.assertNotIn("bundle_supply_pct", rows["MintA"])

    def test_live_loop_and_config_gates_are_untouched(self):
        self.assertNotIn("iterative_backtest", (ROOT / "research.py").read_text())
        self.assertNotIn("iterative_backtest", (ROOT / "forward_paper.py").read_text())
        config = json.loads((ROOT / "config.json").read_text())
        self.assertEqual(config["entry_gates"]["max_bundle_sniper_pct"], 15)
        self.assertEqual(config["entry_gates"]["max_top10_pct"], 40)
        self.assertNotIn("iterative_backtest", json.dumps(config))
        self.assertIn("data/backtest_iterations.json", (ROOT / "publish_data.py").read_text())
        page = (ROOT / "index.html").read_text()
        self.assertIn('id="iterBacktest"', page)
        self.assertIn("data/backtest_iterations.json", page)
        self.assertIn("LEARNING LOG", page)


if __name__ == "__main__":
    unittest.main()
