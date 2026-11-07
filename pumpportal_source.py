"""Read-only PumpPortal store adapter and fail-closed launch-risk filters.

Free creates/migrations work; complete token trades are a paid service. Nothing
here promotes observed fee accounting to verified cumulative coverage merely
because a create event was observed. Unknown remains a rejection.
"""
import json
import sqlite3
import time
from collections import Counter
from pathlib import Path

from sources import SOL_MINT, SourceError, http_json, num

FEE_URL='https://pump.fun/docs/fees'
DATA_URL='https://pumpportal.fun/data-api/real-time'


def connect_readonly(path):
    if not Path(path).exists():
        raise SourceError('PumpPortal collector store missing; collector is OFF by default')
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    db.row_factory=sqlite3.Row
    return db


def fee_coverage(token, connection, latest_event, now, settings):
    from datetime import date
    try:
        rate_current=date.fromisoformat(settings['fee_rate_valid_until'])>=date.today()
    except (KeyError,ValueError,TypeError):
        rate_current=False
    complete=bool(rate_current and token['create_seen'] and token['coverage_complete'] and not token['migrated'])
    complete=complete and bool(connection.get('connected')) and latest_event and now-latest_event<=settings.get('max_market_data_age_seconds',120)
    return bool(complete)


def checks_for(cand, settings, now=None, existing_filters=None):
    now=now or time.time()
    obs=cand.get('pump_observation') or {}
    risk=cand.get('pump_risk') or {}
    existing_filters=existing_filters or {}
    checks=[]
    def add(name,value,rule,phase='pre'):
        checks.append({'name':name,'pass':value is True,'known':value is not None,'phase':phase,
                       'reason':('PASS ' if value is True else ('UNKNOWN / FAIL CLOSED ' if value is None else 'FAIL '))+rule})
    fee=num(cand.get('global_fees_sol'))
    mcap=num(cand.get('market_cap_usd'))
    add('market_cap',None if mcap is None else mcap>=settings.get('min_market_cap_usd',6000),f'market cap must be >=${settings.get("min_market_cap_usd",6000):g} using a fresh SOL/USD quote')
    add('global_fees',None if fee is None else fee>=settings.get('min_global_fees_sol',1.5),f'cumulative bonding-curve fees must be >={settings.get("min_global_fees_sol",1.5):g} SOL with complete create-to-now trade coverage; free creates alone are insufficient')
    add('market_data_fresh',None if obs.get('last_event') is None else now-obs['last_event']<=settings.get('max_market_data_age_seconds',120),f'last coin event must be within {settings.get("max_market_data_age_seconds",120):g}s; a live SOL quote does not refresh an old token price')
    add('minimum_age',None if cand.get('created_ts') is None else now-cand['created_ts']>=settings.get('min_age_seconds',900),f'minimum observed age {settings.get("min_age_seconds",900)/60:g} minutes; no immediate new-launch chase')
    add('observed_trades',obs.get('trade_count',0)>=settings.get('min_observed_trades',50),f'at least {settings.get("min_observed_trades",50)} observed buy/sell trades, excluding the create event')
    add('unique_traders',obs.get('unique_traders',0)>=settings.get('min_unique_traders',20),f'at least {settings.get("min_unique_traders",20)} unique observed traders')
    ratio=obs.get('buy_sell_ratio')
    add('buy_sell_balance',None if ratio is None else settings.get('min_buy_sell_ratio',.25)<=ratio<=settings.get('max_buy_sell_ratio',4),f'buy/sell count ratio must be between {settings.get("min_buy_sell_ratio",.25):g} and {settings.get("max_buy_sell_ratio",4):g}')
    dominance=obs.get('wallet_volume_fraction')
    add('wallet_volume_dominance',None if dominance is None else dominance<=settings.get('max_wallet_volume_fraction',.10),f'no single trader may represent >{100*settings.get("max_wallet_volume_fraction",.1):g}% of observed SOL volume')
    add('recent_real_volume',obs.get('recent_volume_sol',0)>=settings.get('min_recent_volume_sol',20),f'at least {settings.get("min_recent_volume_sol",20):g} SOL traded in the last {settings.get("recent_volume_window_seconds",300)/60:g} minutes; observed not proof against wash trading')
    accel=obs.get('volume_acceleration')
    add('trending_volume',None if accel is None else accel>=settings.get('min_volume_acceleration',1.2),f'recent-window volume must be >={settings.get("min_volume_acceleration",1.2):g}x preceding-window volume')
    slots=risk.get('launch_slot_buys',obs.get('launch_slot_buys'))
    add('launch_slot_burst',None if slots is None else slots<=settings.get('max_launch_slot_buys',4),f'no more than {settings.get("max_launch_slot_buys",4)} buys in the first {settings.get("launch_slot_window",2)} slots; missing slot data fails closed','post')
    launch_frac=risk.get('launch_supply_fraction')
    add('launch_supply',None if launch_frac is None else launch_frac<=settings.get('max_launch_supply_fraction',.10),f'first launch-slot-window buys must total <={100*settings.get("max_launch_supply_fraction",.1):g}% of RPC-measured supply','post')
    linked=risk.get('fresh_or_linked_launch_fraction')
    add('fresh_or_linked_launch',None if linked is None else linked<=settings.get('max_fresh_or_linked_launch_supply_fraction',.05),f'fresh/linked early wallets must total <={100*settings.get("max_fresh_or_linked_launch_supply_fraction",.05):g}% of supply; missing wallet provenance fails closed','post')
    add('mint_authority',risk.get('mint_authority_revoked'),'mint authority must be explicitly null in parsed RPC data','post')
    add('freeze_authority',risk.get('freeze_authority_revoked'),'freeze authority must be explicitly null in parsed RPC data','post')
    dev=risk.get('dev_hold_pct')
    add('dev_holdings',None if dev is None else dev<=settings.get('max_dev_hold_pct',2),f'developer must hold <={settings.get("max_dev_hold_pct",2):g}% of supply across token accounts','post')
    dumped=risk.get('dev_dumped')
    add('dev_dump',None if dumped is None else not dumped,f'developer selling >={100*settings.get("max_dev_sold_fraction",.5):g}% of initial allocation rejects; sold-out rejection={settings.get("reject_dev_soldout",True)}','post')
    top=risk.get('top_holder_pct')
    add('top_holder',None if top is None else top<=settings.get('max_holder_pct',3.5),f'conservative largest non-curve wallet upper bound must be <={settings.get("max_holder_pct",3.5):g}%','post')
    top10=risk.get('top10_pct')
    add('top10_concentration',None if top10 is None else top10<=settings.get('max_top10_pct',30),f'conservative top-10 non-curve concentration upper bound must be <={settings.get("max_top10_pct",30):g}%','post')
    add('curve_exclusion',risk.get('curve_verified'),'exclude a curve account only after RPC verifies its owning pump program','post')
    liq=num(cand.get('liquidity_usd'))
    vol=num(cand.get('volume_24h_usd'))
    add('existing_liquidity',None if liq is None else liq>=existing_filters.get('min_liquidity_usd',12000),f'real reported liquidity must be >=${existing_filters.get("min_liquidity_usd",12000):g}; virtual curve reserves are not liquidity')
    add('existing_daily_volume',None if vol is None else vol>=existing_filters.get('min_volume_24h_usd',8000),f'reported/observed 24h volume must be >=${existing_filters.get("min_volume_24h_usd",8000):g}')
    add('market_cap_ceiling',None if mcap is None else mcap<=existing_filters.get('max_market_cap_usd',20000000),f'market cap must be <=${existing_filters.get("max_market_cap_usd",20000000):g}')
    return checks


