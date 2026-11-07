"""Persistent lessons, variant registry, paper ledger, and the activity feed.

Files under data/ survive process restarts. A rule or a rejected variant is
not removed by the next cycle.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DISCLAIMER = "Paper trading / research only. No wallet. No real trades. Not financial advice."


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def et_now():
    return datetime.now(ET).isoformat()


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} is corrupt and was not overwritten: {exc}") from exc


class Memory:
    def __init__(self, root):
        self.root = root
        self.path = root / "data" / "lessons.json"
        self.feed_path = root / "data" / "feed.json"
        self.ledger_dir = root / "data" / "ledger"
        self.index_path = self.ledger_dir / "index.json"
        self.lessons_md = root / "LESSONS.md"
        self.best_md = root / "BEST_STRATEGY.md"
        self.data = {
            "rules": [],
            "rejected_mints": [],
            "observations": [],
            "variants": [],
            "champion_id": None,
            "loss_reviews": [],
        }
        self.feed = {"updated": None, "next_id": 1, "events": []}
        self.index = {
            "timezone": "America/New_York",
            "label": "PAPER / SIMULATED",
            "updated": None,
            "total_pnl_usd": 0,
            "trade_count": 0,
            "days": [],
            "trade_ids": [],
        }
        self._mint_index = {}
        self.load()

    def load(self):
        loaded = read_json(self.path, None)
        if isinstance(loaded, dict):
            for key in self.data:
                if key in loaded:
                    self.data[key] = loaded[key]
        feed = read_json(self.feed_path, None)
        if isinstance(feed, dict):
            self.feed.update({k: feed.get(k, self.feed.get(k)) for k in ("updated", "next_id", "events")})
        index = read_json(self.index_path, None)
        if isinstance(index, dict):
            self.index.update(index)
        self._reindex_mints()

    def _reindex_mints(self):
        self._mint_index = {}
        for row in self.data.get("rejected_mints") or []:
            if isinstance(row, dict) and row.get("mint"):
                self._mint_index[row["mint"]] = row

    def save(self):
        atomic_json(self.path, self.data)
        self.write_lessons_md()

    def save_feed(self):
        self.feed["updated"] = now_iso()
        atomic_json(self.feed_path, self.feed)

    def add_rule(self, code, rule, evidence, source, mint=None, symbol=None):
        rule = " ".join(str(rule).split())
        evidence = str(evidence)[:500]
        existing = next((r for r in self.data["rules"] if r.get("code") == code), None)
        created = False
        if existing is None:
            existing = {
                "id": f"R{len(self.data['rules']) + 1}",
                "code": code,
                "rule": rule,
                "evidence": evidence,
                "source": source,
                "time": now_iso(),
                "time_et": et_now(),
                "mints": [],
                "active": True,
            }
            self.data["rules"].append(existing)
            created = True
        else:
            existing["evidence"] = evidence
            if symbol or mint:
                existing["evidence"] = evidence
        new_mint = bool(mint and mint not in existing["mints"])
        if new_mint:
            existing["mints"].append(mint)
            existing["mints"] = existing["mints"][-12:]
        if created or new_mint:
            self._observe("rule" if created else "rule_example", f"{rule} — {evidence}", source)
            self.save()
        return existing, created

    def reject_mint(self, mint, reason, code, symbol=None):
        if not mint or mint in self._mint_index:
            return
        row = {
            "mint": mint,
            "symbol": symbol,
            "reason": str(reason)[:300],
            "code": code,
            "time": now_iso(),
            "time_et": et_now(),
        }
        self.data["rejected_mints"].append(row)
        self.data["rejected_mints"] = self.data["rejected_mints"][-500:]
        self._reindex_mints()
        self.save()

    def mint_rejection(self, mint):
        return self._mint_index.get(mint)

    def observe(self, kind, text, source):
        self._observe(kind, text, source)
        self.save()

    def _observe(self, kind, text, source):
        self.data["observations"].append({
            "time": now_iso(),
            "time_et": et_now(),
            "kind": kind,
            "source": source,
            "text": str(text)[:500],
        })
        self.data["observations"] = self.data["observations"][-80:]

    def blocks(self, candidate):
        reasons = []
        safety = candidate.get("safety") or {}
        rejected = self.mint_rejection(candidate.get("mint"))
        if rejected:
            reasons.append(rejected.get("reason") or "previously rejected mint")
        liq = candidate.get("liquidity_usd") or 0
        mcap = candidate.get("market_cap_usd") or 0
        for rule in self.data.get("rules") or []:
            if not rule.get("active", True):
                continue
            code = rule.get("code")
            text = rule.get("rule")
            if code == "live_mint_authority" and safety.get("mint_authority_active"):
                reasons.append(text)
            elif code == "live_freeze_authority" and safety.get("freeze_authority_active"):
                reasons.append(text)
            elif code == "holder_over_3_5" and safety.get("holder_over_3_5"):
                reasons.append(text)
            elif code == "risky_extension" and safety.get("risky_extensions"):
                reasons.append(text)
            elif code == "min_liquidity_15000" and liq < 15000:
                reasons.append(text)
            elif code == "min_liq_to_mcap_5pct" and mcap > 0 and (liq / mcap) < 0.05:
                reasons.append(text)
            elif code == "linked_cluster" and safety.get("cluster_fail"):
                reasons.append(text)
        # Preserve order, drop duplicates.
        seen = set()
        out = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                out.append(reason)
        return out

    def variant_record(self, vid):
        for row in self.data.get("variants") or []:
            if row.get("id") == vid:
                return row
        return None

    def can_test(self, vid):
        row = self.variant_record(vid)
        if row is None:
            return True
        if row.get("status") == "deferred" and int(row.get("attempts") or 0) < 3:
            return True
        return False

    def record_variant(self, record):
        current = self.variant_record(record["id"])
        record = dict(record)
        record["time"] = now_iso()
        record["time_et"] = et_now()
        if current is None:
            record["attempts"] = int(record.get("attempts") or 1)
            self.data["variants"].append(record)
        else:
            record["attempts"] = int(current.get("attempts") or 0) + 1
            current.clear()
            current.update(record)
        if record.get("status") == "champion":
            for row in self.data["variants"]:
                if row.get("id") != record["id"] and row.get("status") == "champion":
                    row["status"] = "replaced"
                    row["reason"] = "replaced by " + record["id"]
            self.data["champion_id"] = record["id"]
        self.save()

    def champion(self):
        cid = self.data.get("champion_id")
        if not cid:
            return None
        return self.variant_record(cid)

    def add_feed(self, agent, text, kind="info", trade=None):
        event = {
            "id": int(self.feed.get("next_id") or 1),
            "time": now_iso(),
            "agent": agent,
            "type": kind,
            "text": text,
        }
        if trade:
            event["trade"] = trade
        self.feed["next_id"] = event["id"] + 1
        self.feed["events"].insert(0, event)
        cap = 180
        del self.feed["events"][cap:]
        self.save_feed()
        return event

    def known_trade_ids(self):
        return set(self.index.get("trade_ids") or [])

    def record_trades(self, trades):
        known = self.known_trade_ids()
        fresh = []
        for trade in trades:
            if trade["id"] in known:
                continue
            known.add(trade["id"])
            fresh.append(trade)
            day = _exit_day(trade["exit_time"])
            path = self.ledger_dir / f"{day}.json"
            doc = read_json(path, {
                "date": day,
                "timezone": "America/New_York",
                "label": "PAPER / SIMULATED",
                "pnl_usd": 0,
                "trade_count": 0,
                "trades": [],
            })
            doc["trades"].append(trade)
            doc["trades"].sort(key=lambda t: t.get("exit_time") or "")
            doc["trade_count"] = len(doc["trades"])
            doc["pnl_usd"] = round(sum(t.get("pnl_usd") or 0 for t in doc["trades"]), 4)
            doc["label"] = "PAPER / SIMULATED"
            atomic_json(path, doc)
        if fresh:
            self._rebuild_index(known)
        return fresh

    def upsert_trade(self, trade):
        """Replace one journaled fill so a post-loss review stays on the ledger row."""
        trade_id = trade.get("id")
        exit_time = trade.get("exit_time")
        if not trade_id or not exit_time:
            return False
        day = _exit_day(exit_time)
        path = self.ledger_dir / f"{day}.json"
        doc = read_json(path, None)
        if not isinstance(doc, dict) or not isinstance(doc.get("trades"), list):
            return False
        for index, row in enumerate(doc["trades"]):
            if isinstance(row, dict) and row.get("id") == trade_id:
                doc["trades"][index] = trade
                doc["trade_count"] = len(doc["trades"])
                doc["pnl_usd"] = round(sum((item.get("pnl_usd") or 0) for item in doc["trades"] if isinstance(item, dict)), 4)
                atomic_json(path, doc)
                return True
        return False

    def record_loss_review(self, review):
        """Store one post-loss review in lessons. Same trade id replaces the prior text."""
        if not isinstance(review, dict) or not str(review.get("text") or "").strip():
            return None
        reviews = [row for row in (self.data.get("loss_reviews") or []) if isinstance(row, dict)]
        trade_id = review.get("trade_id")
        stored = {
            "trade_id": trade_id,
            "mint": review.get("mint"),
            "symbol": review.get("symbol"),
            "pnl_usd": review.get("pnl_usd"),
            "checked_at": review.get("checked_at"),
            "attempts": review.get("attempts"),
            "factors": review.get("factors") or [],
            "checks": review.get("checks") or [],
            "improve_entries": review.get("improve_entries"),
            "text": review.get("text"),
        }
        prior = next((row for row in reviews if trade_id and row.get("trade_id") == trade_id), None)
        if prior and prior.get("text") == stored["text"] and prior.get("improve_entries") == stored["improve_entries"]:
            return prior
        reviews = [row for row in reviews if not (trade_id and row.get("trade_id") == trade_id)]
        reviews.append(stored)
        self.data["loss_reviews"] = reviews[-40:]
        summary = stored.get("improve_entries") or stored["text"]
        self._observe("loss_review", f"{stored.get('symbol') or stored.get('mint') or 'loss'} post-loss review. {summary}", "Backtester")
        self.save()
        return stored

    def _rebuild_index(self, known_ids):
        days = []
        total = 0.0
        count = 0
        if self.ledger_dir.exists():
            for path in sorted(self.ledger_dir.glob("????-??-??.json")):
                doc = read_json(path, None)
                if not isinstance(doc, dict):
                    continue
                pnl = round(sum(t.get("pnl_usd") or 0 for t in doc.get("trades") or []), 4)
                wins = sum(1 for t in doc.get("trades") or [] if (t.get("pnl_usd") or 0) > 0)
                losses = sum(1 for t in doc.get("trades") or [] if (t.get("pnl_usd") or 0) <= 0)
                n = len(doc.get("trades") or [])
                days.append({
                    "date": doc.get("date") or path.stem,
                    "pnl_usd": pnl,
                    "trade_count": n,
                    "wins": wins,
                    "losses": losses,
                })
                total += pnl
                count += n
        self.index = {
            "timezone": "America/New_York",
            "label": "PAPER / SIMULATED",
            "disclaimer": DISCLAIMER,
            "updated": now_iso(),
            "total_pnl_usd": round(total, 4),
            "trade_count": count,
            "days": days,
            "trade_ids": sorted(known_ids),
        }
        atomic_json(self.index_path, self.index)

    def recent_trades(self, limit=12):
        rows = []
        if not self.ledger_dir.exists():
            return rows
        files = sorted(self.ledger_dir.glob("????-??-??.json"), reverse=True)
        for path in files:
            doc = read_json(path, None)
            if not isinstance(doc, dict):
                continue
            for trade in reversed(doc.get("trades") or []):
                rows.append(trade)
                if len(rows) >= limit:
                    return rows
        return rows

    def learn_from_safety(self, candidate):
        safety = candidate.get("safety") or {}
        mint = candidate.get("mint")
        symbol = candidate.get("symbol") or mint
        if safety.get("status") != "fail":
            return []
        created = []
        if safety.get("mint_authority_active"):
            row, was_new = self.add_rule(
                "live_mint_authority",
                "skip tokens with live mint authority",
                f"{symbol} still has a mint authority ({safety.get('summary')})",
                "Risk Manager",
                mint,
                symbol,
            )
            if was_new:
                created.append(row)
            self.reject_mint(mint, "skip tokens with live mint authority", "live_mint_authority", symbol)
        if safety.get("freeze_authority_active"):
            row, was_new = self.add_rule(
                "live_freeze_authority",
                "skip tokens with a live freeze authority",
                f"{symbol} still has a freeze authority",
                "Risk Manager",
                mint,
                symbol,
            )
            if was_new:
                created.append(row)
            self.reject_mint(mint, "skip tokens with a live freeze authority", "live_freeze_authority", symbol)
        if safety.get("risky_extensions"):
            names = ", ".join(safety["risky_extensions"])
            row, was_new = self.add_rule(
                "risky_extension",
                "skip tokens with permanentDelegate, transferHook, nonTransferable, transferFeeConfig, or defaultAccountState",
                f"{symbol} exposes {names}",
                "Risk Manager",
                mint,
                symbol,
            )
            if was_new:
                created.append(row)
            self.reject_mint(mint, "risky token extension", "risky_extension", symbol)
        if safety.get("holder_over_3_5"):
            row, was_new = self.add_rule(
                "holder_over_3_5",
                "skip tokens where a single non-LP, non-program holder owns more than 3.5% of supply",
                f"{symbol} top wallet {safety.get('top_human_pct')}% ({safety.get('top_human')})",
                "Bubble Map Analyst",
                mint,
                symbol,
            )
            if was_new:
                created.append(row)
            self.reject_mint(mint, "holder above 3.5%", "holder_over_3_5", symbol)
        if safety.get("cluster_fail"):
            row, was_new = self.add_rule(
                "linked_cluster",
                "skip tokens whose sampled wallets share a SOL funding source and together hold more than 3.5%",
                f"{symbol} cluster flags: {safety.get('cluster', {}).get('flags')}",
                "Bubble Map Analyst",
                mint,
                symbol,
            )
            if was_new:
                created.append(row)
            self.reject_mint(mint, "linked cluster above 3.5%", "linked_cluster", symbol)
        if safety.get("status") == "fail" and mint not in self._mint_index:
            self.reject_mint(mint, safety.get("summary") or "failed safety review", "safety_fail", symbol)
        return created

    def learn_from_losses(self, trades):
        created = []
        for trade in trades:
            if (trade.get("pnl_usd") or 0) >= 0:
                continue
            liq = trade.get("liquidity_usd") or 0
            mcap = trade.get("market_cap_usd") or 0
            self._observe(
                "paper_loss",
                f"{trade.get('symbol')} paper loss ${trade.get('pnl_usd')} on {trade.get('strategy_id')} "
                f"exit {trade.get('exit_reason')} liq {liq} mcap {mcap}",
                "Backtester",
            )
            if liq and liq < 15000:
                row, was_new = self.add_rule(
                    "min_liquidity_15000",
                    "skip tokens with liquidity under $15,000 after a losing paper trade in that liquidity band",
                    f"{trade.get('symbol')} lost ${trade.get('pnl_usd')} with liquidity ${liq:,.0f} on {trade.get('exit_time')}",
                    "Backtester",
                    trade.get("mint"),
                    trade.get("symbol"),
                )
                if was_new:
                    created.append(row)
            if mcap and liq and (liq / mcap) < 0.05:
                row, was_new = self.add_rule(
                    "min_liq_to_mcap_5pct",
                    "skip tokens whose liquidity is under 5% of market cap after a losing paper trade with that thin book",
                    f"{trade.get('symbol')} lost ${trade.get('pnl_usd')} with liquidity/mcap {liq / mcap:.3f}",
                    "Risk Manager",
                    trade.get("mint"),
                    trade.get("symbol"),
                )
                if was_new:
                    created.append(row)
        if created or any((t.get("pnl_usd") or 0) < 0 for t in trades):
            self.save()
        return created

    def write_lessons_md(self):
        lines = [
            "# Trenchfloor lessons",
            "",
            DISCLAIMER,
            "",
            "Persistent memory. Every agent reads the rules before acting. Tried and rejected strategy variants are not retested.",
            "",
            "## Rules",
            "",
        ]
        rules = self.data.get("rules") or []
        if not rules:
            lines.append("No standing rules yet. A cycle adds one when a token fails a safety check or a losing paper trade shows a concrete, repeatable cause.")
            lines.append("")
        for rule in rules:
            lines.append(f"- **{rule.get('time_et')}** — {rule.get('rule')}")
            lines.append(f"  - Source: {rule.get('source')}")
            lines.append(f"  - Evidence: {rule.get('evidence')}")
            if rule.get("mints"):
                lines.append("  - Examples: " + ", ".join(rule["mints"][:6]))
            lines.append("")
        lines += ["## Observations", ""]
        observations = self.data.get("observations") or []
        if not observations:
            lines.append("None yet.")
            lines.append("")
        for row in observations:
            lines.append(f"- **{row.get('time_et')}** ({row.get('source')}): {row.get('text')}")
        lines += ["", "## Post-loss reviews", ""]
        loss_reviews = self.data.get("loss_reviews") or []
        if not loss_reviews:
            lines.append("None yet.")
            lines.append("")
        for row in loss_reviews:
            flat = " ".join(str(row.get("text") or "").split())
            lines.append(f"- **{row.get('checked_at')}** {row.get('symbol') or row.get('mint')}: {flat}")
            lines.append("")
        lines += ["", "## Tried and rejected variants", ""]
        variants = [v for v in (self.data.get("variants") or []) if v.get("status") in {"rejected", "tried", "replaced", "champion", "deferred"}]
        if not variants:
            lines.append("None yet.")
            lines.append("")
        for row in variants:
            lines.append(f"- `{row.get('id')}` — **{row.get('status')}** at {row.get('time_et')}. {row.get('reason') or ''}")
        lines += ["", "## Rejected mints", ""]
        mints = self.data.get("rejected_mints") or []
        if not mints:
            lines.append("None yet.")
            lines.append("")
        for row in mints[-40:]:
            lines.append(f"- `{row.get('symbol') or row.get('mint')}` `{row.get('mint')}` — {row.get('reason')} ({row.get('time_et')})")
        text = "\n".join(lines).rstrip() + "\n"
        self.lessons_md.write_text(text)

    def write_champion_md(self, variant, oos, pools, goal=None):
        lines = [
            "# Trenchfloor best strategy",
            "",
            f"**{DISCLAIMER}**",
            "",
        ] + standing_goal_lines(goal) + [
            f"Champion `{variant['id']}`, promoted {variant.get('time_et') or et_now()} ET because it beat the previous out-of-sample record.",
            "",
            "## Rule",
            "",
            variant.get("name") or "",
            "",
            "Each simulated trade uses a fresh $100 paper notional. Entries are next-bar opens after a bounce inside the zone. A bar that sets the window high is never an entry. If a later bar touches the stop and the target, the stop is used.",
            "",
            "## Out-of-sample result that earned the promotion",
            "",
            f"- Trades: {oos.get('trades')}",
            f"- Average P&L per trade: ${oos.get('expectancy_usd')}",
            f"- Net P&L: ${oos.get('net_usd')}",
            f"- Win rate: {oos.get('win_rate')}",
            f"- Profit factor: {oos.get('profit_factor')}",
            "",
            "## Pools in that test",
            "",
        ]
        for pool in pools:
            lines.append(f"- {pool.get('symbol')} `{pool.get('mint')}` pool `{pool.get('pool')}`")
        lines += [
            "",
            "ATH is the highest high in the free GeckoTerminal window fetched for each pool (daily up to 90 bars and hourly up to 168). It is not a guaranteed lifetime high when the endpoint returns less. In-sample numbers are not the promotion basis and are stored on the variant record in `data/lessons.json`.",
            "",
        ]
        lines += goal_progress_lines(goal if goal is not None else self.data.get("goal_status"))
        self.best_md.write_text("\n".join(lines))

    def write_champion_md_current(self, goal):
        """Rewrite BEST_STRATEGY.md every cycle so the standing goal and goal progress stay current."""
        self.data["goal_status"] = goal
        self.save()
        champ = self.champion()
        if champ:
            self.write_champion_md(champ, champ.get("oos") or {}, champ.get("pools") or [], goal)
            return
        lines = [
            "# Trenchfloor best strategy",
            "",
            f"**{DISCLAIMER}**",
            "",
        ] + standing_goal_lines(goal) + [
            "No out-of-sample champion yet. This file keeps the standing dip rule until a variant passes the out-of-sample gates.",
            "",
            "## Standing principle",
            "",
            "Buy dips. Never top-tick. Entry zone: 20–45% of the window ATH, after a bounce bar that does not set the high.",
            "",
        ] + goal_progress_lines(goal)
        self.best_md.write_text("\n".join(lines))

    def ensure_champion_doc(self):
        champ = self.champion()
        if not champ:
            return
        text = self.best_md.read_text() if self.best_md.exists() else ""
        if champ["id"] not in text:
            oos = champ.get("oos") or {}
            self.write_champion_md(champ, oos, champ.get("pools") or [])


def standing_goal_lines(goal=None):
    low = (goal or {}).get("monthly_goal_low_usd", 3000)
    high = (goal or {}).get("monthly_goal_high_usd", 5000)
    return [
        "## Standing goal",
        "",
        f"Joey's standing goal: at least **${low:,.0f}–${high:,.0f} extra per month**. Every agent reads this; the Strategist ranks promotions by projected monthly P&L toward it.",
        "",
        "The goal never loosens the safety rules: a version still needs at least 5 out-of-sample paper trades, a positive out-of-sample average, and must not be previously rejected. Everything here is paper / simulated; projections are not income.",
        "",
    ]


def goal_progress_lines(goal):
    lines = ["## Goal progress", ""]
    if not goal:
        return lines + ["No goal projection yet. The next full cycle writes one.", ""]
    lines.append(goal.get("status_line") or "")
    lines.append("")
    lines.append(f"Paper ticket: ${goal.get('notional_usd', 100):,.0f}. Updated {et_now()} ET.")
    lines.append("")
    lines.append("| Version | Role | Status | OOS trades | Avg $/trade | Trades/mo | Projected $/mo at ticket | Ticket for low goal | Ticket for high goal | Qualifies |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in goal.get("candidates") or []:
        f = lambda v, pre="$": "—" if v is None else f"{pre}{v:,.2f}" if isinstance(v, float) else f"{pre}{v}"
        lines.append(
            f"| `{r.get('id')}` | {r.get('role')} | {r.get('status')} | {r.get('oos_trades') if r.get('oos_trades') is not None else '—'} | "
            f"{f(r.get('expectancy_usd'))} | {f(r.get('trades_per_month'), '')} | {f(r.get('monthly_usd'))} | "
            f"{f(r.get('ticket_for_low_usd'))} | {f(r.get('ticket_for_high_usd'))} | {'yes' if r.get('qualifies') else 'no'} |"
        )
    lines += ["", goal.get("method") or "", ""]
    return lines


def _exit_day(iso_text):
    dt = datetime.fromisoformat(iso_text)
    return dt.astimezone(ET).date().isoformat()
