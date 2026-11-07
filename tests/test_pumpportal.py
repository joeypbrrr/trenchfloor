import importlib.util
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from candidate_sources import fee_filter_reason
from pumpportal_collector import Store
from pumpportal_source import checks_for, fee_coverage, launch_risk
from safety import assess_mint, TOKEN_LEGACY


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'events.sqlite3'
        self.settings={'bonding_curve_fee_rate':.0125,'max_tracked_mints':2,'track_seconds':100}
        self.store=Store(self.path,self.settings)

    def tearDown(self):
        self.store.db.close();self.tmp.cleanup()

    def event(self,kind='create',mint='M'*32,signature='signature',sol=10,**kw):
        return dict(mint=mint,txType=kind,traderPublicKey='DEV',signature=signature,solAmount=sol,initialBuy=100,tokenAmount=100,pool='pump',**kw)

    def test_real_rate_is_1_25_percent_observed_not_verified(self):
        self.store.ingest(self.event(),1000)
        self.store.ingest(self.event('buy',signature='b',sol=20),1001)
        self.store.ingest(self.event('sell',signature='c',sol=5),1002)
        total=self.store.db.execute('select sum(fee_sol) from events').fetchone()[0]
        self.assertAlmostEqual(total,35*.0125)
        token=dict(zip([c[0] for c in self.store.db.execute('select * from tokens').description],self.store.db.execute('select * from tokens').fetchone()))
        self.assertEqual(token['coverage_complete'],0)
        self.assertFalse(fee_coverage(token,{'connected':True},1002,1003,{'fee_rate_valid_until':'2099-01-01'}))

    def test_duplicate_create_initial_buy_not_double_counted(self):
        row=self.event()
        self.store.ingest(row,1000)
        self.store.ingest(row,1001)
        row['txType']='buy'
        self.store.ingest(row,1002)
        self.assertEqual(self.store.db.execute('select count(*) from events').fetchone()[0],1)

    def test_migration_disconnect_restart_always_lose_coverage(self):
        self.store.ingest(self.event(),1000)
        self.store.db.execute('update tokens set coverage_complete=1');self.store.db.commit()
        self.store.ingest(self.event('migrate',signature='migration'),1001)
        self.assertEqual(self.store.db.execute('select migrated,coverage_complete from tokens').fetchone(),(1,0))
        self.store.db.execute('update tokens set coverage_complete=1');self.store.db.commit()
        self.store.gap('lost connection')
        self.assertEqual(self.store.db.execute('select coverage_complete from tokens').fetchone()[0],0)
        self.store.db.execute('update tokens set coverage_complete=1');self.store.db.commit()
        other=Store(self.path,self.settings)
        self.assertEqual(other.db.execute('select coverage_complete from tokens').fetchone()[0],0)
        other.db.close()

    def test_tracking_cap_and_expiry(self):
        for i in range(3):self.store.ingest(self.event(mint=('M'*31)+str(i+1),signature=str(i)),1000+i)
        self.assertEqual(self.store.db.execute('select count(*) from tokens where tracked=1').fetchone()[0],2)
        self.store.prune(1200)
        self.assertEqual(self.store.db.execute('select count(*) from tokens where tracked=1').fetchone()[0],0)

    def test_no_launch_or_wrong_venue_cannot_establish_coverage(self):
        self.store.ingest(self.event('buy'),1000)
        self.assertEqual(self.store.db.execute('select create_seen,coverage_complete from tokens').fetchone(),(0,0))
        row=self.event('buy',signature='swap');row['pool']='pump-amm'
        self.store.ingest(row,1001)
        self.assertEqual(self.store.db.execute('select migrated,coverage_complete from tokens').fetchone(),(1,0))
        self.assertIsNone(self.store.db.execute("select fee_sol from events where kind='buy' order by received desc").fetchone()[0])

    def test_paid_stream_switch_refuses_before_network(self):
        import pumpportal_collector as pc
        cfg=Path(self.tmp.name)/'config.json'
        cfg.write_text(json.dumps({'pumpportal':{'collector_enabled':True,'trade_stream_enabled':True}}))
        with patch.object(pc,'ROOT',Path(self.tmp.name)),patch('sys.argv',['collector']),patch.object(pc.websocket,'create_connection') as connect:
            with self.assertRaisesRegex(SystemExit,'Refusing paid'):pc.main()
            connect.assert_not_called()

    def test_off_by_default_never_connects(self):
        import pumpportal_collector as pc
        (Path(self.tmp.name)/'config.json').write_text('{}')
        with patch.object(pc,'ROOT',Path(self.tmp.name)),patch('sys.argv',['collector']),patch.object(pc.websocket,'create_connection') as connect:
            self.assertEqual(pc.main(),0);connect.assert_not_called()