def candidates(market, config):
    settings=config.get('pumpportal') or {}
    root=market.cache_path.parents[2]
    db_path=Path(settings.get('db_path','data/pumpportal.sqlite3'))
    if not db_path.is_absolute():db_path=root/db_path
    db=connect_readonly(db_path)
    db.execute('BEGIN')  # one coherent read-only WAL snapshot
    now=time.time()
    tokens=[dict(row) for row in db.execute('SELECT * FROM tokens WHERE create_seen=1 ORDER BY created DESC')]
    controls={row['key']:json.loads(row['value']) for row in db.execute('SELECT * FROM status')}
    sol_usd=None
    errors=[]
    try:
        payload,_=http_json('https://api.geckoterminal.com/api/v2/simple/networks/solana/token_price/'+SOL_MINT,
                            limiter=market.gecko,attempts=1,timeout=15)
        sol_usd=num((payload.get('data',{}).get('attributes',{}).get('token_prices') or {}).get(SOL_MINT))
    except SourceError as exc:errors.append('SOL/USD quote unavailable: '+str(exc))
    now=time.time()
    result=[]
    verified=0
    window=float(settings.get('recent_volume_window_seconds',300))
    for token in tokens:
        rows=[dict(r) for r in db.execute('SELECT * FROM events WHERE mint=? ORDER BY received',(token['mint'],))]
        create=json.loads(token['create_json'])
        trade_rows=[r for r in rows if r['kind'] in ('buy','sell')]
        counted=[r for r in rows if r['kind'] in ('create','buy','sell')]
        latest=counted[-1] if counted else None
        latest_raw=json.loads(latest['raw_json']) if latest else create
        totals=Counter()
        for row in trade_rows:
            if row['trader'] and row['sol_amount'] is not None:totals[row['trader']]+=row['sol_amount']
        volume=sum(totals.values())
        buys=sum(r['kind']=='buy' for r in trade_rows)
        sells=sum(r['kind']=='sell' for r in trade_rows)
        recent=sum(r['sol_amount'] or 0 for r in trade_rows if r['received']>=now-window)
        previous=sum(r['sol_amount'] or 0 for r in trade_rows if now-2*window<=r['received']<now-window)
        all_slot_data=bool(counted) and all(r['slot'] is not None for r in counted)
        first_slot=min(r['slot'] for r in counted) if all_slot_data else None
        launch_buys=[r for r in counted if r['kind'] in ('create','buy') and r['slot'] is not None and first_slot is not None and r['slot']<first_slot+settings.get('launch_slot_window',2) and (r['token_amount'] or 0)>0]
        complete=fee_coverage(token,controls.get('connection',{}),latest['received'] if latest else None,now,settings) and all(r['fee_sol'] is not None for r in counted)
        fee_total=sum(r['fee_sol'] or 0 for r in counted)
        if complete:verified+=1
        mc_sol=num(latest_raw.get('marketCapSol'))
        vsol=num(latest_raw.get('vSolInBondingCurve'))
        vtokens=num(latest_raw.get('vTokensInBondingCurve'))
        result.append({
            'mint':token['mint'],'symbol':token['symbol'],'name':token['name'],
            'created_ts':token['created'],'quote_mint':SOL_MINT,'quote_symbol':'SOL',
            'market_cap_usd':mc_sol*sol_usd if mc_sol is not None and sol_usd else None,
            'market_cap_from':'PumpPortal marketCapSol × fresh SOL/USD (token event age is checked separately)',
            'price_usd':vsol/vtokens*sol_usd if vsol and vtokens and sol_usd else None,
            'volume_24h_usd':sum(r['sol_amount'] or 0 for r in trade_rows if r['received']>=now-86400)*sol_usd if sol_usd else None,
            'liquidity_usd':None, # virtual reserves are NOT real withdrawable liquidity
            'metrics_source':'pumpportal:observed launches/trades','discovered_from':['pumpportal:new_token'],
            'global_fees_sol':fee_total if complete else None,
            'global_fees_observed_sol':fee_total,'global_fees_verified':complete,
            'global_fees_basis':'observed SOL amount × official bonding-curve total fee; protocol+creator, not network/app fees. '+(token['coverage_reason'] or ''),
            'dev_wallet':token['dev'],'bonding_curve':create.get('bondingCurveKey'),
            'pump_observation':{'trade_count':len(trade_rows),'unique_traders':len(totals),'buy_sell_ratio':buys/sells if sells else None,
                                'wallet_volume_fraction':max(totals.values())/volume if volume else None,
                                'recent_volume_sol':recent,'volume_acceleration':recent/previous if previous else None,
                                'last_event':latest['received'] if latest else None,'launch_slot_buys':len(launch_buys) if all_slot_data else None,
                                'create_seen':bool(token['create_seen']),'complete_coverage':complete,'migrated':bool(token['migrated']),
                                'dev_initial_tokens':num(create.get('initialBuy')),'dev_sold_tokens':sum(r['token_amount'] or 0 for r in trade_rows if r['kind']=='sell' and r['trader']==token['dev']),
                                'launch_signature_events':[{'signature':json.loads(r['raw_json']).get('signature'),**{k:r[k] for k in ('trader','token_amount','received','slot','kind')}} for r in counted[:int(settings.get('max_launch_slot_lookups',8))]],
                                'launch_buys':[{k:r[k] for k in ('trader','token_amount','received','slot')} for r in launch_buys] if all_slot_data else None},
            'pump_risk':{},
        })
    migration_count=db.execute("SELECT COUNT(*) FROM events WHERE kind IN ('migration','migrate')").fetchone()[0]
    tracked_count=db.execute('SELECT COUNT(*) FROM tokens WHERE tracked=1').fetchone()[0]
    db.close()
    result.sort(key=lambda r:r['pump_observation']['recent_volume_sol'],reverse=True)
    limit=int(config.get('limits',{}).get('enrich_mints',30))
    selected=result[:limit]
    # Enrichment only. Launch candidate discovery never comes from paid boosts.
    if selected:
        pairs,err=market.dexscreener_pairs([r['mint'] for r in selected])
        errors.extend(err)
        for cand in selected:
            pair=max((p for p in pairs if p['mint']==cand['mint'] and p.get('quote_mint')==SOL_MINT),key=lambda p:p.get('liquidity_usd') or 0,default={})
            for k in ('pool','dex','liquidity_usd','liquidity_base'):
                if pair.get(k) is not None:cand[k]=pair[k]
    failures=Counter()
    for cand in selected:
        cand['pump_checks']=checks_for(cand,settings,now,config.get('filters'))
        for c in cand['pump_checks']:
            if not c['pass']:failures[c['name']]+=1
    report={'source':'pumpportal','label':'PumpPortal FREE launches/migrations; full token trades are METERED and not subscribed',
            'discovered':len(result),'launches_seen':len(tokens),'enriched':len(selected),'skipped_rejected':0,
            'fee_verified_count':verified,'observed_buy_sell_events':sum(r['pump_observation']['trade_count'] for r in result),
            'failure_counts_all_checks':dict(failures),'errors':errors,'sol_usd':sol_usd,
            'migrations_seen':migration_count,'locally_tracked_mints':tracked_count,'token_trade_subscriptions':0,
            'connection':controls.get('connection'),'last_error':controls.get('last_error'),
            'fee_rate':settings.get('bonding_curve_fee_rate',.0125),'fee_rate_source':FEE_URL,
            'trade_feed_limitation':DATA_URL}
    market.source_status['candidate_source']={'ok':bool(result),**report}
    return selected,report


