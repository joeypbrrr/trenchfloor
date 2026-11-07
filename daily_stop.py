"""Persistent, mode-specific entry gate; never blocks closing a position.

Forward PAPER closes and historical backtests use separate modes.
Only explicitly realized forward fills count in forward mode. No future-dated candle exit is realized. Duplicate strategy variants of
the same economic fill count once. The latch survives P&L falling below target,
restart, or disabling/re-enabling, and expires only at ET midnight.
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from memory import atomic_json, read_json
from sources import num

ET = ZoneInfo('America/New_York')


def mode_for(config):
    if config.get('forward_paper_enabled', False):
        return 'forward:paper'
    source = config.get('candidate_source', 'legacy')
    proxy = ':fee_proxy' if source != 'legacy' and config.get('fee_proxy_enabled', False) else ''
    return source + proxy + ':backtest'


def fill_key(trade):
    return tuple(str(trade.get(k, '')) for k in ('mint', 'entry_time', 'exit_time', 'entry_price', 'exit_price', 'notional_usd'))


def close_time(trade):
    # exit_ts in historical files is the candle OPEN, exit_time is its CLOSE.
    try:
        dt = datetime.fromisoformat(trade['exit_time'].replace('Z', '+00:00'))
        return dt if dt.tzinfo else None
    except (KeyError, ValueError, TypeError):
        return None


class DailyStop:
    def __init__(self, root):
        self.root = root
        self.path = root / 'data' / 'daily_stop.json'

    def status(self, config, now=None):
        now = now or datetime.now(timezone.utc)
        today = now.astimezone(ET).date()
        mode = mode_for(config)
        target = float(config.get('daily_profit_stop_usd', 300))
        if target <= 0:
            raise ValueError('daily_profit_stop_usd must be positive')
        fills, seen = [], set()
        for path in (self.root / 'data' / 'ledger').glob('????-??-??.json'):
            doc = read_json(path, {})
            for trade in doc.get('trades') or []:
                if trade.get('mode', 'legacy:backtest') != mode:
                    continue
                if mode == 'forward:paper' and trade.get('realized') is not True:
                    continue
                closed = close_time(trade)
                pnl = num(trade.get('pnl_usd'))
                if not closed or closed > now or closed.astimezone(ET).date() != today or pnl is None:
                    continue
                identity = fill_key(trade)
                if identity in seen:
                    continue
                seen.add(identity)
                fills.append((closed, identity, pnl))
        fills.sort(key=lambda r: (r[0], r[1]))
        total = 0.0
        crossed = None
        for closed, _identity, pnl in fills:
            total += pnl
            if crossed is None and total >= target:
                crossed = closed.isoformat()
        state = read_json(self.path, {'modes': {}})
        previous = state.get('modes', {}).get(mode, {})
        latched = previous.get('date_et') == str(today) and previous.get('halted', False)
        enabled = bool(config.get('daily_stop_enabled', False))
        halted = enabled and (latched or crossed is not None)
        reset = datetime.combine(today + timedelta(days=1), datetime.min.time(), ET)
        result = {'enabled': enabled, 'halted': halted, 'mode': mode,
                  'date_et': str(today), 'target_usd': target, 'realized_pnl_usd': round(total, 4),
                  'realized_fills': len(fills), 'reset_at': reset.isoformat(),
                  'hit_at': previous.get('hit_at') if latched else crossed,
                  'basis': ('deduplicated realized forward paper closes only; no unrealized P&L' if mode == 'forward:paper' else 'deduplicated closed historical simulations, not forward income; future exits excluded'),
                  'blocks': 'new entries only; position exits are never gated'}
        if enabled:
            state.setdefault('modes', {})[mode] = result
            atomic_json(self.path, state)
        return result
