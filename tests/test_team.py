"""Offline checks for the one-team vote."""
from __future__ import annotations

import unittest

from team import decide, review_trades, team_review

CONFIG = {
    "filters": {"min_liquidity_usd": 12000, "min_volume_24h_usd": 8000},
    "entry_zone": {"min_frac_of_ath": 0.2, "max_frac_of_ath": 0.45},
    "holder_fail_pct": 3.5,
}
VARIANT = {"id": "dip_20_40_stop8_tp15_hold8", "zone_low": 0.2, "zone_high": 0.4, "stop": 0.08, "target": 0.15, "hold_bars": 8}
X_DOWN = {"ok": False, "status": 401, "detail": "X API 401"}


def token(**kw):
    base = {
        "mint": "M", "symbol": "T", "liquidity_usd": 50000, "volume_24h_usd": 90000, "in_entry_zone": True,
        "safety": {"status": "pass", "top_human_pct": 1.2, "hard_fails": [], "risky_extensions": []},
        "lesson_blocks": [],
    }
    base.update(kw)
    return base


def trade(i=0, frac=0.3, pnl=1.0):
    return {"id": f"t{i}", "mint": "M", "symbol": "T", "entry_ts": i * 10, "exit_ts": i * 10 + 5, "entry_frac_of_ath": frac, "pnl_usd": pnl}


class TeamVote(unittest.TestCase):
    def test_clean_trade_approved_with_x_abstaining(self):
        r = team_review(trade(), token(), VARIANT, [], CONFIG, X_DOWN)
        self.assertTrue(r["approved"])
        self.assertEqual(r["tally"], "5/6 approve")
        x = [v for v in r["votes"] if v["agent"] == "X/Twitter Scout"][0]
        self.assertEqual(x["vote"], "abstain")
        self.assertIn("401", x["reason"])
        self.assertEqual(r["proposed_by"], "Data Scout")

    def test_bubble_map_veto_over_3_5(self):
        t = token(safety={"status": "pass", "top_human_pct": 4.74, "hard_fails": []})
        r = team_review(trade(), t, VARIANT, [], CONFIG, X_DOWN)
        self.assertFalse(r["approved"])
        self.assertIn("Bubble Map Analyst", r["vetoes"])

    def test_risk_veto_beats_majority(self):
        votes = [{"agent": "Risk Manager", "vote": "reject"}] + [{"agent": a, "vote": "approve"} for a in ("Data Scout", "Backtester", "Strategist", "Bubble Map Analyst")]
        self.assertFalse(decide(votes)["approved"])

    def test_no_majority_rejects(self):
        votes = [{"agent": "Risk Manager", "vote": "approve"}, {"agent": "Data Scout", "vote": "reject"}, {"agent": "Backtester", "vote": "reject"}, {"agent": "Strategist", "vote": "reject"}]
        self.assertFalse(decide(votes)["approved"])

    def test_backtester_uses_only_earlier_fills(self):
        trades = [trade(i, pnl=-5) for i in range(4)] + [trade(9)]
        approved, rejected = review_trades(trades, {"M": token(in_entry_zone=False)}, VARIANT, CONFIG, X_DOWN)
        last = trades[-1]
        bt = [v for v in last["team"]["votes"] if v["agent"] == "Backtester"][0]
        self.assertEqual(bt["vote"], "reject")
        self.assertEqual(last["proposed_by"], "Strategist")
        self.assertEqual(len(approved) + len(rejected), 5)


if __name__ == "__main__":
    unittest.main()
