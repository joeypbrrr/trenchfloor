import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from candidate_sources import fee_filter_reason, gmgn_request, parse_gmgn
from daily_stop import DailyStop, ET, mode_for
from memory import atomic_json
from sources import ResilientRpcClient, SourceError
import research


class DailyStopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 11, 6, 23, 0, tzinfo=ET)
        self.config = {'daily_stop_enabled': True, 'daily_profit_stop_usd': 300, 'candidate_source': 'gmgn_substitute'}

    def tearDown(self):
        self.temp.cleanup()

    def trade(self, name, pnl, **extra):
        return dict(id=name, mint=name, entry_time=(self.now-timedelta(hours=1)).isoformat(), exit_time=self.now.isoformat(),
                    entry_price=1, exit_price=2, notional_usd=100, pnl_usd=pnl, mode=mode_for(self.config), **extra)

    def write(self, trades):
        atomic_json(self.root/'data/ledger/2026-11-06.json', {'trades': trades})

    def test_exact_threshold_persists_and_resets_at_midnight(self):
        self.write([self.trade('a',300)])
        self.assertTrue(DailyStop(self.root).status(self.config, self.now)['halted'])
        self.write([])  # latch survives corrections/later losses/restart
        self.assertTrue(DailyStop(self.root).status(self.config, self.now)['halted'])
        self.assertFalse(DailyStop(self.root).status(self.config, self.now+timedelta(hours=2))['halted'])

    def test_dedupe_future_wrong_mode_and_candle_end(self):
        t=self.trade('a',150)
        duplicate={**t,'id':'second-variant','strategy_id':'another'}
        future={**self.trade('b',300),'exit_ts':0,'exit_time':(self.now+timedelta(hours=1)).isoformat()}
        other={**self.trade('c',300),'mode':'legacy:backtest'}
        self.write([t, duplicate, future, other])
        s=DailyStop(self.root).status(self.config,self.now)
        self.assertEqual(s['realized_pnl_usd'],150)
        self.assertEqual(s['realized_fills'],1)
        self.assertFalse(s['halted'])

    def test_latches_on_intraday_peak_after_later_loss(self):
        first={**self.trade('a',310),'exit_time':(self.now-timedelta(minutes=1)).isoformat()}
        self.write([first,self.trade('b',-100)])
        s=DailyStop(self.root).status(self.config,self.now)
        self.assertTrue(s['halted']);self.assertEqual(s['realized_pnl_usd'],210)

    def test_off_is_inert_and_does_not_persist(self):
        self.write([self.trade('a',300)])
        s=DailyStop(self.root).status({**self.config,'daily_stop_enabled':False},self.now)
        self.assertFalse(s['halted']);self.assertFalse((self.root/'data/daily_stop.json').exists())

    def test_gate_before_vote_no_future_fill_import_and_per_fill_halt(self):
        # Integration test two proposed wins in today's simulation. First reaches
        # target; second MUST NOT invoke the team or enter the shared ledger.
        from memory import Memory
        from backtest import variant_catalog
        cfg=json.loads((research.ROOT/'config.json').read_text())
        cfg.update(self.config)
        cfg['limits']['variants_per_cycle']=1
        v=variant_catalog()[0]
        trades=[self.trade('a',300),self.trade('b',300)]
        for t in trades:
            t.update(strategy_id=v['id'],symbol='TEST',name='Test',entry_ts=self.now.timestamp()-3600,
                     exit_ts=self.now.timestamp()-3600,entry_price=1,exit_price=2)
        mem=Memory(self.root)
        market=type('Market',(),{'source_status':{}})()
        def vote(trade,*args):
            trade.update(dex_url='',gmgn_url='')
            return dict(approved=True,approve=5,reject=0,abstain=1,tally='5/6',rule='test',vetoes=[],votes=[],proposed_by='Data Scout')
        with patch.object(research,'ROOT',self.root),patch.object(research,'MEMORY',mem),patch.object(research,'MARKET',market),\
             patch.object(research,'post'),patch.object(research,'update'),patch.object(research,'simulate',return_value=trades),\
             patch.object(research,'daily_stop_status',side_effect=lambda config: DailyStop(self.root).status(config,self.now)),\
             patch('team.team_review',side_effect=vote) as voting:
            result=research.run_variants([{'mint':'a','bars':[{'t':self.now.timestamp()-7200},{'t':self.now.timestamp()}]}],cfg)
            self.assertEqual(voting.call_count,1)
            self.assertEqual(result['team_taken'],1)


class SourcesTests(unittest.TestCase):
    def test_unknown_fees_fail_closed_and_proxy_requires_opt_in(self):
        row={'fees_proxy_sol':2,'fees_proxy_basis':'PROXY'}
        self.assertIn('unknown',fee_filter_reason(row,{}))
        self.assertIsNone(fee_filter_reason(row,{'fee_proxy_enabled':True}))
        self.assertIsNone(fee_filter_reason({'global_fees_sol':1.5},{}))
        self.assertIsNotNone(fee_filter_reason({'global_fees_sol':1.49},{}))
        self.assertIsNotNone(fee_filter_reason({'global_fees_sol':float('nan')},{}))

    def test_average_gas_or_raw_ambiguous_total_is_not_global_sol(self):
        rows=parse_gmgn([{'address':'a','gas_fee':4,'total_fee':10}], 'gmgn:trending')
        self.assertIsNone(rows[0]['global_fees_sol'])

    def test_gmgn_without_key_never_calls_network(self):
        with patch.dict('os.environ',{},clear=True),patch('candidate_sources.http_json') as http:
            with self.assertRaises(SourceError): gmgn_request('/v1/market/rank')
            http.assert_not_called()

    def test_empty_holder_list_is_incomplete_in_new_modes(self):
        from safety import review_token
        rpc=type('RPC',(),{})()
        rpc.call=lambda method,params: {
            'getAccountInfo': {'value': {'data': {'parsed': {'type': 'mint', 'info': {'mintAuthority':None,'freezeAuthority':None}}}}},
            'getTokenSupply': {'value': {'amount':'1000','decimals':0}},
            'getTokenLargestAccounts': {'value': []}
        }[method]
        self.assertEqual(review_token(rpc,'M',None,require_complete=True)['status'],'incomplete')

    def test_rpc_enumerates_all_endpoints_and_respects_budget(self):
        rpc=ResilientRpcClient(['a','b','c'],0,3)
        with patch('sources.http_json',side_effect=[SourceError('failed'),SourceError('failed'),({'result':{'value':1}},200)]) as http:
            self.assertEqual(rpc.call('method',[]),{'value':1})
            self.assertEqual([c.args[0] for c in http.call_args_list],['a','b','c'])
            self.assertEqual(rpc.call('method',[]),{'value':1})
            with self.assertRaises(SourceError):rpc.call('other',[])

    def test_market_cap_fdv_not_accepted_for_new_source(self):
        cfg=json.loads((research.ROOT/'config.json').read_text())
        row={'mint':'a','symbol':'A','quote_mint':'So11111111111111111111111111111111111111112',
             'created_ts':research.time.time()-86400,'liquidity_usd':20000,'volume_24h_usd':10000,'fdv_usd':20000}
        filters={**cfg['filters'],'min_market_cap_usd':6000,'strict_market_cap':True}
        self.assertEqual(research._filter_reason(row,filters,research.time.time()),'market cap unknown')

if __name__=='__main__':unittest.main()
