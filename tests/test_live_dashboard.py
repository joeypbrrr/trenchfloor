import json
import tempfile
import time
import unittest
from pathlib import Path
from live_chat import LiveChat

class ChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "chat.json"
        self.chat = LiveChat(self.path)
        self.chat.data["started"] = time.time() - 3600
    def tearDown(self):
        self.tmp.cleanup()
    def close(self, **overrides):
        trade = {"id": "test-forward", "mode": "forward:paper", "realized": True,
                 "entry_ts": time.time()-600, "exit_ts": time.time()-1,
                 "pnl_usd": -8.5, "symbol": "TEST", "exit_reason": "stop"}
        trade.update(overrides)
        return {"agent":"Backtester", "kind":"trade_close", "time":"2026-11-07T04:00:00+00:00", "text":"test close", "is_live_close":True,"historical":False,"trade":trade}
    def test_empty_is_empty(self):
        self.assertEqual(self.chat.data["messages"], [])
        self.assertEqual(self.chat.data["checklist"], [])
    def test_backtest_never_reviewed(self):
        for overrides in ({"mode":"legacy:backtest"}, {"sample":"out_of_sample"}, {"exit_ts":time.time()+3600}, {"exit_ts":time.time()-600}, {"entry_ts":time.time()-7200}):
            self.assertEqual(self.chat.record(self.close(**overrides)), [])
        e=self.close();e["historical"]=True
        self.assertEqual(self.chat.record(e), [])
        self.assertEqual(self.chat.data["checklist"], [])
    def test_real_forward_loss_reviewed_once(self):
        e=self.close(); messages=self.chat.record(e)
        self.assertGreaterEqual(len(messages),6)
        self.assertTrue(any("missing" in m["text"] for m in messages))
        self.assertEqual(self.chat.data["checklist"][0]["supporting_losses"],1)
        self.assertEqual(self.chat.record(e), [])
        restored=LiveChat(self.path)
        self.assertEqual(restored.data["checklist"][0]["supporting_losses"],1)
        self.assertIn("primary", restored.data["checklist"][0]["status"].lower())
        self.assertTrue(restored.data["checklist"][0]["rules"])
    def test_profit_not_reviewed(self):
        # Wins do not create loss-checklist rules. They do get one trade review.
        messages=self.chat.record(self.close(pnl_usd=4, exit_reason='target'))
        self.assertEqual([m['kind'] for m in messages], ['trade_review'])
        self.assertEqual(self.chat.data['checklist'], [])
        self.assertNotIn('How to avoid similar losses', messages[0]['text'])
        self.assertEqual(self.chat.record(self.close(pnl_usd=4, exit_reason='target')), [])
    def test_one_trade_review_per_close(self):
        loss=self.chat.record(self.close(stop_fraction=0.12, entry_liquidity_usd=100, exit_liquidity_usd=70))
        reviews=[m for m in loss if m['kind']=='trade_review']
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]['agent'], 'Backtester')
        text=reviews[0]['text']
        for part in ('What went right', 'What went wrong', 'Red flags', 'How to improve future entries', 'How to avoid similar losses', 'exit stop'):
            self.assertIn(part, text)
        self.assertIn('liquidity', text)
        self.assertIn('12%', text)
        self.assertNotIn('http', text.lower())
        win=self.chat.record(self.close(id='win-1', pnl_usd=4.5, exit_reason='target', entry_price=1, exit_price=1.4,
            hard_rug_checks=[{'name':'sellable_not_honeypot','pass':True}]))
        self.assertEqual(len(win), 1)
        self.assertEqual(win[0]['kind'], 'trade_review')
        self.assertIn('sellable_not_honeypot', win[0]['text'])
        self.assertNotIn('How to avoid similar losses', win[0]['text'])
        self.assertEqual(self.chat.data['checklist'][0]['supporting_losses'], 1)
        historical=self.close(id='hist-win', pnl_usd=9)
        historical['historical']=True
        self.assertEqual(self.chat.record(historical), [])
    def test_independent_losses_increment_support(self):
        self.chat.record(self.close(id="loss-a"));self.chat.record(self.close(id="loss-b"))
        self.assertEqual(self.chat.data["checklist"][0]["supporting_losses"],2)
    def test_messages_survive_restart(self):
        self.chat.record({"agent":"Risk Manager","kind":"safety","text":"actual result","time":"now"})
        self.assertEqual(LiveChat(self.path).data["messages"][0]["text"],"actual result")

if __name__ == "__main__":
    unittest.main()
