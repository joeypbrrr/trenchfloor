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
        self.assertEqual(self.chat.record(self.close(pnl_usd=4)), [])
    def test_independent_losses_increment_support(self):
        self.chat.record(self.close(id="loss-a"));self.chat.record(self.close(id="loss-b"))
        self.assertEqual(self.chat.data["checklist"][0]["supporting_losses"],2)
    def test_messages_survive_restart(self):
        self.chat.record({"agent":"Risk Manager","kind":"safety","text":"actual result","time":"now"})
        self.assertEqual(LiveChat(self.path).data["messages"][0]["text"],"actual result")

if __name__ == "__main__":
    unittest.main()
