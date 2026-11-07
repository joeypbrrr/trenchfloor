#!/usr/bin/env python3
"""Single-connection FREE PumpPortal launch/migration collector.

Trade subscriptions are documented as METERED, not free. This process never
uses an API key/wallet or requests subscribeTokenTrade. Observed fee totals
remain unknown without complete trade coverage. No trading API exists here.
"""
import argparse
import fcntl
import json
import logging
import os
import signal
import sqlite3
import time
from pathlib import Path

import websocket

ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger('pumpportal')
SCHEMA = '''
CREATE TABLE IF NOT EXISTS tokens (
 mint TEXT PRIMARY KEY, created REAL, dev TEXT, name TEXT, symbol TEXT,
 create_json TEXT, create_seen INTEGER DEFAULT 0, tracked INTEGER DEFAULT 0,
 coverage_complete INTEGER DEFAULT 0, coverage_reason TEXT,
 migrated INTEGER DEFAULT 0, updated REAL
);
CREATE TABLE IF NOT EXISTS events (
 event_key TEXT PRIMARY KEY, mint TEXT, kind TEXT, trader TEXT, sol_amount REAL,
 token_amount REAL, slot INTEGER, received REAL, raw_json TEXT,
 fee_rate REAL, fee_sol REAL
);
CREATE INDEX IF NOT EXISTS events_mint ON events(mint,received);
CREATE TABLE IF NOT EXISTS status (key TEXT PRIMARY KEY, value TEXT);
'''


