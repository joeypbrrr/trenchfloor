import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs,urlparse
from sources import SourceError
from tiers import hard_review,tier_reason,fallback_penalties,evaluate
from checklist_rules import normalize_item,violations
from live_chat import LiveChat
from forward_paper import PaperAccount
from memory import Memory

class PolicyRevisionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.cfg=json.loads((Path(__file__).resolve().parents[1]/'config.json').read_text())
  self.c=dict(mint='A',pool='P',price_usd=1,liquidity_usd=20000,volume_24h_usd=30000,market_cap_usd=100000,created_ts=time.time()-7200,quote_mint='So11111111111111111111111111111111111111112',symbol='TEST',name='Test',ath_frac=.3,score=10,tier_eligible=True,entry_tier='fallback')
 def rpc(self,mint_auth=None,freeze_auth=None,extensions=None):
  class RPC:
   def call(self,method,params):
    if method=='getAccountInfo':return {'value':{'owner':'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb','data':{'parsed':{'type':'mint','info':dict(mintAuthority=mint_auth,freezeAuthority=freeze_auth,decimals=6,extensions=extensions or [])}}}}
    if method=='getTokenSupply':return {'value':{'amount':'1000','decimals':6}}
    if method=='getTokenLargestAccounts':return {'value':[{'address':'TA','amount':'800'}]}
    if method=='getMultipleAccounts':
     if params[1]['encoding']=='jsonParsed':return {'value':[{'data':{'parsed':{'info':{'owner':'W','tokenAmount':{'amount':'800'}}}}}]}
     return {'value':[None]}
  return RPC()
 def http(self,url,**kwargs):
  if '/quote?' in url:
   q=parse_qs(urlparse(url).query)
   return dict(inputMint='A',outputMint='So11111111111111111111111111111111111111112',inAmount=q['amount'][0],outAmount='1000',routePlan=[{'swapInfo':{'ammKey':'P'}}]),200
  return {'mint':'A','markets':[]},200
 def market(self,rpc):return type('M',(),{'rpc':rpc,'source_status':{}})()
 def test_exact_three_hard_checks_soft_holder_lp_extensions_never_hard_veto(self):
  m=self.market(self.rpc(extensions=[{'extension':'transferFeeConfig'}]))
  with patch('tiers.http_json',side_effect=self.http):s=hard_review(self.c,m,self.cfg)
  self.assertTrue(s['hard_rug_pass']);self.assertEqual(len(s['hard_rug_checks']),3)
  self.assertEqual(set(x['name'] for x in s['hard_rug_checks']),{'mint_authority_revoked','freeze_authority_revoked','sellable_not_honeypot'})
  self.assertEqual(s['top_human_pct'],80)
  c={**self.c,'safety':s}
  self.assertIsNotNone(tier_reason(c,self.cfg['tiers']['primary']))
  self.assertIsNone(tier_reason(c,self.cfg['tiers']['fallback']))
  self.assertGreater(len(fallback_penalties(c,self.cfg)),1)
 def test_active_mint_and_freeze_still_hard_reject(self):
  for args in ({'mint_auth':'DEV'},{'freeze_auth':'DEV'}):
   with patch('tiers.http_json',side_effect=self.http):s=hard_review(self.c,self.market(self.rpc(**args)),self.cfg)
   self.assertFalse(s['hard_rug_pass'])
 def test_unknown_authorities_and_no_route_reject(self):
  class Broken:
   def call(self,*a):raise SourceError('RPC unavailable')
  with patch('tiers.http_json',side_effect=self.http):s=hard_review(self.c,self.market(Broken()),self.cfg)
  self.assertFalse(s['hard_rug_pass'])
  def no_route(url,**kw):
   if '/quote?' in url:return {'error':'no route'},200
   return self.http(url,**kw)
  with patch('tiers.http_json',side_effect=no_route):s=hard_review(self.c,self.market(self.rpc()),self.cfg)
  self.assertFalse(s['hard_rug_pass'])
 def test_known_pause_unsellable_despite_optimistic_quote(self):
  with patch('tiers.http_json',side_effect=self.http):s=hard_review(self.c,self.market(self.rpc(extensions=[{'extension':'pausableConfig','state':{'paused':True}}])),self.cfg)
  self.assertFalse(s['hard_rug_pass'])
 def test_hook_alone_is_soft_when_positive_route_exists(self):
  with patch('tiers.http_json',side_effect=self.http):s=hard_review(self.c,self.market(self.rpc(extensions=[{'extension':'transferHook'}])),self.cfg)
  self.assertTrue(s['hard_rug_pass']);self.assertFalse(next(x for x in s['soft_checks'] if x['name']=='Token_2022_extensions')['pass'])
 def test_applied_checklist_primary_reject_fallback_penalty(self):
  safety=dict(status='pass',hard_rug_pass=True,hard_rug_checks=[{'name':'all','pass':True}],soft_checks=[],summary='pass',top_human_pct=1,top10_measured_pct=5)
  item={'key':'liq_rule','rules':[{'field':'liquidity_usd','op':'gte','value':30000}]}
  lines=[]
  with patch('tiers.hard_review',return_value=safety):
   r=evaluate([dict(self.c)],self.market(None),self.cfg,lambda *a:lines.append(a),lambda *a:True,self.root,checklist=[item])
  self.assertEqual(r['primary'],0);self.assertEqual(r['fallback'],1)
  c=r['candidates'][0]
  self.assertTrue(c['checklist_violations']);self.assertTrue(any(x['reason']=='checklist:liq_rule' for x in c['fallback_penalties']))
  self.assertTrue(any('CHECKLIST APPLIED' in a[1] for a in lines))
 def test_loss_review_creates_executable_rule_not_advisory(self):
  chat=LiveChat(self.root/'chat.json');chat.data['started']=time.time()-1000
  t=dict(id='loss',mode='forward:paper',realized=True,entry_ts=time.time()-300,exit_ts=time.time()-1,pnl_usd=-2,symbol='TEST',exit_reason='stop')
  chat.record(dict(kind='trade_close',is_live_close=True,historical=False,trade=t,time='now'))
  item=chat.data['checklist'][0]
  self.assertEqual(item['rules'][0]['field'],'green_confirmation')
  self.assertTrue(violations([item],{'green_confirmation':False}))
  self.assertNotIn('SUGGESTION',item['status'])
 def test_target_floor_updates_existing_and_30pct_is_not_exit(self):
  a=PaperAccount(self.root,self.cfg)
  p=dict(id='open',mode='forward:paper',mint='A',pool='P',symbol='TEST',entry_ts=time.time()-60,entry_time='now',entry_price=1,notional_usd=100,cost_rate=.011,stop_fraction=.12,target_fraction=.25,max_hold_seconds=57600)
  a.data['positions']=[p];a.data['cash_usd']=900;a.save();lines=[]
  a.sync_exit_policy(lambda *x:lines.append(x))
  self.assertEqual(p['target_fraction'],.35);self.assertEqual(p['stop_fraction'],.12);self.assertEqual(p['max_hold_seconds'],57600)
  self.assertTrue(any('25% -> 35%' in x[1] for x in lines))
  m=type('M',(),{'dexscreener_pairs':lambda s,m:([{'mint':'A','pool':'P','price_usd':1.30}],[])})()
  a.manage(m,Memory(self.root),lambda *a:None,lambda *a:None)
  self.assertEqual(len(a.data['positions']),1)

class EntryDisplayTests(unittest.TestCase):
 def test_timestamp_formatter_and_all_entry_paths(self):
  import subprocess
  root=Path(__file__).resolve().parents[1]
  for fn in ('index.html','live/index.html'):
   s=(root/fn).read_text()
   self.assertIn("year: 'numeric'",s);self.assertIn("second: '2-digit'",s)
   self.assertIn("opened.textContent='Opened '+et(t.entry_time)",s)
   self.assertIn("'Opened ' + et(t.entry_time)",s)
   self.assertIn('renderOpenPositions(d)',s)
  result=subprocess.check_output(['node','-e',"console.log(new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit',second:'2-digit'}).format(new Date('2026-11-07T05:00:09Z'))+' ET')"],text=True).strip()
  self.assertEqual(result,'Nov 7, 2026, 12:00:09 AM ET')
