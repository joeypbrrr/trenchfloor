"""Offline checks for paper P&L, the no-top-tick rule, lessons, and holder math."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backtest import beats, dollar_pnl, metrics, simulate
from memory import Memory
from safety import assess_mint, cluster_flags

PAPER = {
    "notional_usd": 100,
    "fee_bps_per_side": 30,
    "base_slippage_bps": 0,
    "slippage_extra_below_25k_bps": 0,
    "slippage_extra_below_12k_bps": 0,
    "oos_fraction": 0.3,
    "min_hourly_bars": 30,
}
VARIANT = {
    "id": "dip_20_45_stop12_tp25_hold16",
    "zone_low": 0.20,
    "zone_high": 0.45,
    "stop": 0.12,
    "target": 0.25,
    "hold_bars": 16,
    "name": "test dip",
}


def bar(ts, o, h, l, c):
    return {"t": ts, "o": o, "h": h, "l": l, "c": c, "v": 1}


class PaperMath(unittest.TestCase):
    def test_flat_trade_loses_the_fee(self):
        self.assertLess(dollar_pnl(1, 1, 100, 0.003), 0)

    def test_hand_pnl(self):
        pnl = dollar_pnl(1, 1.25, 100, 0.003)
        qty = 100 / 1.003
        proceeds = qty * 1.25 * 0.997
        self.assertAlmostEqual(pnl, proceeds - 100, places=9)
        self.assertGreater(pnl, 20)

    def test_rally_never_enters(self):
        bars = [bar(i * 3600, 10 + i, 11 + i, 9.5 + i, 10.8 + i) for i in range(40)]
        trades = simulate(bars, VARIANT, {"mint": "M", "symbol": "UP", "liquidity_usd": 50000}, PAPER)
        self.assertEqual(trades, [])

    def test_dip_and_stop_first(self):
        bars = []
        ts = 1_700_000_000
        bars.append(bar(ts, 10, 10, 9.5, 10))
        for i in range(1, 12):
            price = 10 - i * 0.6
            bars.append(bar(ts + i * 3600, price + 0.4, price + 0.45, price, price + 0.05))
        # green bounce inside 20-45% of the prior 10 high. close ~3.3
        bars.append(bar(ts + 12 * 3600, 3.0, 3.4, 2.9, 3.3))
        # next open is the entry, and this bar hits both stop and target
        bars.append(bar(ts + 13 * 3600, 3.2, 5.0, 2.0, 4.0))
        for i in range(14, 36):
            bars.append(bar(ts + i * 3600, 4, 4.2, 3.8, 4.1))
        trades = simulate(bars, VARIANT, {"mint": "MINT", "symbol": "DIP", "name": "Dip", "liquidity_usd": 50000}, PAPER)
        self.assertTrue(trades, "expected a dip entry")
        trade = trades[0]
        self.assertEqual(trade["exit_reason"], "stop")
        self.assertLess(trade["pnl_usd"], 0)
        self.assertEqual(trade["label"], "PAPER / SIMULATED")
        self.assertEqual(trade["dex_url"], "https://dexscreener.com/solana/MINT")
        self.assertEqual(trade["gmgn_url"], "https://gmgn.ai/sol/token/MINT")
        self.assertIn("T", trade["entry_time"])
        self.assertGreater(trade["exit_time"], trade["entry_time"])
        self.assertLess(trade["entry_price"], trade["ath_price"])
        self.assertLess(trade["pnl_usd"], dollar_pnl(trade["entry_price"], trade["exit_price"], 100, 0))

    def test_beats_requires_out_of_sample_edge(self):
        weak = {"trades": 6, "expectancy_usd": 0.5}
        strong = {"trades": 6, "expectancy_usd": 1.0}
        self.assertFalse(beats({"trades": 4, "expectancy_usd": 5}, None, 5))
        self.assertFalse(beats({"trades": 6, "expectancy_usd": -1}, None, 5))
        self.assertTrue(beats(weak, None, 5))
        self.assertTrue(beats(strong, weak, 5))
        self.assertFalse(beats(weak, strong, 5))
        self.assertGreater(metrics([{"pnl_usd": 2}, {"pnl_usd": -1}])["expectancy_usd"], 0)


class LessonsAndLedger(unittest.TestCase):
    def test_rules_survive_and_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mem = Memory(root)
            mem.add_rule("live_mint_authority", "skip tokens with live mint authority", "MINT had one", "Risk Manager", "MINT", "BAD")
            mem.reject_mint("MINT", "skip tokens with live mint authority", "live_mint_authority", "BAD")
            again = Memory(root)
            self.assertEqual(again.data["rules"][0]["rule"], "skip tokens with live mint authority")
            blocked = again.blocks({"mint": "MINT", "liquidity_usd": 50000, "market_cap_usd": 100000, "safety": {"mint_authority_active": True}})
            self.assertTrue(any("mint authority" in r for r in blocked))
            fresh = again.blocks({"mint": "OTHER", "liquidity_usd": 50000, "market_cap_usd": 100000, "safety": {}})
            self.assertEqual(fresh, [])
            self.assertIn("skip tokens with live mint authority", (root / "LESSONS.md").read_text())

    def test_variant_not_retested_and_ledger_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mem = Memory(root)
            self.assertTrue(mem.can_test("dip_a"))
            mem.record_variant({"id": "dip_a", "status": "rejected", "reason": "lost", "oos": {"expectancy_usd": -1}})
            self.assertFalse(Memory(root).can_test("dip_a"))
            trade = {
                "id": "abc",
                "label": "PAPER / SIMULATED",
                "mint": "M",
                "symbol": "S",
                "name": "Name",
                "entry_time": "2026-11-07T10:00:00-05:00",
                "exit_time": "2026-11-07T12:00:00-05:00",
                "entry_price": 1,
                "exit_price": 0.8,
                "pnl_usd": -20,
                "liquidity_usd": 10000,
                "market_cap_usd": 100000,
                "strategy_id": "dip_a",
                "exit_reason": "stop",
            }
            self.assertEqual(len(mem.record_trades([trade])), 1)
            self.assertEqual(mem.record_trades([trade]), [])
            mem.learn_from_losses([trade])
            day = json.loads((root / "data" / "ledger" / "2026-11-07.json").read_text())
            self.assertEqual(day["label"], "PAPER / SIMULATED")
            self.assertEqual(day["trade_count"], 1)
            self.assertEqual(day["pnl_usd"], -20)
            index = json.loads((root / "data" / "ledger" / "index.json").read_text())
            self.assertEqual(index["days"][0]["date"], "2026-11-07")
            self.assertTrue(any(r["code"] == "min_liquidity_15000" for r in Memory(root).data["rules"]))


class HolderRules(unittest.TestCase):
    def mint(self, auth=None, extensions=None):
        return {
            "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "data": {"parsed": {"type": "mint", "info": {
                "mintAuthority": auth,
                "freezeAuthority": None,
                "extensions": extensions or [],
            }}},
        }

    def test_wallet_above_3_5_fails_and_exact_line_passes(self):
        supply = 100000
        fail = assess_mint(self.mint(), [{"owner": "Wallet", "amount": 3600, "address": "ta"}], {"Wallet": {"executable": False}}, supply, 0, None)
        ok = assess_mint(self.mint(), [{"owner": "Wallet", "amount": 3500, "address": "ta"}], {"Wallet": {"executable": False}}, supply, 0, None)
        self.assertEqual(fail["status"], "fail")
        self.assertTrue(fail["holder_over_3_5"])
        self.assertEqual(ok["status"], "pass")

    def test_lp_sized_and_program_are_excluded(self):
        supply = 100000
        rows = [
            {"owner": "Pool", "amount": 40000, "address": "lp"},
            {"owner": "Wallet", "amount": 3000, "address": "w"},
        ]
        meta = {"Pool": {"executable": False}, "Wallet": {"executable": False}}
        result = assess_mint(self.mint(), rows, meta, supply, 0, 40000)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["lp_matched"])
        self.assertEqual(result["top_human_pct"], 3.0)
        program = assess_mint(
            self.mint(),
            [{"owner": "Prog", "amount": 50000, "address": "p"}, {"owner": "Wallet", "amount": 1000, "address": "w"}],
            {"Prog": {"executable": True}, "Wallet": {"executable": False}},
            supply, 0, None,
        )
        self.assertEqual(program["status"], "pass")
        self.assertGreater(program["program_hold_pct"], 20)

    def test_live_mint_and_delegate_fail(self):
        minty = assess_mint(self.mint(auth="Creator"), [{"owner": "W", "amount": 100, "address": "a"}], {"W": {"executable": False}}, 100000, 0, None)
        self.assertIn("live mint authority", " ".join(minty["hard_fails"]))
        hooked = assess_mint(
            self.mint(extensions=[{"extension": "permanentDelegate", "state": {}}]),
            [{"owner": "W", "amount": 100, "address": "a"}],
            {"W": {"executable": False}},
            100000, 0, None,
        )
        self.assertEqual(hooked["status"], "fail")
        self.assertIn("permanentDelegate", hooked["risky_extensions"])

    def test_shared_funder_fails_and_same_slot_only_flags(self):
        samples = [
            {"owner": "A", "pct": 2.0, "slots": [1], "funders": ["F"]},
            {"owner": "B", "pct": 2.0, "slots": [1], "funders": ["F"]},
        ]
        flagged = cluster_flags(samples)
        self.assertTrue(flagged["fail"])
        slot_only = cluster_flags([
            {"owner": "A", "pct": 3.0, "slots": [9], "funders": []},
            {"owner": "B", "pct": 3.0, "slots": [9], "funders": []},
        ])
        self.assertFalse(slot_only["fail"])
        self.assertEqual(slot_only["flags"][0]["kind"], "same_slot")


if __name__ == "__main__":
    unittest.main()
