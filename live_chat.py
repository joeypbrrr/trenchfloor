"""Persistent factual agent chat and suggestion-only reviews of forward paper closes.
Historical/backtest fills are NEVER reviewed as live closes. No strategy writes.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

class LiveChat:
    def __init__(self, path):
        self.path = Path(path)
        try:
            self.data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.data = {"messages": [], "checklist": [], "reviewed": [], "started": time.time()}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data))
        tmp.replace(self.path)

    def record(self, event):
        generated = []
        if event.get("kind") not in ("heartbeat", "status"):
            self.data["messages"].append(event)
        trade = event.get("trade") or {}
        # A producer must explicitly attest a forward-paper realized close.
        # Current research.py produces historical backtest rows, not these.
        try:
            exit_ts = float(trade.get("exit_ts", 0))
            entry_ts = float(trade.get("entry_ts", 0))
            qualifies = (event.get("kind") == "trade_close" and event.get("is_live_close") is True
                and event.get("historical") is False and trade.get("realized") is True
                and trade.get("mode") == "forward:paper" and not trade.get("sample")
                and trade.get("id") and trade["id"] not in self.data["reviewed"]
                and self.data["started"] <= entry_ts < exit_ts <= time.time()
                and time.time() - exit_ts <= 120 and float(trade.get("pnl_usd", 0)) < 0)
        except (TypeError, ValueError):
            qualifies = False
        if qualifies:
            generated = self.review(trade, event.get("time"))
            self.data["messages"].extend(generated)
            self.data["reviewed"].append(trade["id"])
        self.data["messages"] = self.data["messages"][-1000:]
        if event.get("kind") != "heartbeat":
            self.save()
        return generated

    def review(self, t, timestamp):
        messages, suggestions = [], []
        def say(agent, text):
            messages.append({"agent": agent, "kind": "loss_review", "text": "RULE-BASED LOSS REVIEW / " + text, "time": timestamp or datetime.now(timezone.utc).isoformat(), "trade_id": t["id"]})
        def suggest(key, text):
            suggestions.append((key, text))
        say("Risk Manager", f"{t.get('symbol', '?')} closed for ${t['pnl_usd']:.2f}. Exit reason: {t.get('exit_reason') or 'not recorded'}. This describes recorded facts, not a proven cause.")
        frac = t.get("entry_frac_of_ath")
        say("Data Scout", f"Entry was {float(frac)*100:.1f}% of recorded window ATH ({(1-float(frac))*100:.1f}% below it)." if frac is not None else "Entry depth vs ATH was not recorded; cannot assess.")
        for name in ("liquidity", "volume"):
            before, after = t.get(f"entry_{name}_usd"), t.get(f"exit_{name}_usd")
            if before is not None and after is not None:
                say("Data Scout", f"Recorded {name}: ${before:,.2f} at entry → ${after:,.2f} at exit.")
                if before > 0 and after < before * 0.8:
                    suggest(f"{name}_drop", f"Test an entry-time {name} stability check; flag >20% deterioration against the preceding observation.")
            else:
                say("Data Scout", f"Entry/exit {name} snapshots missing; no change inferred.")
        top = t.get("top_human_pct")
        say("Bubble Map Analyst", f"Recorded top non-LP holder: {top}%. Linked-wallet changes were not recorded." if top is not None else "Holder concentration at the close was not recorded; cannot attribute this loss to wallets.")
        held = (float(t["exit_ts"])-float(t["entry_ts"]))/60
        say("Backtester", f"Held {held:.1f} minutes; modeled slippage per side: {t.get('slippage_bps_per_side', 'not recorded')} bps. Actual execution slippage is unavailable in paper research.")
        say("X/Twitter Scout", "No time-aligned, verified X data supplied with this close; no social explanation inferred.")
        if t.get("exit_reason") == "stop":
            suggest("stop_confirmation", "Backtest requiring a closed-candle dip-recovery confirmation before entry; compare OOS stop-out rate and missed winners before considering any filter change.")
        elif t.get("exit_reason") == "time":
            suggest("time_exit", "Backtest an earlier time-exit against the current hold limit, including fees/slippage and OOS missed recoveries.")
        else:
            suggest("loss_instrumentation", "Capture time-aligned entry/exit liquidity, volume, holders and cost assumptions before diagnosing another loss; do not change filters from incomplete evidence.")
        for key, text in suggestions:
            item = next((i for i in self.data["checklist"] if i["key"] == key), None)
            if item is None:
                item = {"key": key, "suggestion": text, "supporting_losses": 0, "trade_ids": [], "status": "SUGGESTION ONLY — not applied"}
                self.data["checklist"].append(item)
            if t["id"] not in item["trade_ids"]:
                item["trade_ids"].append(t["id"])
                item["supporting_losses"] += 1
            say("Strategist", f"Checklist suggestion ({item['supporting_losses']} supporting loss(es), not causal proof): {text} SUGGESTION ONLY: no strategy or filter was changed.")
        return messages
