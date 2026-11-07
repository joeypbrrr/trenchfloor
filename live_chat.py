"""Persistent factual agent chat and structured-rule reviews of forward paper closes.
Historical/backtest fills are NEVER reviewed as live closes. No strategy writes.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from checklist_rules import normalize_item, STATUS


def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _flag_text(item):
    if isinstance(item, dict):
        key = item.get("key") or item.get("reason") or item.get("name")
        if key:
            return str(key)
    return str(item)


class LiveChat:
    def __init__(self, path):
        self.path = Path(path)
        try:
            self.data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.data = {"messages": [], "checklist": [], "reviewed": [], "started": time.time()}

        self.data["checklist"]=[normalize_item(x) for x in self.data.get("checklist",[])]
        self.data.setdefault("trade_reviews", [])

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data))
        tmp.replace(self.path)

    def _close_ready(self, event, trade, allow_journal_replay):
        # Same provenance gate as loss checklist reviews. Wins qualify too.
        # Historical, sampled, and backtest rows never do.
        exit_ts = _finite(trade.get("exit_ts"))
        entry_ts = _finite(trade.get("entry_ts"))
        pnl = _finite(trade.get("pnl_usd"))
        if exit_ts is None or entry_ts is None or pnl is None or not trade.get("id"):
            return False
        now = time.time()
        return (event.get("kind") == "trade_close" and event.get("is_live_close") is True
            and event.get("historical") is False and trade.get("realized") is True
            and trade.get("mode") == "forward:paper" and not trade.get("sample")
            and self.data["started"] <= entry_ts < exit_ts <= now
            and (allow_journal_replay or now - exit_ts <= 120))

    def record(self, event, allow_journal_replay=False):
        generated = []
        if event.get("kind") not in ("heartbeat", "status"):
            self.data["messages"].append(event)
        trade = event.get("trade") or {}
        ready = self._close_ready(event, trade, allow_journal_replay)
        pnl = _finite(trade.get("pnl_usd")) if ready else None
        # Checklist rules stay loss-only. The single trade_review covers wins and losses.
        if ready and pnl < 0 and trade["id"] not in self.data["reviewed"]:
            generated.extend(self.review(trade, event.get("time")))
            self.data["reviewed"].append(trade["id"])
        reviewed_ids = self.data.setdefault("trade_reviews", [])
        if ready and trade["id"] not in reviewed_ids:
            generated.append(self.compose_trade_review(trade, event.get("time")))
            reviewed_ids.append(trade["id"])
        if generated:
            self.data["messages"].extend(generated)
        self.data["messages"] = self.data["messages"][-1000:]
        if event.get("kind") != "heartbeat":
            self.save()
        return generated

    def compose_trade_review(self, t, timestamp):
        """One factual review per forward-paper close. Missing fields stay unknown."""
        pnl = _finite(t.get("pnl_usd"))
        reason = t.get("exit_reason") if isinstance(t.get("exit_reason"), str) and t.get("exit_reason") else "not recorded"
        symbol = t.get("symbol") or "?"
        outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "flat"
        checks = [c for c in (t.get("hard_rug_checks") or []) if isinstance(c, dict)]
        passed = [c["name"] for c in checks if c.get("pass") is True and c.get("name")]
        failed = [c["name"] for c in checks if c.get("pass") is False and c.get("name")]
        audit = t.get("checklist_audit") if isinstance(t.get("checklist_audit"), dict) else None
        violations = audit.get("violations") if audit and isinstance(audit.get("violations"), list) else []
        penalties = t.get("fallback_penalties") if isinstance(t.get("fallback_penalties"), list) else []
        entry_px, exit_px = _finite(t.get("entry_price")), _finite(t.get("exit_price"))
        drops = []
        for name in ("liquidity", "volume"):
            before, after = _finite(t.get(f"entry_{name}_usd")), _finite(t.get(f"exit_{name}_usd"))
            if before is not None and after is not None and before > 0 and after < before * 0.8:
                drops.append(f"{name} ${before:,.2f} at entry → ${after:,.2f} at exit")

        right = []
        if pnl > 0:
            right.append(f"Recorded P&L +${pnl:.2f} after modeled fees and slippage.")
        if reason == "target":
            right.append("Exit reason recorded as target.")
        if passed:
            right.append("Recorded hard checks passed: " + ", ".join(passed) + ".")
        if entry_px is not None and exit_px is not None and exit_px > entry_px and pnl > 0:
            right.append(f"Exit price ${exit_px:.8g} was above entry price ${entry_px:.8g}.")
        if not right:
            right.append("No positive P&L, target exit, or passed hard check was recorded.")

        wrong = []
        if pnl < 0:
            wrong.append(f"Recorded P&L ${pnl:.2f} after modeled fees and slippage.")
        elif pnl == 0:
            wrong.append("Recorded P&L was $0.00.")
        if reason in ("stop", "time") or (pnl < 0 and reason not in ("stop", "time", "target")):
            wrong.append(f"Exit reason recorded as {reason}.")
        if failed:
            wrong.append("Recorded hard checks failed: " + ", ".join(failed) + ".")
        if violations:
            wrong.append("Recorded checklist violations: " + ", ".join(_flag_text(v) for v in violations) + ".")
        if not wrong:
            wrong.append("No negative P&L, stop, time exit, failed hard check, or checklist violation was recorded.")

        flags = []
        if failed:
            flags.append("Present: failed hard checks " + ", ".join(failed) + ".")
        elif checks:
            flags.append("No failed hard check was recorded.")
        else:
            flags.append("Hard checks were not recorded on this close.")
        if violations:
            flags.append("Present: checklist violations " + ", ".join(_flag_text(v) for v in violations) + ".")
        elif audit is not None:
            flags.append("Checklist audit recorded no violations.")
        else:
            flags.append("Checklist audit was not recorded.")
        if penalties:
            flags.append("Present: fallback penalties " + ", ".join(_flag_text(v) for v in penalties) + ".")
        top = t.get("top_human_pct")
        flags.append(f"Recorded top non-LP holder {top}%. No later holder change was recorded." if top is not None else "Top non-LP holder was not recorded.")
        frac = _finite(t.get("entry_frac_of_ath"))
        flags.append(f"Entry was {frac * 100:.1f}% of the recorded window ATH." if frac is not None else "Entry depth versus window ATH was not recorded.")
        for name in ("liquidity", "volume"):
            before, after = _finite(t.get(f"entry_{name}_usd")), _finite(t.get(f"exit_{name}_usd"))
            if before is None or after is None:
                flags.append(f"Entry/exit {name} was not both recorded; no {name} change inferred.")
            else:
                flags.append(f"Recorded {name} ${before:,.2f} at entry → ${after:,.2f} at exit.")
                if before > 0 and after < before * 0.8:
                    flags.append(f"Present: {name} at exit was more than 20% below the entry snapshot.")

        improve = []
        if violations:
            improve.append("Later entries already have to clear the checklist violations recorded on this trade.")
        if failed:
            improve.append("Do not repeat an entry with these recorded failed hard checks: " + ", ".join(failed) + ".")
        if drops:
            improve.append("Weigh the recorded deterioration before a similar entry: " + "; ".join(drops) + ".")
        if not improve:
            if reason == "target" and pnl > 0:
                improve.append("No missed flag was recorded. This close does not justify a tighter entry filter.")
            elif reason == "stop":
                improve.append("The recorded stop was hit and no failed hard check, checklist violation, or 20% liquidity/volume drop was stored. No new entry filter is identified from this close alone.")
            elif reason == "time":
                improve.append("The recorded time stop ended the trade. No additional entry defect was stored, so no new entry filter is identified.")
            else:
                improve.append("No recorded entry defect is available, so no new entry filter is identified.")
        posted = t.get("post_loss_review") if isinstance(t.get("post_loss_review"), dict) else None
        if pnl is not None and pnl < 0 and posted and str(posted.get("improve_entries") or "").strip():
            improve.append(str(posted["improve_entries"]).strip())

        lines = [
            f"TRADE REVIEW / {symbol} / {outcome} / P&L {'+' if pnl > 0 else ''}${pnl:.2f} / exit {reason}.",
            "What went right: " + " ".join(right),
            "What went wrong: " + " ".join(wrong),
            "Red flags: " + " ".join(flags),
            "How to improve future entries: " + " ".join(improve),
        ]
        if pnl < 0:
            avoid = [f"Recorded loss of ${abs(pnl):.2f} on exit {reason}. Fields that were not recorded stay unknown."]
            if failed or violations or drops:
                avoid.append("The present flags above are the only recorded warnings available for avoiding a repeat.")
            else:
                avoid.append("No missed red flag was recorded. Do not invent one.")
            stop = _finite(t.get("stop_fraction"))
            if reason == "stop" and stop is not None:
                avoid.append(f"The recorded stop fraction was {stop * 100:.0f}%. This review does not change that exit rule.")
            lines.append("How to avoid similar losses: " + " ".join(avoid))
        if pnl is not None and pnl < 0 and posted and str(posted.get("text") or "").strip():
            lines.append(str(posted["text"]).strip())
        return {
            "agent": "Backtester",
            "kind": "trade_review",
            "text": "\n".join(lines),
            "time": timestamp or datetime.now(timezone.utc).isoformat(),
            "trade_id": t.get("id"),
        }

    def rewrite_trade_review(self, trade, timestamp=None):
        """Replace the one trade_review for this close, or append it if none was stored."""
        msg = self.compose_trade_review(trade, timestamp)
        for existing in self.data.get("messages") or []:
            if existing.get("kind") == "trade_review" and existing.get("trade_id") == trade.get("id"):
                existing["text"] = msg["text"]
                existing["agent"] = msg["agent"]
                self.save()
                return existing
        self.data.setdefault("messages", []).append(msg)
        reviewed = self.data.setdefault("trade_reviews", [])
        if trade.get("id") and trade.get("id") not in reviewed:
            reviewed.append(trade["id"])
        self.data["messages"] = self.data["messages"][-1000:]
        self.save()
        return msg

    def review(self, t, timestamp):
        messages, suggestions = [], []
        def say(agent, text):
            messages.append({"agent": agent, "kind": "loss_review", "text": "RULE-BASED LOSS REVIEW / " + text, "time": timestamp or datetime.now(timezone.utc).isoformat(), "trade_id": t["id"]})
        def suggest(key, text):
            suggestions.append((key, text))
        say("Risk Manager", f"{t.get('symbol', '?')} closed for ${t['pnl_usd']:.2f}. Exit reason: {t.get('exit_reason') or 'not recorded'}. This describes recorded facts, not a proven cause.")
        say("Strategist", ("Entry rationale: ranked "+t["tier"]+" candidate with common hard rug blocks and recorded team majority. Green-candle confirmation optional; fallback ATH optional. " if t.get("tier") else "Entry rationale: current dip plus closed green confirmation, measured chain/holder safety, and recorded team majority. ") + ((t.get("team") or {}).get("rule") or "Full entry vote was not recorded.") + " A passing entry check is not a guarantee; the approved checklist policy applies structured rules to subsequent selections, not proof of causation.")
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
                item = {"key": key, "suggestion": text, "supporting_losses": 0, "trade_ids": [], "status": STATUS}
                item=normalize_item(item)
                self.data["checklist"].append(item)
            if t["id"] not in item["trade_ids"]:
                item["trade_ids"].append(t["id"])
                item["supporting_losses"] += 1
            item.update(normalize_item(item))
            say("Strategist", f"CHECKLIST RULE ADDED/UPDATED ({item['supporting_losses']} supporting loss(es), not causal proof): {item['rule_text']} Rules {item['rules']}. Applied before selection: PRIMARY violation rejects; FALLBACK violation penalizes score.")
        return messages