class RiskTests(unittest.TestCase):
    def test_missing_fee_never_uses_volume_proxy(self):
        self.assertIn('no proxy',fee_filter_reason({'fees_proxy_sol':100},{'candidate_source':'pumpportal','fee_proxy_enabled':True}))

    def test_unknown_launch_slot_and_wallet_provenance_reject(self):
        checks=checks_for({'pump_observation':{},'pump_risk':{}},{})
        by_name={c['name']:c for c in checks}
        for name in ('global_fees','launch_slot_burst','fresh_or_linked_launch','dev_holdings','mint_authority','freeze_authority'):
            self.assertFalse(by_name[name]['pass']);self.assertFalse(by_name[name]['known'])

    def test_all_thresholds_applied(self):
        now=time.time()
        c={'market_cap_usd':6000,'global_fees_sol':1.5,'created_ts':now-1000,'liquidity_usd':20000,'volume_24h_usd':10000,
           'pump_observation':{'last_event':now,'trade_count':50,'unique_traders':20,'buy_sell_ratio':1,'wallet_volume_fraction':.1,'recent_volume_sol':20,'volume_acceleration':1.2,'launch_slot_buys':4},
           'pump_risk':{'launch_supply_fraction':.1,'fresh_or_linked_launch_fraction':.05,'mint_authority_revoked':True,'freeze_authority_revoked':True,'dev_hold_pct':2,'dev_dumped':False,'top_holder_pct':3.5,'top10_pct':30,'curve_verified':True}}
        self.assertTrue(all(t['pass'] for t in checks_for(c,{},now)))
        c['pump_risk']['dev_dumped']=True
        self.assertFalse(next(t for t in checks_for(c,{},now) if t['name']=='dev_dump')['pass'])
        c['pump_observation']['wallet_volume_fraction']=.1001
        self.assertFalse(next(t for t in checks_for(c,{},now) if t['name']=='wallet_volume_dominance')['pass'])

    def test_expired_fee_schedule_is_not_verified(self):
        token={'create_seen':1,'coverage_complete':1,'migrated':0}
        self.assertFalse(fee_coverage(token,{'connected':True},100,101,{'fee_rate_valid_until':'2000-01-01'}))
        self.assertFalse(fee_coverage(token,{'connected':False},100,101,{'fee_rate_valid_until':'2099-01-01'}))

    def mint(self):
        return {'owner':TOKEN_LEGACY,'data':{'parsed':{'type':'mint','info':{'mintAuthority':None,'freezeAuthority':None}}}}

    def test_only_verified_curve_excluded_and_wallet_accounts_aggregated(self):
        largest=[{'address':'curve-token','owner':'curve','amount':'9500'}, {'address':'a','owner':'wallet','amount':'210'}, {'address':'b','owner':'wallet','amount':'290'}]
        meta={'curve':{'executable':False},'wallet':{'executable':False}}
        result=assess_mint(self.mint(),largest,meta,'10000',0,None,3.5,excluded_owners={'curve'},aggregate_holders=True)
        self.assertEqual(result['top_human_pct'],5)
        self.assertEqual(result['status'],'fail')
        self.assertEqual(result['excluded'][0]['excluded_as'],'rpc_verified_bonding_curve')
        result=assess_mint(self.mint(),largest,meta,'10000',0,None,3.5,aggregate_holders=True)
        self.assertGreater(result['top_human_pct'],90)

    def test_unaccounted_supply_does_not_manufacture_holder_pass(self):
        largest=[{'address':'c','owner':'curve','amount':'9500'}, {'address':'w','owner':'wallet','amount':'100'}]
        result=assess_mint(self.mint(),largest,{'curve':{},'wallet':{}},'10000',0,None,3.5,excluded_owners={'curve'},aggregate_holders=True)
        self.assertEqual(result['status'],'incomplete')

    @unittest.skipUnless(importlib.util.find_spec('solders'),'optional public-key validator not in this interpreter')
    def test_canonical_curve_derivation_matches_actual_launch(self):
        from solders.pubkey import Pubkey
        program='6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
        mint='BhLrV9YzZcQy6T2V1p1eXSJDYZSV5aWcxRHuLNCrorxv'
        expected='9d3yrRzkqb4Pbwnh9RYKTjsgKRtj7Wpo57dhap34VceH'
        actual,_=Pubkey.find_program_address([b'bonding-curve',bytes(Pubkey.from_string(mint))],Pubkey.from_string(program))
        self.assertEqual(str(actual),expected)

if __name__=='__main__':unittest.main()
