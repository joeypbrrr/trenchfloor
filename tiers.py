"""Primary/fallback selection with identical fail-closed hard rug checks.
All remote operations are PUBLIC READS: RPC, risk report and unsigned price quote.
No swap transaction is requested, signed, simulated with a wallet, or submitted.
"""
import math
import time
from urllib.parse import urlencode
from sources import num, http_json, SourceError, SKIP_MINTS, SKIP_SYMBOLS
from safety import review_token, TOKEN_LEGACY, TOKEN_2022, KNOWN_AMM
from entry_gates import assess_entry_gates, gather_entry_evidence
from traded_mints import TradedMints

SOL='So11111111111111111111111111111111111111112'

def market_reason(c, f, now=None):
    now=now or time.time()
    if c.get('mint') in SKIP_MINTS or str(c.get('symbol','')).upper() in SKIP_SYMBOLS:return 'quote asset'
    if c.get('quote_mint') not in SKIP_MINTS:return 'unknown/nonstandard quote'
    if not c.get('created_ts'):return 'pair age unknown'
    age=(now-c['created_ts'])/3600
    if age<f['min_pair_age_hours'] or age>f['max_pair_age_days']*24:return 'pair age'
    for key, floor in [('liquidity_usd',f['min_liquidity_usd']),('volume_24h_usd',f['min_volume_24h_usd']),('market_cap_usd',f['min_market_cap_usd'])]:
        v=num(c.get(key))
        if v is None or v<floor:return key+' unknown/below floor'
    if num(c.get('market_cap_usd'))>f['max_market_cap_usd']:return 'market cap above ceiling'
    if not c.get('pool') or not num(c.get('price_usd')) or c['price_usd']<=0:return 'price/pool unknown'
    return None

def score(c):
    # Stable transparent rank; volume and liquidity dominate, concentration is penalized.
    return round(math.log10(1+max(0,c.get('liquidity_usd') or 0))*2
                 +math.log10(1+max(0,c.get('volume_24h_usd') or 0))
                 -(c.get('safety',{}).get('top_human_pct') or 0)/20,6)

