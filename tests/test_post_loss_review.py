"""Post-loss reviews must be written, retried, stored, and required before the next entry."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from forward_paper import PaperAccount, iso
from live_chat import LiveChat
from memory import Memory
from post_loss_review import CHECK_NAMES, review_is_complete, review_losing_trade


ROOT = Path(__file__).resolve().parents[1]
NOW = 1_794_044_000


def config():
    return {
        "entry_gates": {"max_top10_pct": 40},
        "tiers": {"primary": {"max_holder_pct": 20}},
    }


def good_chain():
    return {
        "status": "pass",
        "top_human_pct": 1.25,
        "top10_measured_pct": 6.5,
        "humans": [{"owner": "WalletA", "pct": 1.25}],
        "mint_authority_active": False,
        "freeze_authority_active": False,
        "warnings": [],
        "hard_fails": [],
    }


def good_evidence():
    return {
        "holder_read_ok": True,
        "holders": [{
            "owner": "WalletA",
            "pct": 1.25,
            "history_complete": True,
            "oldest_ts": NOW - 10 * 86400,
            "funders": ["FunderA"],
            "funder_known": True,
            "acquire_slot": 10,
            "acquire_known": True,
        }],
        "trade_read_ok": True,
        "trades": [
            {"signer": "Buyer", "side": "buy", "amount": 3},
            {"signer": "Seller", "side": "sell", "amount": 1},
        ],
        "lp_visible": True,
        "lp_burned_or_locked": True,
        "lp_detail": "chosen pool LP mint supply is 0",
        "creator": "CreatorWallet",
        "coin_creator": "CoinCreator",
        "creator_detail": "PumpSwap pool creator and coin_creator pubkeys",
        "top10_ex_pool_burn_pct": 6.5,
    }


def trade(**overrides):
    row = {
        "id": "paper-loss",
        "mint": "Mint111",
        "pool": "Pool111",
        "symbol": "AMD",
        "pnl_usd": -10.93,
        "exit_reason": "stop",
        "entry_price": 0.001419,
        "exit_price": 0.001233,
        "entry_ts": NOW - 6000,
        "exit_ts": NOW - 60,
        "entry_time": "2026-11-07T08:04:35+00:00",
        "exit_time": "2026-11-07T09:46:04+00:00",
        "entry_liquidity_usd": 103830.28,
        "exit_liquidity_usd": 96877.24,
        "entry_volume_usd": 3155033.57,
        "exit_volume_usd": 3157705.10,
        "entry_frac_of_ath": 0.3938,
        "top_human_pct": 0.148,
        "stop_fraction": 0.12,
        "mode": "forward:paper",
        "realized": True,
    }
    row.update(overrides)
    return row


class Market:
    def __init__(self, pair=None, error=None):
        self.pair = pair
        self.error = error
        self.rpc = None

    def dexscreener_pairs(self, mints):
        if self.error:
            raise RuntimeError(self.error)
        if self.pair is None:
            return [], ["no pair"]
        return [self.pair], []


def review(row, chain, evidence, market=None, attempts=2):
    return review_losing_trade(
        row,
        market if market is not None else Market({"mint": row["mint"], "pool": row["pool"], "market_cap_usd": 125000, "price_usd": row.get("exit_price")}),
        config(),
        review_token_fn=lambda *args, **kwargs: chain,
        gather_fn=lambda *args, **kwargs: evidence,
        attempts=attempts,
        now=NOW,
    )


class ReviewTextTests(unittest.TestCase):
    def test_clean_checks_are_listed_with_numbers_and_an_improve_line(self):
        before = (ROOT / "config.json").read_bytes()
        doc = review(trade(), good_chain(), good_evidence())
        self.assertTrue(review_is_complete(doc))
        self.assertEqual(doc["attempts"], 1)
        self.assertEqual(doc["factors"], [])
        self.assertEqual([c["name"] for c in doc["checks"]], list(CHECK_NAMES))
        self.assertTrue(all(c["result"] == "clean" for c in doc["checks"]))
        for name in CHECK_NAMES:
            self.assertIn(name, doc["text"])
            self.assertIn("CLEAN", doc["text"])
        self.assertIn("1.25%", doc["text"])
        self.assertIn("6.50%", doc["text"])
        self.assertIn("0.001419", doc["text"])
        self.assertIn("0.001233", doc["text"])
        self.assertIn("CreatorWallet", doc["text"])
        self.assertIn("$103,830.28", doc["text"])
        self.assertIn("$96,877.24", doc["text"])
        self.assertIn("Improve entries:", doc["text"])
        self.assertIn("Improve entries:", doc["improve_entries"])
        self.assertNotIn("59.41", doc["text"])
        self.assertEqual((ROOT / "config.json").read_bytes(), before)

    def test_concentration_is_a_factor_with_the_measured_percent(self):
        chain = good_chain()
        chain["top10_measured_pct"] = 59.41
        evidence = good_evidence()
        evidence["top10_ex_pool_burn_pct"] = 59.41
        doc = review(trade(), chain, evidence)
        self.assertTrue(review_is_complete(doc))
        factor = next(item for item in doc["factors"] if item["check"] == "holder_distribution")
        self.assertIn("59.41%", factor["text"])
        self.assertIn("40%", factor["text"])
        self.assertEqual(next(c for c in doc["checks"] if c["name"] == "holder_distribution")["result"], "flag")
        self.assertIn("Improve entries:", doc["improve_entries"])
        self.assertIn("59.41%", doc["improve_entries"])

    def test_liquidity_drop_and_unlocked_lp_are_factors(self):
        evidence = good_evidence()
        evidence["lp_burned_or_locked"] = False
        evidence["lp_detail"] = "LP mint StillMint still has supply 26780512735"
        row = trade(entry_liquidity_usd=1000, exit_liquidity_usd=700, entry_volume_usd=5000, exit_volume_usd=1000)
        doc = review(row, good_chain(), evidence)
        by_name = {c["name"]: c for c in doc["checks"]}
        self.assertEqual(by_name["liquidity"]["result"], "flag")
        self.assertIn("26780512735", by_name["liquidity"]["detail"])
        self.assertIn("$1,000.00", by_name["liquidity"]["detail"])
        self.assertIn("$700.00", by_name["liquidity"]["detail"])
        self.assertEqual(by_name["volume_profile"]["result"], "flag")
        self.assertIn("$5,000.00", by_name["volume_profile"]["detail"])
        self.assertIn("$1,000.00", by_name["volume_profile"]["detail"])

    def test_failed_source_is_retried_then_the_good_read_is_used(self):
        state = {"n": 0}

        def token_fn(*args, **kwargs):
            state["n"] += 1
            if state["n"] == 1:
                return {"status": "incomplete", "summary": "temporary 429"}
            return good_chain()

        def gather_fn(*args, **kwargs):
            if state["n"] == 1:
                return {
                    "holder_read_ok": False,
                    "holder_read_error": "temporary 429",
                    "trade_read_ok": False,
                    "trade_read_error": "temporary 429",
                    "lp_detail": "temporary 429",
                    "creator_detail": "temporary 429",
                }
            return good_evidence()

        class Flaky(Market):
            def dexscreener_pairs(self, mints):
                if state["n"] == 1:
                    return [], ["temporary 429"]
                return [{"mint": "Mint111", "pool": "Pool111", "market_cap_usd": 125000}], []

        doc = review_losing_trade(
            trade(), Flaky(), config(), review_token_fn=token_fn, gather_fn=gather_fn, attempts=2, now=NOW,
        )
        self.assertEqual(doc["attempts"], 2)
        self.assertNotIn("temporary 429", doc["text"])
        self.assertIn("6.50%", doc["text"])
        self.assertTrue(all(c["result"] == "clean" for c in doc["checks"]))

    def test_source_failure_after_retry_is_written_and_not_invented(self):
        def boom(*args, **kwargs):
            raise RuntimeError("rpc down")

        doc = review_losing_trade(
            trade(entry_price=None, exit_price=None, entry_liquidity_usd=None, exit_liquidity_usd=None, entry_volume_usd=None, exit_volume_usd=None),
            Market(error="rpc down"),
            config(),
            review_token_fn=boom,
            gather_fn=boom,
            attempts=2,
            now=NOW,
        )
        self.assertTrue(review_is_complete(doc))
        self.assertEqual(doc["attempts"], 2)
        self.assertTrue(doc["text"].strip())
        self.assertIn("Improve entries:", doc["improve_entries"])
        self.assertNotIn("59.41", doc["text"])
        self.assertNotIn("0.001419", doc["text"])
        by_name = {check["name"]: check for check in doc["checks"]}
        for name, check in by_name.items():
            self.assertEqual(check["result"], "failed", check)
            self.assertIn("2 attempts", check["detail"])
            if name == "price_mcap_path":
                self.assertIn("not recorded", check["detail"])
            else:
                self.assertIn("rpc down", check["detail"])

    def test_empty_reviewer_result_is_replaced_with_a_written_failure(self):
        from post_loss_review import failed_review
        doc = failed_review(trade(), "post-loss review returned an incomplete document")
        self.assertTrue(review_is_complete(doc))
        self.assertIn("incomplete", doc["text"])
        self.assertTrue(doc["improve_entries"].startswith("Improve entries:"))
        self.assertEqual(len(doc["checks"]), len(CHECK_NAMES))


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = json.loads((ROOT / "config.json").read_text())
        self.config["tiered_selection_enabled"] = False
        self.memory = Memory(self.root)
        self.now = time.time()

    def tearDown(self):
        self.tmp.cleanup()

    def test_loss_is_reviewed_before_close_and_blocks_the_next_entry_until_then(self):
        account = PaperAccount(self.root, self.config)
        account.data["positions"] = [{
            "id": "paper-open", "mode": "forward:paper", "realized": False, "mint": "M", "pool": "P",
            "symbol": "AMD", "entry_ts": self.now - 100, "entry_time": iso(self.now - 100),
            "entry_price": 1, "notional_usd": 10, "cost_rate": 0.011, "stop_fraction": 0.12,
            "target_fraction": 0.35, "max_hold_seconds": 57600,             "entry_liquidity_usd": 10000,
            "entry_volume_usd": 8000, "top_human_pct": 1.2, "dex_url": "https://dexscreener.com/solana/P",
        }]
        account.data["cash_usd"] = 990
        account.save()
        market = type("M", (), {"dexscreener_pairs": lambda self, mints: ([{"mint": "M", "pool": "P", "price_usd": 0.8, "liquidity_usd": 9000, "volume_24h_usd": 7000, "market_cap_usd": 40000}], [])})()
        order = []

        def reviewer(row):
            order.append("review")
            self.assertEqual(row["symbol"], "AMD")
            self.assertLess(row["pnl_usd"], 0)
            return review(row, good_chain(), good_evidence(), Market({"mint": "M", "pool": "P", "market_cap_usd": 40000, "price_usd": 0.8}))

        chat = LiveChat(self.root / "chat.json")
        chat.data["started"] = self.now - 1000

        def close(row):
            order.append("close")
            self.assertTrue(review_is_complete(row.get("post_loss_review")))
            chat.record({"kind": "trade_close", "agent": "Backtester", "text": "realized", "time": iso(time.time()),
                         "trade": row, "is_live_close": True, "historical": False}, allow_journal_replay=True)

        account.manage(market, self.memory, lambda *args: None, close, self.now, loss_review=reviewer)
        self.assertEqual(order, ["review", "close"])
        stored = account.data["closed"][0]["post_loss_review"]
        self.assertTrue(review_is_complete(stored))
        self.assertIn("POST-LOSS REVIEW", stored["text"])
        ledger = self.memory.recent_trades(1)[0]
        self.assertEqual(ledger["post_loss_review"]["text"], stored["text"])
        self.assertEqual(self.memory.data["loss_reviews"][0]["trade_id"], "paper-open")
        self.assertIn("POST-LOSS REVIEW", (self.root / "LESSONS.md").read_text())
        self.assertEqual(self.memory.data["rules"], [])
        message = next(item for item in chat.data["messages"] if item["kind"] == "trade_review")
        self.assertIn("POST-LOSS REVIEW", message["text"])
        self.assertIn("Improve entries:", message["text"])
        self.assertIn("How to improve future entries", message["text"])
        account.manage(market, self.memory, lambda *args: None, close, self.now, loss_review=reviewer)
        self.assertEqual(order, ["review", "close"])

    def test_missing_review_blocks_entry_and_a_written_failure_clears_the_latch(self):
        account = PaperAccount(self.root, self.config)
        account.data["closed"] = [{
            "id": "paper-old", "symbol": "AMD", "mint": "M", "pnl_usd": -10.93, "exit_reason": "stop",
            "exit_time": iso(self.now - 10), "entry_time": iso(self.now - 100), "realized": True,
            "mode": "forward:paper", "review_delivered": True,
        }]
        account.save()
        messages = []
        token = dict(mint="A", pool="P", symbol="TEST", name="Test", eligible=True, in_entry_zone=True,
                     price_usd=30, seed_ath=100, bars=[dict(t=self.now - 3700, o=28, c=30, h=31, l=27)],
                     safety=dict(status="pass", top_human_pct=1), liquidity_usd=50000, volume_24h_usd=50000)
        market = type("Mkt", (), {"source_status": {}})()
        self.assertIsNone(account.try_entry([token], market, self.memory, lambda *args: messages.append(args), self.now))
        self.assertIn("POST-LOSS REVIEW REQUIRED", messages[-1][1])
        self.assertIn("AMD", messages[-1][1])
        account.loss_review = lambda row: {}
        done = account.complete_loss_reviews(self.memory, lambda row: None)
        self.assertEqual(done, 1)
        self.assertTrue(review_is_complete(account.data["closed"][0]["post_loss_review"]))
        self.assertIn("incomplete", account.data["closed"][0]["post_loss_review"]["text"])
        messages.clear()
        opened = account.try_entry([token], market, self.memory, lambda *args: messages.append(args), self.now)
        self.assertIsNotNone(opened)
        self.assertFalse(any("POST-LOSS REVIEW REQUIRED" in args[1] for args in messages))

    def test_backfill_rewrites_the_empty_trade_review_without_a_second_message(self):
        account = PaperAccount(self.root, self.config)
        closed = trade(id="paper-278e35c1222548f0b825bd22197c6181", review_delivered=True, realized=True, mode="forward:paper")
        account.data["closed"] = [closed]
        account.save()
        chat = LiveChat(self.root / "chat.json")
        chat.data["messages"] = [{
            "agent": "Backtester", "kind": "trade_review", "trade_id": closed["id"],
            "time": "2026-11-07T04:46:05-05:00",
            "text": "TRADE REVIEW / AMD / loss / P&L $-10.93 / exit stop.\nHow to improve future entries: No new entry filter is identified from this close alone.",
        }]
        chat.data["trade_reviews"] = [closed["id"]]
        chat.data["reviewed"] = [closed["id"]]
        chat.save()
        calls = []
        account.loss_review = lambda row: calls.append(row["id"]) or review(row, good_chain(), good_evidence())
        account.loss_review_refresh = lambda row: chat.rewrite_trade_review(row)
        done = account.complete_loss_reviews(self.memory, lambda row: self.fail("backfill must not redeliver the close"))
        self.assertEqual(done, 1)
        self.assertEqual(calls, [closed["id"]])
        reviews = [item for item in chat.data["messages"] if item["kind"] == "trade_review"]
        self.assertEqual(len(reviews), 1)
        self.assertIn("POST-LOSS REVIEW", reviews[0]["text"])
        self.assertIn("1.25%", reviews[0]["text"])
        self.assertIn("Improve entries:", reviews[0]["text"])
        self.assertEqual(reviews[0]["time"], "2026-11-07T04:46:05-05:00")
        self.assertEqual(chat.data["checklist"], [])
        self.assertEqual(account.complete_loss_reviews(self.memory, lambda row: None), 0)
        self.assertEqual(calls, [closed["id"]])

    def test_winning_close_does_not_run_the_post_loss_review(self):
        account = PaperAccount(self.root, self.config)
        account.data["positions"] = [{
            "id": "paper-win", "mode": "forward:paper", "realized": False, "mint": "M", "pool": "P",
            "symbol": "WIN", "entry_ts": self.now - 100, "entry_time": iso(self.now - 100),
            "entry_price": 1, "notional_usd": 10, "cost_rate": 0, "stop_fraction": 0.12,
            "target_fraction": 0.35, "max_hold_seconds": 57600, "dex_url": "https://dexscreener.com/solana/P",
        }]
        account.data["cash_usd"] = 990
        account.save()
        market = type("M", (), {"dexscreener_pairs": lambda self, mints: ([{"mint": "M", "pool": "P", "price_usd": 1.4, "liquidity_usd": 1, "volume_24h_usd": 1}], [])})()
        calls = []
        account.manage(market, self.memory, lambda *args: None, lambda row: None, self.now, loss_review=lambda row: calls.append(row))
        self.assertEqual(calls, [])
        self.assertGreater(account.data["closed"][0]["pnl_usd"], 0)
        self.assertNotIn("post_loss_review", account.data["closed"][0])

    def test_site_keeps_the_review_chat_box_and_shows_the_stored_review(self):
        page = (ROOT / "index.html").read_text()
        self.assertIn("#liveChat{max-height:360px!important", page)
        self.assertIn("#liveChat{max-height:280px!important", page)
        self.assertIn("e.kind==='trade_review'", page)
        self.assertIn("post_loss_review", page)
        self.assertIn("loss_reviews", page)
        live = (ROOT / "live/index.html").read_text()
        self.assertIn("#liveChat{max-height:none!important", live)
        self.assertIn("post_loss_review", live)


if __name__ == "__main__":
    unittest.main()
