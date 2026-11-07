"""Hard entry gates. Network is not required; recorded holder reads are frozen."""
import json
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from entry_gates import assess_entry_gates, decode_pumpswap_pool, trades_from_transaction
from tiers import evaluate


def ts(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()


def base(now, created, **kw):
    row = {
        "now": now,
        "created_ts": created,
        "top10_ex_pool_burn_pct": 5,
        "holder_read_ok": True,
        "holders": [{
            "owner": "OldWallet",
            "pct": 1,
            "history_complete": True,
            "oldest_ts": now - 10 * 86400,
            "funders": ["UniqueFunder"],
            "funder_known": True,
            "acquire_slot": 50,
            "acquire_known": True,
        }],
        "trade_read_ok": True,
        "trades": [{"signer": "A", "side": "buy", "amount": 4}, {"signer": "B", "side": "sell", "amount": 1}],
        "lp_visible": True,
        "lp_burned_or_locked": True,
        "lp_detail": "LP mint supply 0",
        "global_fees_verified": True,
        "global_fees_sol": 2,
    }
    row.update(kw)
    return row


def by_name(checks):
    return {c["name"]: c for c in checks}


class GateMath(unittest.TestCase):
    def setUp(self):
        self.now = 1_794_040_000
        self.created = self.now - 8 * 3600

    def test_clean_evidence_passes_every_gate(self):
        checks = by_name(assess_entry_gates(base(self.now, self.created), now=self.now))
        self.assertTrue(all(c["pass"] is True for c in checks.values()), checks)

    def test_unknown_age_top10_holders_lp_and_fees_fail_closed(self):
        checks = by_name(assess_entry_gates({"now": self.now}, now=self.now))
        for name in ("min_pair_age", "top10_ex_pool_burn", "fresh_wallet_cluster", "bundle_sniper_share", "wash_trade", "lp_locked_or_burned", "global_fees_sol"):
            self.assertIsNone(checks[name]["pass"], name)
            self.assertIn("FAIL CLOSED", checks[name]["detail"])

    def test_pair_age_floor_and_top10_cap(self):
        young = by_name(assess_entry_gates(base(self.now, self.now - 60), now=self.now))
        self.assertIs(young["min_pair_age"]["pass"], False)
        wide = by_name(assess_entry_gates(base(self.now, self.created, top10_ex_pool_burn_pct=40.01), now=self.now))
        self.assertIs(wide["top10_ex_pool_burn"]["pass"], False)
        under = by_name(assess_entry_gates(base(self.now, self.created, top10_ex_pool_burn_pct=40), now=self.now))
        self.assertIs(under["top10_ex_pool_burn"]["pass"], True)

    def test_full_signature_page_is_not_a_fresh_wallet(self):
        holders = [{
            "owner": "Busy", "pct": 2, "history_complete": False, "oldest_ts": self.now - 3600,
            "funders": [], "funder_known": False, "acquire_slot": None, "acquire_known": False,
        }]
        checks = by_name(assess_entry_gates(base(self.now, self.created, holders=holders), now=self.now))
        self.assertIs(checks["fresh_wallet_cluster"]["pass"], True)

    def test_three_fresh_wallets_block_even_when_each_is_small(self):
        holders = [{
            "owner": f"W{i}", "pct": 0.14, "history_complete": True, "oldest_ts": self.now - 3600,
            "funders": [f"F{i}"], "funder_known": True, "acquire_slot": 100 + i, "acquire_known": True,
        } for i in range(3)]
        checks = by_name(assess_entry_gates(base(self.now, self.created, holders=holders), now=self.now))
        self.assertIs(checks["fresh_wallet_cluster"]["pass"], False)
        self.assertIn("3 fresh", checks["fresh_wallet_cluster"]["detail"])

    def test_shared_funder_blocks(self):
        holders = [
            {"owner": "A", "pct": 3, "history_complete": True, "oldest_ts": self.now - 10 * 86400, "funders": ["Same"], "funder_known": True, "acquire_slot": 1, "acquire_known": True},
            {"owner": "B", "pct": 2.5, "history_complete": True, "oldest_ts": self.now - 10 * 86400, "funders": ["Same"], "funder_known": True, "acquire_slot": 9, "acquire_known": True},
        ]
        checks = by_name(assess_entry_gates(base(self.now, self.created, holders=holders), now=self.now))
        self.assertIs(checks["fresh_wallet_cluster"]["pass"], False)
        self.assertIn("Same", checks["fresh_wallet_cluster"]["detail"])

    def test_same_slot_bundle_blocks_below_top10_cap(self):
        holders = [{
            "owner": f"B{i}", "pct": 0.2, "history_complete": True, "oldest_ts": self.now - 10 * 86400,
            "funders": [f"F{i}"], "funder_known": True, "acquire_slot": 77, "acquire_known": True,
        } for i in range(3)]
        checks = by_name(assess_entry_gates(base(self.now, self.created, holders=holders, top10_ex_pool_burn_pct=1), now=self.now))
        self.assertIs(checks["bundle_sniper_share"]["pass"], False)
        self.assertIs(checks["top10_ex_pool_burn"]["pass"], True)

    def test_sniper_share_blocks_at_15_percent(self):
        holders = [{
            "owner": f"S{i}", "pct": 6, "history_complete": True, "oldest_ts": self.now - 10 * 86400,
            "funders": [f"F{i}"], "funder_known": True, "acquire_slot": 10 + i, "acquire_known": True,
        } for i in range(3)]
        checks = by_name(assess_entry_gates(base(self.now, self.created, holders=holders, top10_ex_pool_burn_pct=18), now=self.now))
        self.assertIs(checks["bundle_sniper_share"]["pass"], False)
        self.assertIn("18.00%", checks["bundle_sniper_share"]["detail"])

    def test_wash_roundtrip_and_unreadable_sample(self):
        trades = [{"signer": "Washer", "side": "buy", "amount": 5}, {"signer": "Washer", "side": "sell", "amount": 5}]
        hit = by_name(assess_entry_gates(base(self.now, self.created, trades=trades), now=self.now))
        self.assertIs(hit["wash_trade"]["pass"], False)
        small = [{"signer": "Washer", "side": "buy", "amount": 1}, {"signer": "Washer", "side": "sell", "amount": 1}, {"signer": "Real", "side": "buy", "amount": 100}]
        quiet = by_name(assess_entry_gates(base(self.now, self.created, trades=small), now=self.now))
        self.assertIs(quiet["wash_trade"]["pass"], True)
        unread = by_name(assess_entry_gates(base(self.now, self.created, trade_read_ok=False, trade_read_error="RPC rate limit (429)"), now=self.now))
        self.assertIsNone(unread["wash_trade"]["pass"])
        flagged = by_name(assess_entry_gates(base(self.now, self.created, is_wash_trading=True), now=self.now))
        self.assertIs(flagged["wash_trade"]["pass"], False)

    def test_lp_not_visible_blocks_and_supply_zero_passes(self):
        hidden = by_name(assess_entry_gates(base(self.now, self.created, lp_visible=False, lp_detail="LP lock/burn is not visible"), now=self.now))
        self.assertIsNone(hidden["lp_locked_or_burned"]["pass"])
        unlocked = by_name(assess_entry_gates(base(self.now, self.created, lp_burned_or_locked=False, lp_detail="LP mint still has supply 10"), now=self.now))
        self.assertIs(unlocked["lp_locked_or_burned"]["pass"], False)

    def test_fee_lower_bound_below_1_5_is_unknown_not_a_measured_fail(self):
        low = by_name(assess_entry_gates(base(
            self.now, self.created, global_fees_verified=False, global_fees_sol=None, fee_lower_bound_sol=0.003
        ), now=self.now))
        self.assertIsNone(low["global_fees_sol"]["pass"])
        self.assertIn("unclaimed", low["global_fees_sol"]["detail"].lower())
        self.assertIn("not proof", low["global_fees_sol"]["detail"].lower())
        proven = by_name(assess_entry_gates(base(
            self.now, self.created, global_fees_verified=False, global_fees_sol=None, fee_lower_bound_sol=1.5
        ), now=self.now))
        self.assertIs(proven["global_fees_sol"]["pass"], True)
        short = by_name(assess_entry_gates(base(self.now, self.created, global_fees_sol=1.49), now=self.now))
        self.assertIs(short["global_fees_sol"]["pass"], False)

    def test_trade_parser_reads_signer_delta(self):
        tx = {
            "transaction": {"message": {"accountKeys": [{"pubkey": "Signer", "signer": True}]}},
            "meta": {
                "preTokenBalances": [{"mint": "Mint", "owner": "Signer", "uiTokenAmount": {"uiAmount": 1}}],
                "postTokenBalances": [{"mint": "Mint", "owner": "Signer", "uiTokenAmount": {"uiAmount": 4}}],
            },
        }
        self.assertEqual(trades_from_transaction(tx, "Mint"), [{"signer": "Signer", "side": "buy", "amount": 3}])
        self.assertIsNone(trades_from_transaction({"meta": {}}, "Mint"))

    def test_pool_decoder_rejects_non_pools(self):
        self.assertIsNone(decode_pumpswap_pool(b"not-a-pool"))


class RecordedEntries(unittest.TestCase):
    """Frozen reads from the public RPC on 2026-11-07. Not a pass for fees."""

    def evidence(self, created_hours_before_entry, entry_ts, top10, holders, fee_lower):
        return {
            "now": entry_ts,
            "created_ts": entry_ts - created_hours_before_entry * 3600,
            "top10_ex_pool_burn_pct": top10,
            "holder_read_ok": True,
            "holders": holders,
            "trade_read_ok": True,
            "trades": [{"signer": "Buyer", "side": "buy", "amount": 2}, {"signer": "Seller", "side": "sell", "amount": 1}],
            "lp_visible": True,
            "lp_burned_or_locked": True,
            "lp_detail": "chosen pool LP mint supply is 0",
            "global_fees_verified": False,
            "global_fees_sol": None,
            "fee_lower_bound_sol": fee_lower,
        }

    def holder(self, owner, pct, complete, oldest):
        return {
            "owner": owner, "pct": pct, "history_complete": complete, "oldest_ts": None if oldest is None else ts(oldest),
            "funders": [], "funder_known": False, "acquire_slot": None, "acquire_known": False,
        }

    def test_five_paper_entries(self):
        cases = {
            "COGE": self.evidence(33.19, 1794027609, 8.62, [
                self.holder("coge-holder", 0.90, False, "2026-11-05T21:12:58"),
            ], 0.0),
            "GATO": self.evidence(1769.57, 1794031307, 14.27, [
                self.holder("gato-fresh-a", 3.3245, True, "2026-11-06T23:58:37"),
                self.holder("gato-fresh-b", 1.1054, True, "2026-11-06T23:11:07"),
                self.holder("gato-old", 1.4186, True, "2026-09-01T09:48:09"),
            ], 0.000247),
            "HODL": self.evidence(7.89, 1794034998, 1.36, [
                self.holder("hodl-a", 0.1362, True, "2026-11-06T23:15:15"),
                self.holder("hodl-b", 0.1362, True, "2026-11-06T23:15:15"),
                self.holder("hodl-c", 0.1361, True, "2026-11-06T23:06:28"),
                self.holder("hodl-d", 0.1359, True, "2026-11-06T23:06:29"),
            ], 0.000037),
            "AMD": self.evidence(29.56, 1794038675, 1.14, [
                self.holder("amd-a", 0.148, True, "2026-11-07T05:52:26"),
                self.holder("amd-b", 0.1282, True, "2026-11-07T07:12:34"),
                self.holder("amd-c", 0.1202, True, "2026-11-07T05:40:02"),
                self.holder("amd-d", 0.1117, True, "2026-11-06T20:41:21"),
            ], 0.0),
            "GLITCH": self.evidence(521.51, 1794042338, 28.10, [
                self.holder("glitch-holder", 3.59, False, "2026-11-03T12:49:13"),
            ], 0.003669),
        }
        blocked_by_fresh = set()
        for symbol, evidence in cases.items():
            checks = by_name(assess_entry_gates(evidence))
            self.assertIs(checks["min_pair_age"]["pass"], True, symbol)
            self.assertIs(checks["top10_ex_pool_burn"]["pass"], True, symbol)
            self.assertIs(checks["lp_locked_or_burned"]["pass"], True, symbol)
            self.assertIs(checks["wash_trade"]["pass"], True, symbol)
            self.assertIsNone(checks["global_fees_sol"]["pass"], symbol)
            if checks["fresh_wallet_cluster"]["pass"] is False:
                blocked_by_fresh.add(symbol)
        self.assertEqual(blocked_by_fresh, {"HODL", "AMD"})


class FeedBlock(unittest.TestCase):
    def test_failed_gate_blocks_fallback_and_posts_reason(self):
        root = Path(__file__).resolve().parents[1]
        cfg = json.loads((root / "config.json").read_text())
        now = time.time()
        token = dict(
            mint="A", pool="P", symbol="HODL", name="Diamond Hands", price_usd=1,
            quote_mint="So11111111111111111111111111111111111111112", created_ts=now - 7200,
            liquidity_usd=2000, volume_24h_usd=30000, market_cap_usd=100000,
        )
        safety = dict(
            status="fail", summary="blocked", hard_rug_pass=False,
            hard_rug_checks=[{"name": "fresh_wallet_cluster", "pass": False, "detail": "FAIL 4 fresh wallets"}],
            hard_reasons=["fresh_wallet_cluster: FAIL 4 fresh wallets"],
            soft_checks=[], top_human_pct=1, top10_measured_pct=5,
        )
        lines = []
        with patch("tiers.hard_review", return_value=safety):
            result = evaluate([token], type("M", (), {"rpc": None, "source_status": {}})(), cfg, lambda *a: lines.append(a), lambda *a: True, Path("/tmp/entry-gate-test"))
        self.assertEqual(result["primary"], 0)
        self.assertEqual(result["fallback"], 0)
        self.assertTrue(any(a[0] == "Risk Manager" and a[1].startswith("HARD BLOCK HODL:") and "fresh_wallet_cluster" in a[1] for a in lines))


if __name__ == "__main__":
    unittest.main()