def hard_review(c, market, config):
    """Hard entry gates. Unknown data blocks. Extensions stay a primary soft risk."""
    meta={'hard_rug_pass':False,'hard_rug_checks':[],'soft_checks':[]}
    def hard(name,passed,detail):meta['hard_rug_checks'].append({'name':name,'pass':passed,'detail':detail})
    info={};extensions=[];decimals=None;mint_value=None
    try:
        mint_value=market.rpc.call('getAccountInfo',[c['mint'],{'encoding':'jsonParsed'}]).get('value')
        parsed=((mint_value or {}).get('data') or {}).get('parsed') or {}
        if parsed.get('type')!='mint':raise SourceError('parsed mint unavailable')
        info=parsed.get('info') or {};extensions=info.get('extensions') or []
        decimals=info.get('decimals')
    except (SourceError,TypeError,ValueError,AttributeError) as exc:meta['mint_read_error']=str(exc)
    for field,name in [('mintAuthority','mint_authority_revoked'),('freezeAuthority','freeze_authority_revoked')]:
        value=info.get(field,'UNKNOWN')
        passed=(True if value is None else False if isinstance(value,str) and value!='UNKNOWN' else None)
        hard(name,passed,'explicitly revoked' if passed is True else 'active authority' if passed is False else 'authority UNKNOWN')
    # A known paused/nontransferable token cannot pass via an optimistic quote.
    paused=False;pause_unknown=False
    for ext in extensions if isinstance(extensions,list) else []:
        if not isinstance(ext,dict):continue
        name=str(ext.get('extension','')).replace('_','').lower()
        state=ext.get('state') or {}
        if name in ('pausable','pausableconfig'):
            flag=state.get('paused',ext.get('paused'))
            if flag is True:paused=True
            elif flag is not False:pause_unknown=True
        if name=='nontransferable':paused=True
    q=None;route=None
    try:
        if paused:route=False
        elif pause_unknown:route=None
        elif not isinstance(decimals,int) or not 0<=decimals<=18:route=None
        else:
            raw=max(1,int(config['paper']['notional_usd']/c['price_usd']*10**decimals))
            params=urlencode(dict(inputMint=c['mint'],outputMint=SOL,amount=raw,slippageBps=100))
            q,_=http_json('https://lite-api.jup.ag/swap/v1/quote?'+params,timeout=12,attempts=2)
            route=(isinstance(q,dict) and q.get('inputMint')==c['mint'] and q.get('outputMint')==SOL
                   and str(q.get('inAmount'))==str(raw) and (num(q.get('outAmount')) or 0)>0 and any(isinstance(r,dict) and isinstance(r.get('swapInfo'),dict) and r['swapInfo'].get('ammKey') for r in q.get('routePlan',[])))
    except (SourceError,ValueError,TypeError,OverflowError,ZeroDivisionError) as exc:meta['sell_read_error']=str(exc)
    hard('sellable_not_honeypot',route,'read-only positive sell route required; known paused/nontransferable rejects; unknown route/paused state rejects; no execution')
    meta['sell_quote']={k:q.get(k) for k in ('inAmount','outAmount','inputMint','outputMint','contextSlot')} if isinstance(q,dict) else None
    # Rugcheck is only used to confirm the pool vault address. LP lock/burn and
    # the other entry gates are decided later and never relabel mint, freeze, or sell-route.
    report={};pool={};exact=False;burned=None
    try:
        report,_=http_json('https://api.rugcheck.xyz/v1/tokens/'+c['mint']+'/report',timeout=12,attempts=2)
        if not isinstance(report,dict) or report.get('mint')!=c['mint']:raise SourceError('risk report mint mismatch/malformed')
        pool=next((m for m in report.get('markets',[]) if m.get('pubkey')==c['pool']),{})
        vault=pool.get('liquidityA') if pool.get('mintA')==c['mint'] else pool.get('liquidityB') if pool.get('mintB')==c['mint'] else None
        if vault:
            values=market.rpc.call('getMultipleAccounts',[[c['pool'],vault],{'encoding':'jsonParsed'}]).get('value')
            if isinstance(values,list) and len(values)==2:
                pi,vi=values;vinfo=((((vi or {}).get('data') or {}).get('parsed') or {}).get('info') or {})
                exact=isinstance(pi,dict) and pi.get('owner') in KNOWN_AMM and vinfo.get('mint')==c['mint'] and vinfo.get('owner')==c['pool']
        lp=pool.get('lp') or {};lp_mint=pool.get('mintLP') or lp.get('lpMint')
        if lp_mint and (num(lp.get('lpLockedPct')) or 0)>=99.99 and (num(lp.get('lpTotalSupply')) or 0)>0:
            supply=market.rpc.call('getTokenSupply',[lp_mint]).get('value') or {}
            if 'amount' in supply:burned=int(supply['amount'])==0
    except (SourceError,ValueError,TypeError,AttributeError) as exc:meta['lp_read_error']=str(exc)
    try:
        chain=review_token(market.rpc,c['mint'],None,20,require_complete=True,excluded_owners={c['pool']} if c.get('pool') else set(),aggregate_holders=True,conservative_tail=False)
    except (SourceError,ValueError,TypeError,AttributeError) as exc:chain={'status':'incomplete','summary':str(exc)}
    meta.update({k:v for k,v in chain.items() if k not in ('status','summary','hard_fails','hard_rug_checks')})
    meta['mint_authority_active']=info.get('mintAuthority') is not None if 'mintAuthority' in info else None
    meta['freeze_authority_active']=info.get('freezeAuthority') is not None if 'freezeAuthority' in info else None
    safe={'metadataPointer','tokenMetadata','mintCloseAuthority','groupPointer','groupMemberPointer','tokenGroup','tokenGroupMember'}
    program=(mint_value or {}).get('owner')
    ext_names=[e.get('extension') for e in extensions if isinstance(e,dict)] if isinstance(extensions,list) else []
    extension_safe=(program==TOKEN_LEGACY or (program==TOKEN_2022 and set(ext_names).issubset(safe)))
    meta['soft_checks']=[
        {'name':'holder_observations_complete','pass':chain.get('status')!='incomplete' and num(chain.get('top_human_pct')) is not None and exact,'detail':'top-20 accounts aggregated; only the pool address and exact verified vault are excluded'},
        {'name':'single_non_pool_holder_20pct','pass':None if num(chain.get('top_human_pct')) is None else chain['top_human_pct']<=20,'detail':str(chain.get('top_human_pct'))+'%'},
        {'name':'Token_2022_extensions','pass':extension_safe,'detail':'risky/unknown extensions primary-reject, fallback-penalty unless actually unsellable'}]
    try:
        evidence=gather_entry_evidence(c,market,chain,config,http_get=http_json)
    except (SourceError,TypeError,ValueError,AttributeError,OSError) as exc:
        evidence={'holder_read_ok':False,'holder_read_error':str(exc),'trade_read_ok':False,'trade_read_error':str(exc),'lp_detail':str(exc),'fee_detail':str(exc),'created_ts':c.get('created_ts')}
    for check in assess_entry_gates(evidence,config):
        hard(check['name'],check['pass'],check['detail'])
    meta['lp_burned']=evidence.get('lp_burned_or_locked') if evidence.get('lp_visible') else burned
    meta['lp_locked']=None
    meta['entry_gate_evidence']={k:evidence.get(k) for k in ('top10_ex_pool_burn_pct','holder_read_ok','trade_read_ok','lp_visible','lp_burned_or_locked','global_fees_verified','global_fees_sol','fee_lower_bound_sol','fee_detail','lp_detail')}
    meta['hard_reasons']=[x['name']+': '+x['detail'] for x in meta['hard_rug_checks'] if x['pass'] is not True]
    meta['hard_rug_pass']=not meta['hard_reasons']
    meta['status']='pass' if meta['hard_rug_pass'] else ('incomplete' if any(x['pass'] is None for x in meta['hard_rug_checks']) else 'fail')
    meta['summary']='PASS hard entry gates; soft flags '+str([x['name'] for x in meta['soft_checks'] if x['pass'] is not True]) if meta['hard_rug_pass'] else '; '.join(meta['hard_reasons'])
    return meta