def connect_store(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript(SCHEMA)
    db.commit()
    return db


def status(db, key, value):
    db.execute('INSERT OR REPLACE INTO status VALUES (?,?)', (key,json.dumps(value)))
    db.commit()


def finite(value):
    try:
        import math
        value=float(value)
        return value if math.isfinite(value) else None
    except (ValueError,TypeError):
        return None


class Store:
    def __init__(self, path, settings):
        self.db=connect_store(path)
        self.settings=settings
        # A process restart/disconnect creates an unrecoverable stream gap.
        self.gap('collector started/restarted; trade stream unavailable on free tier')

    def gap(self, reason):
        self.db.execute('UPDATE tokens SET coverage_complete=0,coverage_reason=?',(reason,))
        self.db.commit()
        status(self.db,'coverage_gap',{'time':time.time(),'reason':reason})

    def prune(self, now):
        ttl=self.settings.get('track_seconds',3600)
        cap=int(self.settings.get('max_tracked_mints',64))
        self.db.execute('UPDATE tokens SET tracked=0,coverage_complete=0,coverage_reason=? WHERE tracked=1 AND (created<? OR migrated=1)',
                        ('tracking expired or migrated',now-ttl))
        rows=self.db.execute('SELECT mint FROM tokens WHERE tracked=1 ORDER BY created DESC').fetchall()
        for (mint,) in rows[cap:]:
            self.db.execute('UPDATE tokens SET tracked=0,coverage_complete=0,coverage_reason=? WHERE mint=?',('tracking cap evicted mint',mint))
        self.db.commit()

    def ingest(self, row, received=None):
        now=received or time.time()
        mint=row.get('mint')
        kind=row.get('txType') or ('migration' if row.get('migration') else None)
        import re
        if not mint or not isinstance(mint,str) or not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}',mint):
            status(self.db,'last_control',row)
            return
        trader=row.get('traderPublicKey')
        sol=finite(row.get('solAmount'))
        amount=finite(row.get('tokenAmount',row.get('initialBuy')))
        amount=abs(amount) if amount is not None else None
        slot=row.get('slot')
        slot=slot if isinstance(slot,int) and not isinstance(slot,bool) and slot>=0 else None
        if kind=='create':
            self.db.execute('INSERT OR IGNORE INTO tokens (mint,created,dev,name,symbol,create_json,create_seen,tracked,coverage_complete,coverage_reason,updated) VALUES (?,?,?,?,?,?,1,1,0,?,?)',
                            (mint,now,trader,row.get('name'),row.get('symbol'),json.dumps(row),'trade feed is metered; complete global fee coverage unknown',now))
        elif kind in ('migration','migrate'):
            self.db.execute('UPDATE tokens SET migrated=1,tracked=0,coverage_complete=0,coverage_reason=?,updated=? WHERE mint=?',
                            ('migration ends bonding-curve coverage; PumpSwap not tracked',now,mint))
        if kind in ('buy','sell'):
            self.db.execute('INSERT OR IGNORE INTO tokens (mint,created,create_seen,tracked,coverage_reason,updated) VALUES (?,?,0,0,?,?)',
                            (mint,now,'launch not observed; partial history',now))
            self.db.execute('UPDATE tokens SET updated=? WHERE mint=?',(now,mint))
        if kind not in ('create','buy','sell','migration','migrate'):
            status(self.db,'last_control',row)
            return
        # Never use signature alone: one transaction can contain multiple events.
        signature=row.get('signature')
        if signature:
            identity='|'.join(str(v) for v in (signature,mint,('buy' if kind=='create' else kind),trader,sol,amount,row.get('vSolInBondingCurve'),row.get('vTokensInBondingCurve')))
        else:
            # Unidentifiable events cannot establish complete fee coverage.
            import hashlib
            identity='missing-signature:'+hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
            self.db.execute('UPDATE tokens SET coverage_complete=0,coverage_reason=? WHERE mint=?',('event missing signature; completeness unprovable',mint))
        rate=float(self.settings.get('bonding_curve_fee_rate',0.0125))
        fee=abs(sol)*rate if sol is not None and kind in ('create','buy','sell') and row.get('pool')=='pump' else None
        if fee is None and kind in ('create','buy','sell'):
            self.db.execute('UPDATE tokens SET coverage_complete=0,coverage_reason=? WHERE mint=?',('fee amount/venue unknown; partial coverage',mint))
        if kind in ('buy','sell') and row.get('pool') not in (None,'pump'):
            self.db.execute('UPDATE tokens SET migrated=1,coverage_complete=0,coverage_reason=? WHERE mint=?',('post-curve venue seen; global fee coverage ends',mint))
        self.db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (identity,mint,kind,trader,abs(sol) if sol is not None else None,amount,slot,now,json.dumps(row),rate,fee))
        self.db.commit()
        self.prune(now)
        status(self.db,'last_event',{'time':now,'kind':kind,'mint':mint})


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--test-seconds',type=float,default=0,help='explicit isolated timed collector test, even while default collector is OFF')
    p.add_argument('--db',type=Path)
    a=p.parse_args()
    config=json.loads((ROOT/'config.json').read_text())
    cfg=config.get('pumpportal',{})
    if not a.test_seconds and not cfg.get('collector_enabled',False):
        print('PumpPortal collector OFF by default',flush=True)
        return 0
    if cfg.get('trade_stream_enabled',False):
        raise SystemExit('Refusing paid token-trade subscriptions: free-data-only/no-wallet constraint. subscribeTokenTrade requires a funded wallet per PumpPortal docs.')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s ET %(message)s')
    path=a.db or ROOT/'data'/'pumpportal.sqlite3'
    # A global lock, even for isolated tests, enforces ONE connection on this box.
    lock=open(ROOT/'data'/'pumpportal.collector.lock','a+')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('Another PumpPortal collector holds the single-connection lock; not connecting')
    store=Store(path,cfg)
    deadline=time.monotonic()+a.test_seconds if a.test_seconds else float('inf')
    delay=1
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    connections=0
    while not stopping and time.monotonic()<deadline:
        ws=None
        try:
            ws=websocket.create_connection('wss://pumpportal.fun/api/data',timeout=10)
            connections+=1
            status(store.db,'connection',{'connected':True,'at':time.time(),'connections':connections})
            ws.send(json.dumps({'method':'subscribeNewToken'}))
            ws.send(json.dumps({'method':'subscribeMigration'}))
            LOG.info('Connected: free creates+migrations only; token trades NOT subscribed (metered)')
            healthy_since=time.monotonic()
            while not stopping and time.monotonic()<deadline:
                try: raw=ws.recv()
                except websocket.WebSocketTimeoutException: continue
                if time.monotonic()-healthy_since>=60:delay=1
                if not raw: raise ConnectionError('websocket closed')
                row=json.loads(raw)
                if isinstance(row,dict): store.ingest(row)
        except Exception as exc:
            store.gap('disconnect; no replay available: '+type(exc).__name__)
            status(store.db,'last_error',{'time':time.time(),'type':type(exc).__name__,'message':str(exc)[:300]})
            LOG.warning('Connection unavailable (%s); retry backoff %ss',type(exc).__name__,delay)
            remaining=max(0,deadline-time.monotonic())
            time.sleep(min(delay,remaining))
            delay=min(delay*2,float(cfg.get('reconnect_max_seconds',60)))
        finally:
            if ws:
                ws.close()
            status(store.db,'connection',{'connected':False,'at':time.time(),'connections':connections})
    store.gap('collector stopped; complete trade coverage unavailable')
    LOG.info('Stopped. launches=%s events=%s connections=%s',store.db.execute('SELECT COUNT(*) FROM tokens WHERE create_seen=1').fetchone()[0],store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0],connections)
    store.db.close()
    return 0


if __name__=='__main__':raise SystemExit(main())
