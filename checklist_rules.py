"""Structured loss-checklist rules: primary rejects, fallback score penalties.
Never eval arbitrary text. Only allowlisted numeric/bool candidate fields and ops.
"""
import math
import time
from sources import num

FIELDS={'liquidity_change_pct','volume_change_pct','green_confirmation','liquidity_usd',
        'volume_24h_usd','market_cap_usd','top_holder_pct','entry_frac_of_ath','evidence_complete',
        'market_snapshot_age_seconds','planned_hold_seconds'}
OPS={'gte','lte','gt','lt','eq','neq'}
STATUS='ACTIVE — primary violation rejects; fallback violation penalizes score'

def normalize_item(item):
    item=dict(item)
    key=item.get('key','entry_evidence')
    defaults={
        'liquidity_drop':('liquidity_change_pct','gte',-20,'Require liquidity not to deteriorate by more than 20% vs preceding observed snapshot.'),
        'volume_drop':('volume_change_pct','gte',-20,'Require 24h volume not to deteriorate by more than 20% vs preceding observed snapshot.'),
        'stop_confirmation':('green_confirmation','eq',True,'Require a recently closed green hourly candle after a stop-out loss.'),
        'time_exit':('evidence_complete','eq',True,'Require complete entry market and holder evidence after a time-exit loss; 16h time limit unchanged.'),
        'loss_instrumentation':('evidence_complete','eq',True,'Require complete measured entry liquidity, volume, price and holder evidence.')}
    field,op,value,text=defaults.get(key,('evidence_complete','eq',True,'Require complete measured entry evidence for this recorded lesson.'))
    item.setdefault('rules',[{'field':field,'op':op,'value':value,'missing_violation':True}])
    item['rule_text']=text if 'rules' not in item else item.get('rule_text',item.get('suggestion',text))
    if item.get('rule_text','').startswith(('Test ','Backtest ','Capture ')):item['rule_text']=text
    item['suggestion']=item['rule_text']  # backwards-compatible display field, no advisory semantics
    item['status']=STATUS;item.setdefault('enabled',True)
    return item

def features(c,config,previous=None):
    s=c.get('safety') or {};previous=previous or {}
    bars=[b for b in c.get('bars',[]) if b.get('t',time.time())+3600<=time.time()]
    green=(bars[-1]['c']>bars[-1]['o']) if bars and time.time()-(bars[-1]['t']+3600)<=7200 else None
    f={k:num(c.get(k)) for k in ('liquidity_usd','volume_24h_usd','market_cap_usd')}
    f.update(top_holder_pct=num(s.get('top_human_pct')),entry_frac_of_ath=num(c.get('ath_frac')),
             green_confirmation=green,planned_hold_seconds=config['paper']['max_hold_seconds'],
             market_snapshot_age_seconds=(max(0,time.time()-c['metrics_observed_ts']) if c.get('metrics_observed_ts') else None))
    f['evidence_complete']=all(num(c.get(k)) is not None for k in ('liquidity_usd','volume_24h_usd','price_usd')) and f['top_holder_pct'] is not None
    for label,key in [('liquidity','liquidity_usd'),('volume','volume_24h_usd')]:
        a,b=num(previous.get(key)),num(c.get(key))
        f[label+'_change_pct']=(100*(b/a-1)) if a and a>0 and b is not None else None
    return f

def violations(items,values):
    bad=[]
    for original in items:
        item=normalize_item(original)
        if item.get('enabled') is False:continue
        rules=item.get('rules')
        if not isinstance(rules,list) or not rules:
            bad.append({'key':item.get('key','?'),'reason':'structured rules missing/malformed'});continue
        for r in rules:
            field,op=r.get('field'),r.get('op');expected=r.get('value');actual=values.get(field)
            if field not in FIELDS or op not in OPS or not isinstance(expected,(int,float,bool)) or not math.isfinite(float(expected)):
                bad.append({'key':item.get('key','?'),'reason':'unsupported structured rule'});continue
            if actual is None:
                if r.get('missing_violation',True):bad.append({'key':item.get('key','?'),'field':field,'reason':'required observation unavailable'})
                continue
            try:
                good={'gte':lambda:actual>=expected,'lte':lambda:actual<=expected,'gt':lambda:actual>expected,
                      'lt':lambda:actual<expected,'eq':lambda:actual==expected,'neq':lambda:actual!=expected}[op]()
            except (TypeError,ValueError):good=False
            if not good:bad.append({'key':item.get('key','?'),'field':field,'actual':actual,'op':op,'value':expected,'reason':'rule violation'})
    return bad
