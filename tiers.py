"""Primary/fallback selection with identical fail-closed hard rug checks.
All remote operations are PUBLIC READS: RPC, risk report and unsigned price quote.
No swap transaction is requested, signed, simulated with a wallet, or submitted.
"""
import math
import time
from urllib.parse import urlencode
from sources import num, http_json, SourceError, SKIP_MINTS, SKIP_SYMBOLS
from safety import review_token, TOKEN_LEGACY, TOKEN_2022, KNOWN_AMM
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
    reasons=[]; meta={'hard_rug_pass':False,'hard_rug_checks':[]}
    def check(name, passed, detail):
        meta['hard_rug_checks'].append({'name':name,'pass':passed,'detail':detail})
        if passed is not True:reasons.append(name+': '+detail)
    try:
        report,_=http_json('https://api.rugcheck.xyz/v1/tokens/'+c['mint']+'/report',timeout=12,attempts=2)
        if not isinstance(report,dict) or report.get('mint')!=c['mint']:raise SourceError('risk report mint mismatch/malformed')
        markets=[m for m in report.get('markets',[]) if isinstance(m,dict)]
        pool=next((m for m in markets if m.get('pubkey')==c['pool']),None)
        if not pool:raise SourceError('chosen DexScreener pool absent from LP report')
        vault=pool.get('liquidityA') if pool.get('mintA')==c['mint'] else pool.get('liquidityB') if pool.get('mintB')==c['mint'] else None
        if not vault:raise SourceError('chosen pool base vault unknown')
        batch=market.rpc.call('getMultipleAccounts',[[c['pool'],vault],{'encoding':'jsonParsed'}]).get('value')
        if not isinstance(batch,list) or len(batch)!=2:raise SourceError('pool/vault batch malformed')
        pool_account,vault_account=batch
        info=(((vault_account or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
        exact_pool=(isinstance(pool_account,dict) and pool_account.get('owner') in KNOWN_AMM
                    and info.get('mint')==c['mint'] and info.get('owner')==c['pool'])
        check('verified_pool_vault',exact_pool,'RPC exact vault mint/owner and known DEX program; no approximate liquidity exclusions')
        excluded={c['pool']} if exact_pool else set()
        s=review_token(market.rpc,c['mint'],None,20,require_complete=True,excluded_owners=excluded,
                       aggregate_holders=True,conservative_tail=False)
        meta.update(s)
        meta['hard_rug_checks']=meta.get('hard_rug_checks',[])
        check('complete_chain_read',s.get('status')=='pass',s.get('summary','unknown'))
        check('mint_authority_revoked',s.get('mint_authority_active') is False,'must be explicitly revoked')
        check('freeze_authority_revoked',s.get('freeze_authority_active') is False,'must be explicitly revoked')
        check('single_non_pool_holder_20pct',num(s.get('top_human_pct')) is not None and s['top_human_pct']<=20,
              'top-20 token accounts aggregated by owner, only exact verified chosen-pool vault excluded; '+str(s.get('top_human_pct'))+'%')
        # All non-pool executable addresses still count here (only pool owners excluded).
        lp=pool.get('lp') or {}; lp_mint=pool.get('mintLP') or lp.get('lpMint')
        burned=None
        if lp_mint and num(lp.get('lpLockedPct')) is not None and lp['lpLockedPct']>=99.99 and num(lp.get('lpTotalSupply')) and lp['lpTotalSupply']>0:
            supply=market.rpc.call('getTokenSupply',[lp_mint]).get('value') or {}
            if 'amount' in supply:burned=int(supply['amount'])==0
        check('LP_locked_or_burned',burned,'chosen pool LP fully burned: current LP mint supply zero plus positive historical LP issuance and >=99.99% lock/burn report; unknown/unverified locks reject')
        meta['lp_burned']=burned is True;meta['lp_locked']=None
        # A fresh sell quote PLUS canonical standard SPL semantics and no authorities
        # or extensions is evidence of sellability, not a guaranteed executable fill.
        safe_extensions={'metadataPointer','tokenMetadata','mintCloseAuthority','groupPointer','groupMemberPointer','tokenGroup','tokenGroupMember'}
        canonical=(s.get('token_program')==TOKEN_LEGACY or (s.get('token_program')==TOKEN_2022 and set(s.get('extensions') or []).issubset(safe_extensions))) and not s.get('risky_extensions')
        q=None
        if canonical and not reasons:
            size=config['paper']['notional_usd']
            raw=max(1,int(size/c['price_usd']*10**s['decimals']))
            params=urlencode(dict(inputMint=c['mint'],outputMint=SOL,amount=raw,slippageBps=100))
            q,_=http_json('https://lite-api.jup.ag/swap/v1/quote?'+params,timeout=12,attempts=2)
        route=(isinstance(q,dict) and q.get('inputMint')==c['mint'] and q.get('outputMint')==SOL
               and str(q.get('inAmount'))==str(raw) and (num(q.get('outAmount')) or 0)>0
               and any((r.get('swapInfo') or {}).get('ammKey')==c['pool'] for r in q.get('routePlan',[])))
        danger=any(any(word in str(x.get('name','')).lower() for word in ('honeypot','unsellable','non-transferable','freeze authority','mint authority')) for x in report.get('risks',[]))
        check('sellable_not_honeypot',canonical and route and not danger,'canonical SPL token, revoked authorities, no risky extensions, fresh read-only sell route through verified pool; no signed execution')
        meta['sell_quote']={k:q.get(k) for k in ('inAmount','outAmount','inputMint','outputMint','contextSlot')} if isinstance(q,dict) else None
        meta['hard_rug_pass']=not reasons
        meta['top10_measured_pct']=round(sum(x['pct'] for x in s.get('humans',[])[:10]),4)
        # assess_mint retains 8 humans for old UI; dedicated total is produced by safety.py.
        meta['top10_measured_pct']=s.get('top10_measured_pct',meta['top10_measured_pct'])
        meta['hard_reasons']=reasons
        meta['status']='pass' if not reasons else ('incomplete' if any(x['pass'] is None for x in meta['hard_rug_checks']) else 'fail')
        meta['summary']='PASS all hard rug blocks' if not reasons else '; '.join(reasons)
        return meta
    except (SourceError,ValueError,TypeError,KeyError,OverflowError) as exc:
        meta.update(status='incomplete',hard_rug_pass=False,hard_reasons=reasons+[str(exc)],summary='Hard rug check UNKNOWN: '+str(exc))
        return meta

def tier_reason(c, settings):
    s=c.get('safety') or {}
    if s.get('hard_rug_pass') is not True:return 'hard rug block failed/unknown'
    if s.get('top_human_pct',100)>settings['max_holder_pct']:return 'tier single-holder limit'
    if s.get('top10_measured_pct',100)>settings['max_top10_pct']:return 'tier top-10 concentration'
    zone=settings.get('entry_zone')
    if zone:
        f=c.get('ath_frac')
        if f is None:return 'ATH unknown'
        if not zone[0]<=f<=zone[1]:return 'outside tier ATH zone'
    if settings.get('require_green_candle'):
        bars=[b for b in c.get('bars',[]) if b['t']+3600<=time.time()]
        if not bars or bars[-1]['c']<=bars[-1]['o']:return 'green confirmation missing'
    return None

def evaluate(queue, market, config, post, history, root):
    registry=TradedMints(root)
    fresh=[c for c in queue if c['mint'] not in registry]  # before scoring in BOTH tiers
    excluded=len(queue)-len(fresh)
    primary=[c for c in fresh if market_reason(c,config['filters']) is None]
    fallback=[c for c in fresh if market_reason(c,config['tiers']['fallback']['filters']) is None]
    union={c['mint']:c for c in primary+fallback}
    ranked=sorted(union.values(),key=lambda c:(score(c),c['mint']),reverse=True)
    reviewed=[]; p=[]; f=[]
    post('Data Scout',f"Tier market candidates: primary {len(primary)}, fallback market pool {len(fallback)}; {excluded} excluded: already traded (before scoring).")
    for c in ranked[:config['limits']['deep_dives']]:
        c['safety']=hard_review(c,market,config)
        c['score']=score(c);reviewed.append(c)
        post('Risk Manager',f"{c.get('symbol',c['mint'])}: {c['safety']['summary']}; owner lookup {c['safety'].get('owner_lookup','not completed')}")
        if c['safety'].get('hard_rug_pass') is not True:continue
        c['lesson_blocks']=[] # Old soft 3.5%/liquidity lessons do not override owner-approved new tiers.
        c['eligible']=True
        if c in primary:
            history(c,config)
            # Current DexScreener quote vs fetched nonfuture window high.
            if c.get('window_ath') and c.get('price_usd'):c['ath_frac']=c['price_usd']/c['window_ath']
            reason=tier_reason(c,config['tiers']['primary'])
            c['primary_reason']=reason
            if reason is None:p.append(c)
        if c in fallback and tier_reason(c,config['tiers']['fallback']) is None:f.append(c)
    p.sort(key=lambda c:(c['score'],c['mint']),reverse=True);f.sort(key=lambda c:(c['score'],c['mint']),reverse=True)
    chosen=p if p else f; tier='primary' if p else 'fallback'
    for c in chosen:c['entry_tier']=tier;c['tier_eligible']=True
    post('Strategist',f"After hard blocks and entry criteria: primary {len(p)}, fallback-eligible {len(f)}. "+
         (f"Using {tier}; team ranks by 2*log10(1+liquidity)+log10(1+volume)-topHolder/20." if chosen else 'NO TRADE: every reviewed candidate failed/unknown hard checks or tier criteria; minimum never overrides hard blocks.'))
    baseline=dict(min_pair_age_hours=6,max_pair_age_days=60,min_liquidity_usd=12000,min_volume_24h_usd=8000,min_market_cap_usd=6000,max_market_cap_usd=20000000)
    before_after={'same_queue_size':len(fresh),'old_market_filters':sum(market_reason(c,baseline) is None for c in fresh),'new_primary_market_filters':len(primary),'new_fallback_market_filters':len(fallback)}
    return dict(before_after=before_after,primary_market=len(primary),fallback_market=len(fallback),primary=len(p),fallback=len(f),
                excluded_traded=excluded,reviewed=reviewed,candidates=chosen,tier=tier,market_review_cap=config['limits']['deep_dives'])