def tier_reason(c, settings):
    s=c.get('safety') or {}
    if s.get('hard_rug_pass') is not True:return 'hard rug block failed/unknown'
    if settings.get('penalty_only'):return None
    if any(x.get('pass') is not True for x in s.get('soft_checks',[])):return 'primary soft risk reject'
    if num(s.get('top_human_pct')) is None or s['top_human_pct']>settings['max_holder_pct']:return 'tier single-holder limit'
    if num(s.get('top10_measured_pct')) is None or s['top10_measured_pct']>settings['max_top10_pct']:return 'tier top-10 concentration'
    if c.get('checklist_violations'):return 'primary checklist rule violation'
    zone=settings.get('entry_zone')
    if zone:
        f=c.get('ath_frac')
        if f is None:return 'ATH unknown'
        if not zone[0]<=f<=zone[1]:return 'outside tier ATH zone'
    if settings.get('require_green_candle'):
        bars=[b for b in c.get('bars',[]) if b['t']+3600<=time.time()]
        if not bars or bars[-1]['c']<=bars[-1]['o']:return 'green confirmation missing'
    return None

def fallback_penalties(c,config):
    penalties=[];weights=config['tiers']['fallback']['penalties']
    for check in c.get('safety',{}).get('soft_checks',[]):
        if check.get('pass') is not True:penalties.append({'reason':check['name'],'points':weights['soft_risk_each']})
    s=c.get('safety') or {}
    if (num(s.get('top10_measured_pct')) or 0)>config['tiers']['primary']['max_top10_pct']:
        penalties.append({'reason':'top10_concentration','points':weights['top10']})
    for v in c.get('checklist_violations',[]):penalties.append({'reason':'checklist:'+v['key'],'points':weights['checklist_each']})
    market=market_reason(c,config['tiers']['fallback']['filters'])
    if market:penalties.append({'reason':'fallback_market:'+market,'points':weights['market']})
    return penalties