def launch_risk(rpc,cand,settings):
    """RPC dev/curve/provenance checks. Bounded by the existing RPC budget.

    All missing data remains unknown. No inference of fresh-wallet age from a
    short history: an old confirmed signature proves age; lack of one doesn't.
    """
    out={}
    mint=cand['mint'];dev=cand.get('dev_wallet');curve=cand.get('bonding_curve')
    try:
        mint_data=rpc.call('getAccountInfo',[mint,{'encoding':'jsonParsed'}])
        info=(((mint_data or {}).get('value',{}).get('data') or {}).get('parsed') or {}).get('info') or {}
        out['mint_authority_revoked']=info['mintAuthority'] is None if 'mintAuthority' in info else None
        out['freeze_authority_revoked']=info['freezeAuthority'] is None if 'freezeAuthority' in info else None
        supply=rpc.call('getTokenSupply',[mint]).get('value') or {}
        raw=num(supply.get('amount')); decimals=int(supply.get('decimals',0))
        supply_ui=raw/(10**decimals) if raw and raw>0 else None
        out['supply_ui']=supply_ui
        if curve:
            try:
                from solders.pubkey import Pubkey
                derived,_=Pubkey.find_program_address([b'bonding-curve',bytes(Pubkey.from_string(mint))],Pubkey.from_string(settings['pump_program_id']))
                canonical=str(derived)==curve
            except (ImportError,ValueError,KeyError):
                canonical=False
            value=(rpc.call('getAccountInfo',[curve,{'encoding':'base64'}]) or {}).get('value') or {}
            out['curve_verified']=canonical and value.get('owner')==settings.get('pump_program_id') and value.get('executable') is False
        if dev and supply_ui:
            doc=rpc.call('getTokenAccountsByOwner',[dev,{'mint':mint},{'encoding':'jsonParsed'}])
            accounts=doc.get('value')
            if isinstance(accounts,list):
                balances=[]
                for account in accounts:
                    parsed=account.get('account',{}).get('data',{}).get('parsed',{}).get('info',{})
                    amount=num(parsed.get('tokenAmount',{}).get('amount'))
                    if amount is None:break
                    balances.append(amount/(10**decimals))
                if len(balances)==len(accounts):out['dev_hold_pct']=sum(balances)/supply_ui*100
        obs=cand.get('pump_observation') or {}
        initial=obs.get('dev_initial_tokens');sold=obs.get('dev_sold_tokens')
        if obs.get('complete_coverage') and initial is not None and sold is not None and 'dev_hold_pct' in out:
            soldout=initial>0 and out['dev_hold_pct']==0
            dumped=initial>0 and sold/initial>=settings.get('max_dev_sold_fraction',.5)
            out['dev_dumped']=dumped or (soldout and settings.get('reject_dev_soldout',True))
        launch=obs.get('launch_buys')
        if launch is None and obs.get('complete_coverage'):
            slot_rows=[]
            for row in obs.get('launch_signature_events') or []:
                if not row.get('signature'):break
                tx=rpc.call('getTransaction',[row['signature'],{'encoding':'jsonParsed','maxSupportedTransactionVersion':0}])
                if not isinstance(tx,dict) or tx.get('slot') is None:break
                slot_rows.append({**row,'slot':tx['slot']})
            if slot_rows and len(slot_rows)==len(obs.get('launch_signature_events') or []):
                first=min(r['slot'] for r in slot_rows)
                end=first+settings.get('launch_slot_window',2)
                if any(r['slot']>=end for r in slot_rows):
                    launch=[r for r in slot_rows if r['kind'] in ('create','buy') and r['slot']<end and (r['token_amount'] or 0)>0]
                    out['launch_slot_buys']=len(launch)
        if launch is not None and supply_ui and all(r['token_amount'] is not None for r in launch):
            out['launch_supply_fraction']=sum(r['token_amount'] for r in launch)/supply_ui
            # Provenance sampling is fail-closed when there are too many wallets.
            wallets=list(dict.fromkeys(r['trader'] for r in launch if r['trader']))
            if len(wallets)<=settings.get('max_provenance_wallets',4):
                from safety import extract_funders
                wallet_info={};all_known=True
                for wallet in wallets:
                    sigs=rpc.call('getSignaturesForAddress',[wallet,{'limit':20}])
                    if not isinstance(sigs,list) or not sigs:
                        all_known=False;break
                    times=[s.get('blockTime') for s in sigs if s.get('blockTime') is not None]
                    old_enough=any(t<cand['created_ts']-settings.get('wallet_min_history_seconds',86400) for t in times)
                    if not old_enough:all_known=False;break # fresh OR unknown; cannot establish safe age
                    sig=sigs[-1].get('signature')
                    tx=rpc.call('getTransaction',[sig,{'encoding':'jsonParsed','maxSupportedTransactionVersion':0}]) if sig else None
                    if not tx:all_known=False;break
                    wallet_info[wallet]=extract_funders(tx,wallet)
                if all_known and len(wallet_info)==len(wallets) and all(wallet_info.values()):
                    common=set()
                    for i,a in enumerate(wallets):
                        for b in wallets[i+1:]:
                            if wallet_info[a]&wallet_info[b]:common.update((a,b))
                    out['fresh_or_linked_launch_fraction']=sum(r['token_amount'] for r in launch if r['trader'] in common)/supply_ui
                    out['provenance_basis']='bounded oldest-of-20 signature and funding sample; not exhaustive wallet linkage'
    except (SourceError,KeyError,AttributeError,TypeError,ValueError) as exc:
        out['error']='launch risk incomplete: '+str(exc)[:200]
    return out
