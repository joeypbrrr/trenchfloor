"""Permanent forward-entry mint exclusion; historical simulations never seed it."""
from memory import atomic_json, read_json

class TradedMints:
    def __init__(self, root):
        self.path = root / 'data/traded_mints.json'
        self.data = read_json(self.path, {'scope':'forward:paper only; permanent exclusion', 'mints':{}})
        account = read_json(root / 'data/paper_account.json', {})
        for t in account.get('positions', []) + account.get('closed', []):
            if t.get('mode') == 'forward:paper':
                self.add(t, save=False)
        self.save()
    def add(self, trade, save=True):
        self.data['mints'].setdefault(trade['mint'], {k:trade.get(k) for k in ('id','entry_time','tier','symbol')})
        if save:self.save()
    def save(self):atomic_json(self.path, self.data)
    def __contains__(self, mint):return mint in self.data['mints']
