import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from forward_paper import PaperAccount, iso
from daily_stop import DailyStop, ET
from live_chat import LiveChat
from memory import Memory, atomic_json

class ForwardPaperTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.config=json.loads((Path(__file__).resolve().parents[1]/'config.json').read_text())
        self.config['tiered_selection_enabled']=False  # legacy single-slot tests
        self.now=time.time()
        self.mem=Memory(self.root)
        self.messages=[]
        self.post=lambda *args:self.messages.append(args)
        self.market=type('M',(),{'source_status':{}})()
        self.token=dict(mint='A',pool='P',symbol='TEST',name='Test',eligible=True,in_entry_zone=True,
                        price_usd=30,seed_ath=100,bars=[dict(t=self.now-3700,o=28,c=30,h=31,l=27)],
                        safety=dict(status='pass',top_human_pct=1),liquidity_usd=50000,volume_24h_usd=50000)

    def test_entry_rolling_hour_restart_and_sizing(self):
        a=PaperAccount(self.root,self.config)
        t=a.try_entry([self.token],self.market,self.mem,self.post,self.now)
        self.assertIsNotNone(t);self.assertEqual(t['notional_usd'],100)
        self.assertEqual(a.snapshot()['cash_usd'],900)
        a.data['positions']=[];a.save()  # an exit does not clear the rolling entry latch
        b=PaperAccount(self.root,self.config)
        self.assertIsNone(b.try_entry([self.token],self.market,self.mem,self.post,self.now+3599))
        self.assertEqual(b.data['last_entry_ts'],self.now)
        self.assertIsNotNone(b.try_entry([self.token],self.market,self.mem,self.post,self.now+3600))

    def test_no_bypass_of_missing_safety_or_green_confirmation(self):
        a=PaperAccount(self.root,self.config)
        bad={**self.token,'safety':{'status':'incomplete','top_human_pct':None}}
        self.assertIsNone(a.try_entry([bad],self.market,self.mem,self.post,self.now))
        bad={**self.token,'bars':[dict(t=self.now-3700,o=31,c=30,h=32)]}
        self.assertIsNone(a.try_entry([bad],self.market,self.mem,self.post,self.now))
        self.assertEqual(a.snapshot()['balance_usd'],1000)

    def test_close_loss_review_replay_once_even_while_daily_halted(self):
        chat=LiveChat(self.root/'data/cache/test-chat.json');chat.data['started']=self.now-1
        close=lambda t:chat.record(dict(kind='trade_close',agent='Backtester',text='realized',time=iso(time.time()),
                                        trade=t,is_live_close=True,historical=False),allow_journal_replay=True)
        a=PaperAccount(self.root,self.config)
        a.try_entry([self.token],self.market,self.mem,self.post,self.now-0.5)
        # Simulate an existing persistent daily halt: it must never block an exit.
        today=datetime.now(ET).date().isoformat()
        atomic_json(self.root/'data/daily_stop.json',{'modes':{'forward:paper':{'date_et':today,'halted':True,'hit_at':iso(self.now)}}})
        self.market.dexscreener_pairs=lambda m:([dict(mint='A',pool='P',price_usd=20,liquidity_usd=40000,volume_24h_usd=40000)],[])
        a.manage(self.market,self.mem,self.post,close,time.time())
        self.assertEqual(len(a.data['closed']),1);self.assertFalse(a.data['positions'])
        self.assertEqual(self.mem.index['trade_count'],1)
        self.assertTrue(chat.data['checklist']); n=len(chat.data['messages'])
        b=PaperAccount(self.root,self.config);b.reconcile(self.mem,close)
        self.assertEqual(len(chat.data['messages']),n)
        self.assertIsNone(b.try_entry([self.token],self.market,self.mem,self.post))

    def test_daily_stop_forward_realized_only_latch_and_midnight(self):
        now=datetime.now(timezone.utc)
        t=dict(id='win',mode='forward:paper',realized=True,mint='A',entry_time=iso(self.now-10),exit_time=now.isoformat(),entry_price=1,exit_price=4,notional_usd=100,pnl_usd=300)
        unclosed={**t,'mint':'B','realized':False,'pnl_usd':10000}
        historical={**t,'mint':'C','mode':'legacy:backtest','pnl_usd':10000}
        atomic_json(self.root/'data/ledger/2026-11-06.json',{'trades':[t,{**t,'id':'duplicate'},unclosed,historical]})
        d=DailyStop(self.root);s=d.status(self.config,now)
        self.assertTrue(s['halted']);self.assertEqual(s['realized_pnl_usd'],300);self.assertEqual(s['realized_fills'],1)
        atomic_json(self.root/'data/ledger/2026-11-06.json',{'trades':[]})
        self.assertTrue(DailyStop(self.root).status(self.config,now)['halted'])
        self.assertFalse(d.status(self.config,datetime.fromisoformat(s['reset_at']))['halted'])

if __name__=='__main__':unittest.main()

class PublicationAndFeeTests(unittest.TestCase):
    def test_unavailable_global_fees_skipped_on_legacy_dex_only(self):
        import research
        from sources import SKIP_MINTS
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);mem=Memory(root)
            cfg=json.loads((Path(research.__file__).parent/'config.json').read_text())
            c=dict(mint='A',symbol='A',quote_mint=next(iter(SKIP_MINTS)),created_ts=time.time()-36000,
                   liquidity_usd=50000,volume_24h_usd=20000,market_cap_usd=6000)
            with patch.object(research,'MEMORY',mem),patch.object(research,'post') as post:
                passed,_,_=research.screen([c],cfg)
                self.assertEqual(len(passed),1)
                self.assertIn('SKIPPED',post.call_args[0][1])

    def test_only_forced_end_of_cycle_publishes(self):
        import research
        with patch.object(research,'NO_PUBLISH',False),patch.object(research,'PUBLISHING',False), \
             patch.object(research,'FEED_DIRTY',True),patch.object(research,'load_config',return_value={'publish_once_per_cycle':True}), \
             patch.object(research,'publish',return_value={'published':None}) as pub:
            research.maybe_publish_feed(force=True)
            research.maybe_publish_full(force=False)
            pub.assert_not_called()
            research.maybe_publish_full(force=True)
            self.assertEqual(pub.call_count,1)
