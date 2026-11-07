import json,time,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from memory import Memory,atomic_json
from sources import ResilientRpcClient,SKIP_MINTS
from safety import review_token,TOKEN_LEGACY
from traded_mints import TradedMints
from forward_paper import PaperAccount
from tiers import evaluate,tier_reason,hard_review

class TierTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.config=json.loads((Path(__file__).resolve().parents[1]/'config.json').read_text());self.now=time.time()
  self.mem=Memory(self.root);self.lines=[];self.post=lambda *a:self.lines.append(a)
  self.market=type('M',(),{'source_status':{}})()
  self.safety=dict(status='pass',summary='PASS',hard_rug_pass=True,hard_rug_checks=[dict(name='all',pass_=True)],top_human_pct=1,top10_measured_pct=5)
  self.safety['hard_rug_checks']=[{'name':'all','pass':True}]
  self.token=dict(mint='A',pool='P',symbol='TEST',name='Test',price_usd=1,quote_mint=next(iter(SKIP_MINTS)),created_ts=self.now-7200,
                  liquidity_usd=20000,volume_24h_usd=30000,market_cap_usd=100000,ath_frac=.3,score=10,eligible=True,tier_eligible=True,entry_tier='fallback',safety=self.safety)
 def test_fallback_entry_50_and_registry_never_reenter(self):
  a=PaperAccount(self.root,self.config);t=a.try_entry([self.token],self.market,self.mem,self.post,self.now)
  self.assertIsNotNone(t);self.assertEqual(t['notional_usd'],50);self.assertEqual(t['tier'],'fallback')
  self.assertIn('A',TradedMints(self.root));self.assertIn('A',json.loads((self.root/'data/traded_mints.json').read_text())['mints'])
  a.data['positions']=[];a.save()
  b=PaperAccount(self.root,self.config)
  self.assertIsNone(b.try_entry([self.token],self.market,self.mem,self.post,self.now+3601))
 def test_no_entry_for_failed_or_unknown_hard_check(self):
  a=PaperAccount(self.root,self.config)
  for flag in (False,None):
   t={**self.token,'safety':{**self.safety,'hard_rug_pass':flag}}
   self.assertIsNone(a.try_entry([t],self.market,self.mem,self.post,self.now))
 def test_new_mint_hourly_gate_open_positions_do_not_block_next_hour(self):
  a=PaperAccount(self.root,self.config)
  self.assertIsNotNone(a.try_entry([self.token],self.market,self.mem,self.post,self.now))
  second={**self.token,'mint':'B'}
  self.assertIsNone(a.try_entry([second],self.market,self.mem,self.post,self.now+3599))
  self.assertIsNotNone(a.try_entry([second],self.market,self.mem,self.post,self.now+3600))
  self.assertEqual(len(a.data['positions']),2)
 def test_primary_preferred_and_fallback_only_when_primary_empty(self):
  with patch('tiers.hard_review',return_value=self.safety):
   r=evaluate([self.token],self.market,self.config,self.post,lambda *a:True,self.root)
   self.assertEqual(r['primary'],1);self.assertEqual(r['tier'],'primary')
   low={**self.token,'liquidity_usd':2000}
   r=evaluate([low],self.market,self.config,self.post,lambda *a:True,self.root)
   self.assertEqual(r['primary'],0);self.assertEqual(r['fallback'],1);self.assertEqual(r['tier'],'fallback')
 def test_traded_removed_before_scoring_both_tiers(self):
  TradedMints(self.root).add(dict(mint='A',id='f',mode='forward:paper'))
  with patch('tiers.hard_review') as hard,patch('tiers.score') as score:
   r=evaluate([self.token],self.market,self.config,self.post,lambda *a:True,self.root)
   self.assertEqual(r['excluded_traded'],1);hard.assert_not_called();score.assert_not_called()
 def test_registry_only_reconstructs_forward_journal_not_old_backtests(self):
  atomic_json(self.root/'data/paper_account.json',{'positions':[dict(mode='forward:paper',mint='A')],'closed':[dict(mode='legacy:backtest',mint='OLD')]})
  r=TradedMints(self.root);self.assertIn('A',r);self.assertNotIn('OLD',r)
 def test_hard20_and_tier15(self):
  self.assertIsNone(tier_reason(self.token,self.config['tiers']['primary']))
  c={**self.token,'safety':{**self.safety,'top_human_pct':19}}
  self.assertIsNotNone(tier_reason(c,self.config['tiers']['primary']))
  self.assertIsNone(tier_reason(c,self.config['tiers']['fallback']))
 def test_daily_halt_overrides_minimum(self):
  from datetime import datetime
  from daily_stop import ET
  atomic_json(self.root/'data/daily_stop.json',{'modes':{'forward:paper':{'date_et':str(datetime.now(ET).date()),'halted':True}}})
  self.assertIsNone(PaperAccount(self.root,self.config).try_entry([self.token],self.market,self.mem,self.post))
 def test_lp_or_report_unknown_is_hard_reject(self):
  from sources import SourceError
  with patch('tiers.http_json',side_effect=SourceError('no LP data')):
   s=hard_review(self.token,self.market,self.config)
   self.assertFalse(s['hard_rug_pass']);self.assertEqual(s['status'],'incomplete')

class OwnerLookupTests(unittest.TestCase):
 def test_successful_null_native_owner_is_wallet_not_unknown_or_excluded(self):
  mint={'owner':TOKEN_LEGACY,'data':{'parsed':{'type':'mint','info':{'mintAuthority':None,'freezeAuthority':None}}}}
  class RPC:
   def call(self,method,params):
    if method=='getAccountInfo':return {'value':mint}
    if method=='getTokenSupply':return {'value':{'amount':'1000','decimals':0}}
    if method=='getTokenLargestAccounts':return {'value':[{'address':'TA','amount':'100'}]}
    if method=='getMultipleAccounts':
     if params[1]['encoding']=='jsonParsed':return {'value':[{'data':{'parsed':{'info':{'owner':'ABSENT','tokenAmount':{'amount':'100'}}}}}]}
     return {'value':[None]}
  s=review_token(RPC(),'M',None,20,require_complete=True,aggregate_holders=True,conservative_tail=False)
  self.assertEqual(s['status'],'pass');self.assertEqual(s['top_human_pct'],10);self.assertEqual(s['owner_lookup']['confirmed_absent_native_accounts'],1)
 def test_truncated_batch_retries_next_endpoint(self):
  rpc=ResilientRpcClient(['a','b'],0,4)
  with patch('sources.http_json',side_effect=[({'result':{'value':[]}},200),({'result':{'value':[None]}},200)]):
   s=rpc.call('getMultipleAccounts',[['X'],{'encoding':'base64'}])
  self.assertEqual(s['value'],[None]);self.assertEqual(rpc.calls,2);self.assertEqual(rpc.used,['b'])
