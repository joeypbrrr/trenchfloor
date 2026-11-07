"""Goal projection and goal-ranked promotion."""
import unittest

from backtest import beats_goal, goal_projection


class Goal(unittest.TestCase):
    def test_projection_math(self):
        g = goal_projection({"trades": 10, "expectancy_usd": 2.0}, 10 * 86400, 100, 3000, 5000)
        self.assertAlmostEqual(g["trades_per_month"], 30.4, places=1)
        self.assertAlmostEqual(g["monthly_usd"], 60.88, places=2)
        self.assertEqual(g["ticket_for_low_usd"], round(100 * 3000 / 60.88))
        self.assertEqual(g["ticket_for_high_usd"], round(100 * 5000 / 60.88))

    def test_negative_has_no_ticket(self):
        g = goal_projection({"trades": 10, "expectancy_usd": -1.0}, 86400 * 5, 100, 3000, 5000)
        self.assertIsNone(g["ticket_for_low_usd"])

    def test_gates_never_loosen(self):
        big = goal_projection({"trades": 4, "expectancy_usd": 50.0}, 86400, 100, 3000, 5000)
        self.assertFalse(beats_goal({"trades": 4, "expectancy_usd": 50.0}, big, None, 5))
        self.assertFalse(beats_goal({"trades": 9, "expectancy_usd": -0.1}, big, None, 5))

    def test_ranked_by_monthly(self):
        champ = {"oos": {"trades": 9, "expectancy_usd": 3.0}, "goal": {"monthly_usd": 40.0}}
        # lower per-trade average but more trades per month wins
        self.assertTrue(beats_goal({"trades": 30, "expectancy_usd": 1.0}, {"monthly_usd": 90.0}, champ, 5))
        self.assertFalse(beats_goal({"trades": 30, "expectancy_usd": 5.0}, {"monthly_usd": 39.0}, champ, 5))

    def test_legacy_champion_uses_old_rule(self):
        champ = {"oos": {"trades": 9, "expectancy_usd": 0.41}}
        self.assertTrue(beats_goal({"trades": 6, "expectancy_usd": 0.5}, {"monthly_usd": 5.0}, champ, 5))
        self.assertFalse(beats_goal({"trades": 6, "expectancy_usd": 0.3}, {"monthly_usd": 500.0}, champ, 5))


if __name__ == "__main__":
    unittest.main()