def evaluate(queue, market, config, post, history, root, checklist=None):
    from checklist_rules import normalize_item, features, violations
    from memory import read_json, atomic_json
    checklist=[normalize_item(x) for x in (checklist or [])]
    observed=read_json(root / "data/cache/checklist-market-observations.json", {})
    registry=TradedMints(root)
    fresh=[c for c in queue if c['mint'] not in registry]  # before scoring in BOTH tiers
    excluded=len(queue)-len(fresh)
    primary=[c for c in fresh if market_reason(c,config['filters']) is None]
    fallback=[c for c in fresh if (num(c.get('price_usd')) or 0)>0 and c.get('pool') and c.get('mint') not in SKIP_MINTS]
    union={c['mint']:c for c in primary+fallback}
    ranked=sorted(union.values(),key=lambda c:(score(c),c['mint']),reverse=True)
    reviewed=[]; p=[]; f=[]
    post('Data Scout',f"Tier market candidates: primary {len(primary)}, fallback market pool {len(fallback)}; {excluded} excluded: already traded (before scoring).")
    for c in ranked[:config['limits']['deep_dives']]:
        c['safety']=hard_review(c,market,config)
        c['score']=score(c);reviewed.append(c)
        post('Risk Manager',f"{c.get('symbol',c['mint'])}: {c['safety']['summary']}; owner lookup {c['safety'].get('owner_lookup','not completed')}")
        if c['safety'].get('hard_rug_pass') is not True:
            sym=c.get('symbol',c['mint'])
            for reason in c['safety'].get('hard_reasons') or ['hard entry gate failed or unknown']:
                post('Risk Manager',f"HARD BLOCK {sym}: {reason}")
            continue
        c['lesson_blocks']=[] # Old soft 3.5%/liquidity lessons do not override owner-approved new tiers.
        c['eligible']=True
        if c in primary:
            history(c,config)
            # Current DexScreener quote vs fetched nonfuture window high.
            if c.get('window_ath') and c.get('price_usd'):c['ath_frac']=c['price_usd']/c['window_ath']
            reason=tier_reason(c,config['tiers']['primary'])
            c['primary_reason']=reason
            if reason is None:p.append(c)
        # Checklist is a deterministic executable gate BEFORE final selection.
        if checklist and not c.get('bars') and any(r.get('field')=='green_confirmation' for item in checklist for r in item.get('rules',[])):
            history(c,config)
        c['active_checklist_rule_keys']=[x.get('key','?') for x in checklist if x.get('enabled') is not False]
        c['checklist_features']=features(c,config,observed.get(c['mint']))
        c['checklist_violations']=violations(checklist,c['checklist_features'])
        if c['checklist_violations']:
            post('Strategist',f"CHECKLIST APPLIED {c.get('symbol',c['mint'])}: "+str(c['checklist_violations'])+"; PRIMARY REJECT, FALLBACK SCORE PENALTY.")
            if c in p:p.remove(c)
        penalties=fallback_penalties(c,config)
        c['fallback_penalties']=penalties;c['fallback_score']=round(c['score']-sum(x['points'] for x in penalties),6)
        if c in fallback and tier_reason(c,config['tiers']['fallback']) is None:
            f.append(c)
            post('Bubble Map Analyst',f"FALLBACK SCORE {c.get('symbol',c['mint'])}: base {c['score']} minus "+str(penalties)+f" = {c['fallback_score']}; single-holder concentration, extensions, and checklist are penalties. Top-10, LP, clusters, wash, and fees already had to pass as hard gates.")
    p.sort(key=lambda c:(c['score'],c['mint']),reverse=True);f.sort(key=lambda c:(c['fallback_score'],c['mint']),reverse=True)
    chosen=p if p else f; tier='primary' if p else 'fallback'
    for c in chosen:
        c['entry_tier']=tier;c['tier_eligible']=True
        if tier=='fallback':c['score']=c['fallback_score']
    for c in fresh:
        observed[c['mint']]={k:c.get(k) for k in ('liquidity_usd','volume_24h_usd')}
    atomic_json(root / 'data/cache/checklist-market-observations.json',observed)
    post('Strategist',f"After hard blocks and entry criteria: primary {len(p)}, fallback-eligible {len(f)}. "+
         (f"Using {tier}; team ranks by 2*log10(1+liquidity)+log10(1+volume)-topHolder/20." if chosen else 'NO TRADE: every reviewed candidate failed/unknown hard checks or tier criteria; minimum never overrides hard blocks.'))
    baseline=dict(min_pair_age_hours=6,max_pair_age_days=60,min_liquidity_usd=12000,min_volume_24h_usd=8000,min_market_cap_usd=6000,max_market_cap_usd=20000000)
    before_after={'same_queue_size':len(fresh),'old_market_filters':sum(market_reason(c,baseline) is None for c in fresh),'new_primary_market_filters':len(primary),'new_fallback_market_filters':len(fallback)}
    return dict(before_after=before_after,primary_market=len(primary),fallback_market=len(fallback),primary=len(p),fallback=len(f),
                excluded_traded=excluded,reviewed=reviewed,candidates=chosen,tier=tier,market_review_cap=config['limits']['deep_dives'])
