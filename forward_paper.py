"""Forward PAPER ONLY account. Public DexScreener observations, no execution API.

Journaled entries/closed fills survive restart. Caller serializes account access by
holding the runner flock. Exits are processed before entry gates, including halt.
"""
import time
import uuid
from datetime import datetime, timezone
from memory import atomic_json, read_json
from daily_stop import DailyStop
from backtest import dollar_pnl, slippage_bps
from team import team_review
from traded_mints import TradedMints


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


class PaperAccount:
    def __init__(self, root, config):
        self.root, self.config = root, config
        self.path = root / 'data/paper_account.json'
        self.data = read_json(self.path, None)
        if self.data is None:
            start = float(config.get('paper', {}).get('starting_balance_usd', 1000))
            self.data = dict(started=iso(time.time()), starting_balance_usd=start,
                             cash_usd=start, last_entry_ts=None, positions=[], closed=[])
            self.save()

    def save(self):
        atomic_json(self.path, self.data)

    def snapshot(self):
        d = self.data
        realized = sum(t['pnl_usd'] for t in d['closed'])
        return dict(started=d['started'], starting_balance_usd=d['starting_balance_usd'],
                    cash_usd=round(d['cash_usd'], 4), realized_pnl_usd=round(realized, 4),
                    balance_usd=round(d['starting_balance_usd'] + realized, 4),
                    reserved_usd=round(sum(p['notional_usd'] for p in d['positions']), 4),
                    positions=d['positions'], last_entry_ts=d['last_entry_ts'],
                    sizing=('primary cap $100, fallback cap $50; min(cap, 10% realized balance, 10% available cash); max 24 open positions' if self.config.get('tiered_selection_enabled') else '10% of realized account balance, capped at $100 and available cash; max one open position'),
                    tier_pnl_usd={tier:round(sum(t['pnl_usd'] for t in d['closed'] if t.get('tier','primary')==tier),6) for tier in ('primary','fallback')})

    def reconcile(self, memory, close_event):
        # Durable account journal is written BEFORE ledger/chat. Replay is idempotent.
        for t in self.data['closed']:
            memory.record_trades([t])
            if not t.get('review_delivered'):
                close_event(t)
                t['review_delivered'] = True
                self.save()

    def manage(self, market, memory, post, close_event, now=None):
        now = now or time.time()
        self.reconcile(memory, close_event)
        positions = self.data['positions']
        if not positions:
            return []
        rows, errors = market.dexscreener_pairs([p['mint'] for p in positions])
        if errors:
            post('Risk Manager', 'Paper position mark unavailable; no invented exit: ' + '; '.join(errors), 'error')
        closed = []
        for p in list(positions):
            matches = [r for r in rows if r.get('mint') == p['mint'] and r.get('pool') == p['pool']]
            if not matches:
                continue
            r = matches[0]
            price = r.get('price_usd')
            if price is None or price <= 0:
                continue
            p['mark_price_usd'], p['mark_time'] = price, iso(now)
            change = price / p['entry_price'] - 1
            why = ('stop' if change <= -p['stop_fraction'] else 'target' if change >= p['target_fraction']
                   else 'time' if now - p['entry_ts'] >= p['max_hold_seconds'] else None)
            if not why:
                continue
            pnl = dollar_pnl(p['entry_price'], price, p['notional_usd'], p['cost_rate'])
            t = {**p, 'exit_ts': now, 'exit_time': iso(now), 'exit_price': price,
                 'exit_reason': why, 'pnl_usd': round(pnl, 6), 'realized': True,
                 'exit_liquidity_usd': r.get('liquidity_usd'), 'exit_volume_usd': r.get('volume_24h_usd')}
            self.data['cash_usd'] += p['notional_usd'] + t['pnl_usd']
            positions.remove(p)
            self.data['closed'].append(t)
            self.save()
            self.reconcile(memory, close_event)
            # Latch immediately on realized close; never gates this method.
            DailyStop(self.root).status(self.config)
            post('Backtester', f"FORWARD PAPER close {t['symbol']} ({t['mint']}): {why}, ${t['pnl_usd']:.2f} net after modeled fees/slippage. {t['dex_url']}", 'trade', t)
            closed.append(t)
        self.save()
        return closed

    def try_entry(self, tokens, market, memory, post, now=None):
        if self.config.get('tiered_selection_enabled'):
            return self.try_tiered_entry(tokens,market,memory,post,now)
        now = now or time.time()
        daily = DailyStop(self.root).status(self.config)
        if daily['halted']:
            post('Risk Manager', 'DAILY $300 REALIZED PROFIT HALT: no new entry until ET midnight; exits remain enabled.')
            return None
        last = self.data['last_entry_ts']
        if last is not None and now - last < self.config.get('entry_interval_seconds', 3600):
            post('Risk Manager', 'ROLLING HOUR ENTRY LIMIT: prior persisted entry is less than 3600 seconds old; exits remain enabled.')
            return None
        if self.data['positions']:
            post('Risk Manager', 'One open paper position already uses the allocation slot; management/exits remain enabled.')
            return None
        paper = self.config['paper']
        for token in tokens:
            if not token.get('eligible') or not token.get('in_entry_zone'):
                continue
            # Require a recently CLOSED green hourly candle; no future high/candle.
            bars = [b for b in token.get('bars', []) if b['t'] + 3600 <= now]
            if not bars:
                continue
            b = bars[-1]
            if now - (b['t'] + 3600) > 7200 or b['c'] <= b['o']:
                continue
            high = max([v['h'] for v in bars] + [token.get('seed_ath') or 0])
            price = token.get('price_usd')
            if not price or high <= 0 or b['h'] >= high:
                continue
            frac = price / high
            zone = self.config['entry_zone']
            if not zone['min_frac_of_ath'] <= frac <= zone['max_frac_of_ath']:
                continue
            balance = self.snapshot()['balance_usd']
            size = round(min(paper['notional_usd'], balance * paper['allocation_fraction'], self.data['cash_usd']), 4)
            if size <= 0:
                return None
            variant = dict(id='forward_dip_20_45', stop=paper['stop_fraction'], target=paper['target_fraction'], zone_high=zone['max_frac_of_ath'])
            slip = slippage_bps(token.get('liquidity_usd'), paper)
            t = dict(id='paper-' + uuid.uuid4().hex, mode='forward:paper', realized=False,
                     mint=token['mint'], pool=token['pool'], symbol=token.get('symbol', '?'), name=token.get('name', '?'),
                     entry_ts=now, entry_time=iso(now), entry_price=price, entry_frac_of_ath=frac,
                     notional_usd=size, slippage_bps_per_side=slip,
                     cost_rate=(paper['fee_bps_per_side'] + slip) / 10000,
                     entry_liquidity_usd=token.get('liquidity_usd'), entry_volume_usd=token.get('volume_24h_usd'),
                     top_human_pct=token.get('safety', {}).get('top_human_pct'),
                     stop_fraction=paper['stop_fraction'], target_fraction=paper['target_fraction'], max_hold_seconds=paper['max_hold_seconds'],
                     dex_url=token.get('dex_url') or 'https://dexscreener.com/solana/' + token['pool'],
                     gmgn_url=token.get('gmgn_url', ''), strategy_id=variant['id'])
            result = team_review(t, token, variant, [], self.config, market.source_status.get('x_twitter'))
            for v in result['votes']:
                post(v['agent'], f"FORWARD PAPER {t['symbol']} vote {v['vote']}: {v['reason']}")
            if not result['approved']:
                continue
            t['team'] = result
            t['proposed_by'] = result['proposed_by']
            self.data['positions'].append(t)
            self.data['cash_usd'] -= size
            self.data['last_entry_ts'] = now
            self.save()  # both cash debit and rolling-hour gate persist atomically
            post(t['proposed_by'], f"FORWARD PAPER entry {t['symbol']} ({t['mint']}) @ {price}; allocation ${size:.2f}, 12% stop / 25% target / 16h time stop. {t['dex_url']}", 'trade', t)
            return t
        post('Strategist', 'No forward paper entry: no fully scam-filtered current dip with a recent closed green confirmation. No trade minimum; no forced trade.')
        return None

    def try_tiered_entry(self, tokens, market, memory, post, now=None):
        from tiers import tier_reason, market_reason
        now=now or time.time()
        registry=TradedMints(self.root)
        if DailyStop(self.root).status(self.config)['halted']:
            post('Risk Manager','DAILY $300 REALIZED PROFIT HALT: minimum-entry rule yields; exits remain enabled.')
            return None
        last=self.data['last_entry_ts']
        if last is not None and now-last<self.config['entry_interval_seconds']:
            post('Risk Manager','ROLLING HOUR ENTRY LIMIT: minimum yields to the persisted 3600s cap; open positions still managed.')
            return None
        if len(self.data['positions'])>=self.config['paper']['max_open_positions']:
            post('Risk Manager','No entry: paper position capacity reached; no unmanaged entry or fabricated fill.')
            return None
        paper=self.config['paper']
        for token in tokens:
            if token['mint'] in registry:
                post('Data Scout',token['mint']+' excluded: already traded; permanent forward-entry exclusion.')
                continue
            tier=token.get('entry_tier')
            if tier not in ('primary','fallback') or token.get('tier_eligible') is not True:continue
            settings=self.config['tiers'][tier]
            filters=self.config['filters'] if tier=='primary' else settings['filters']
            if market_reason(token,filters,now) or tier_reason(token,settings):continue
            # Entry guard repeats common hard-block attestation; no team/minimum bypass.
            safety=token.get('safety') or {}
            if safety.get('hard_rug_pass') is not True or not safety.get('hard_rug_checks') or any(c.get('pass') is not True for c in safety['hard_rug_checks']):continue
            size=round(min(settings['notional_usd'],self.snapshot()['balance_usd']*paper['allocation_fraction'],self.data['cash_usd']*paper['allocation_of_free_cash_fraction']),4)
            if size<0.01:
                post('Risk Manager','No entry: paper cash below one-cent funded size; no fabricated borrowing.')
                return None
            frac=token.get('ath_frac')
            variant=dict(id='forward_ranked_'+tier,stop=paper['stop_fraction'],target=paper['target_fraction'],zone_high=(settings.get('entry_zone') or [0,1e100])[1])
            slip=slippage_bps(token.get('liquidity_usd'),paper)
            t=dict(id='paper-'+uuid.uuid4().hex,mode='forward:paper',realized=False,tier=tier,selection_score=token['score'],
                   mint=token['mint'],pool=token['pool'],symbol=token.get('symbol','?'),name=token.get('name','?'),
                   entry_ts=now,entry_time=iso(now),entry_price=token['price_usd'],entry_frac_of_ath=frac,notional_usd=size,
                   slippage_bps_per_side=slip,cost_rate=(paper['fee_bps_per_side']+slip)/10000,
                   entry_liquidity_usd=token.get('liquidity_usd'),entry_volume_usd=token.get('volume_24h_usd'),
                   top_human_pct=safety.get('top_human_pct'),stop_fraction=paper['stop_fraction'],target_fraction=paper['target_fraction'],
                   max_hold_seconds=paper['max_hold_seconds'],dex_url='https://dexscreener.com/solana/'+token['pool'],gmgn_url=token.get('gmgn_url',''),
                   strategy_id=variant['id'],hard_rug_checks=safety['hard_rug_checks'])
            vote_config={**self.config,'holder_fail_pct':settings['max_holder_pct'],'filters':filters}
            result=team_review(t,token,variant,[],vote_config,market.source_status.get('x_twitter'))
            for v in result['votes']:post(v['agent'],f"{tier.upper()} PAPER {t['symbol']} vote {v['vote']}: {v['reason']}")
            if not result['approved']:continue
            t['team']=result;t['proposed_by']=result['proposed_by']
            self.data['positions'].append(t);self.data['cash_usd']-=size;self.data['last_entry_ts']=now
            self.save()  # journal is authoritative if process stops before registry write
            registry.add(t)
            post(t['proposed_by'],f"{tier.upper()} FORWARD PAPER entry {t['name']} / {t['symbol']} ({t['mint']}) @ {t['entry_price']}; size ${size:.2f}; score {t['selection_score']}; 12% stop / 25% target / 16h time stop. ONE TRADE PER COIN EVER: mint permanently excluded after this entry. {t['dex_url']}",'trade',t)
            return t
        post('Risk Manager','NO TRADE: no funded, untraded, team-approved candidate with every hard rug check known/pass; minimum never overrides hard blocks.')
        return None
