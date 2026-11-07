#!/usr/bin/env python3
"""Trenchfloor research loop.

Six paper-trading research agents share one state file. No wallet, no signing keys,
no real orders. Public data only. Optional key-only GMGN discovery; no trading endpoints.
"""
from __future__ import annotations

import argparse
import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from backtest import beats_goal, describe_variant, goal_projection, metrics, oos_window_seconds, simulate, split_samples, variant_catalog
from memory import DISCLAIMER, Memory, atomic_json, et_now, now_iso
from publish_data import publish
from safety import review_token, sample_links
from team import review_trades
from sources import SKIP_MINTS, SKIP_SYMBOLS, MarketData, SourceError, num, ResilientRpcClient
from candidate_sources import candidates as source_candidates, fee_filter_reason
from daily_stop import DailyStop, mode_for, close_time, fill_key

ROOT = Path(__file__).resolve().parent
ROLES = [
    ("Risk Manager", "RM", "ff7a00"),
    ("Bubble Map Analyst", "BA", "ffb000"),
    ("X/Twitter Scout", "XS", "ff5a1f"),
    ("Data Scout", "DS", "ff9a3c"),
    ("Backtester", "BT", "ffc266"),
    ("Strategist", "ST", "ff6a00"),
]
ROLE_NAMES = [r[0] for r in ROLES]

MEMORY = None
MARKET = None
STATE = {}
AGENTS = {}
HEARTS = {}
NO_PUBLISH = False
FEED_DIRTY = False
LAST_FEED_PUSH = 0.0
LAST_FULL_PUSH = 0.0
PUBLISHING = False


def log(msg):
    print(datetime.now().strftime("%H:%M:%S"), msg, flush=True)


def load_config():
    return json.loads((ROOT / "config.json").read_text())


def load_prior():
    path = ROOT / "data" / "research.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        log(f"research.json unreadable: {exc}")
        return {"errors": [{"agent": "System", "text": f"research.json unreadable: {exc}"}]}


def boot(config):
    global MEMORY, MARKET
    MEMORY = Memory(ROOT)
    if not MEMORY.path.exists():
        MEMORY.save()
    else:
        MEMORY.write_lessons_md()
    MEMORY.ensure_champion_doc()
    if not MEMORY.feed_path.exists():
        MEMORY.save_feed()
    MARKET = MarketData(config, ROOT / "data" / "cache" / "negative.json")
    prior = load_prior()
    STATE.clear()
    STATE.update({
        "name": "Trenchfloor",
        "disclaimer": DISCLAIMER,
        "scope": "Solana meme-coin paper research",
        "ok": False,
        "cycle_count": prior.get("cycle_count") or 0,
        "last_cycle": prior.get("last_cycle"),
        "next_cycle": prior.get("next_cycle"),
        "generated": None,
        "data_status": "Starting",
        "errors": [],
        "agents": [],
        "activity": list(prior.get("activity") or [])[:80],
        "watchlist": prior.get("watchlist") or [],
        "rejected_review": prior.get("rejected_review") or [],
        "filter_rejects_sample": prior.get("filter_rejects_sample") or [],
        "best": prior.get("best"),
        "strategist_note": prior.get("strategist_note") or "",
        "risk_note": prior.get("risk_note") or "",
        "summary": prior.get("summary") or {},
        "sources": prior.get("sources") or {},
        "report": prior.get("report") or {},
        "health": prior.get("health") or {},
        "ledger": prior.get("ledger") or {},
        "recent_trades": prior.get("recent_trades") or [],
        "lessons_preview": prior.get("lessons_preview") or [],
    })
    for name, initials, color in ROLES:
        AGENTS[name] = {
            "role": name,
            "initials": initials,
            "color": color,
            "status": "idle",
            "task": "Reading lessons before the first cycle.",
            "detail": "",
            "latest_action": "",
            "heartbeat": now_iso(),
        }
        HEARTS[name] = time.time()
    STATE["agents"] = [AGENTS[name] for name in ROLE_NAMES]
    save_state()


def save_state():
    STATE["generated"] = now_iso()
    STATE["agents"] = [AGENTS[name] for name in ROLE_NAMES]
    STATE["disclaimer"] = DISCLAIMER
    atomic_json(ROOT / "data" / "research.json", STATE)


def update(role, status, task, detail="", action=None):
    agent = AGENTS[role]
    agent["status"] = status
    agent["task"] = task
    agent["detail"] = detail
    agent["heartbeat"] = now_iso()
    if action:
        agent["latest_action"] = action[:220]
    HEARTS[role] = time.time()
    save_state()


def post(agent, text, kind="info", trade=None, publish_feed=True):
    global FEED_DIRTY
    event = MEMORY.add_feed(agent, text, kind, trade)
    STATE["activity"].insert(0, {"id": event["id"], "time": event["time"], "agent": agent, "text": text, "type": kind})
    del STATE["activity"][80:]
    if agent in AGENTS:
        AGENTS[agent]["latest_action"] = text[:220]
        AGENTS[agent]["heartbeat"] = now_iso()
        HEARTS[agent] = time.time()
    FEED_DIRTY = True
    save_state()
    if publish_feed:
        maybe_publish_feed()
    return event


def note_error(agent, text):
    log("ERROR " + text)
    STATE["errors"].append({"time": now_iso(), "agent": agent, "text": text[:500]})
    post(agent, text, "error", publish_feed=False)
    try:
        MEMORY.observe("error", text, agent)
    except Exception:
        log(traceback.format_exc())


def maybe_publish_feed(force=False):
    global FEED_DIRTY, LAST_FEED_PUSH, PUBLISHING
    if NO_PUBLISH or PUBLISHING:
        return
    if not FEED_DIRTY and not force:
        return
    config = load_config()
    gap = float(config.get("feed_publish_min_seconds", 45))
    if not force and LAST_FEED_PUSH and time.time() - LAST_FEED_PUSH < gap:
        return
    PUBLISHING = True
    try:
        publish(root=ROOT, feed_only=True)
        LAST_FEED_PUSH = time.time()
        FEED_DIRTY = False
    except Exception as exc:
        STATE["errors"].append({"time": now_iso(), "agent": "System", "text": f"Feed publish failed: {exc}"[:500]})
        log(f"feed publish failed: {exc}")
    finally:
        PUBLISHING = False


def maybe_publish_full(force=False):
    global FEED_DIRTY, LAST_FULL_PUSH, PUBLISHING
    if NO_PUBLISH or PUBLISHING:
        return
    config = load_config()
    gap = float(config.get("full_publish_min_seconds", 600))
    if not force and LAST_FULL_PUSH and time.time() - LAST_FULL_PUSH < gap:
        return
    PUBLISHING = True
    try:
        result = publish(root=ROOT, feed_only=False)
        LAST_FULL_PUSH = time.time()
        FEED_DIRTY = False
        if result.get("published"):
            STATE.setdefault("health", {})["last_published"] = result["published"]
            save_state()
    except Exception as exc:
        STATE["errors"].append({"time": now_iso(), "agent": "System", "text": f"Publish failed: {exc}"[:500]})
        log(f"publish failed: {exc}")
    finally:
        PUBLISHING = False


def lessons_banner():
    rules = MEMORY.data.get("rules") or []
    variants = MEMORY.data.get("variants") or []
    blocked = [v for v in variants if v.get("status") in {"rejected", "tried", "champion", "replaced"}]
    low, high, _ = goal_settings(load_config())
    return f"Read {len(rules)} standing rules and {len(blocked)} variants that will not be retested. Standing goal: ${low:,.0f}–${high:,.0f}/mo extra (paper projection; OOS rules never loosened)."


def blank(mint):
    return {
        "mint": mint,
        "symbol": None,
        "name": None,
        "pool": None,
        "dex": None,
        "quote_mint": None,
        "quote_symbol": None,
        "price_usd": None,
        "liquidity_usd": None,
        "liquidity_base": None,
        "volume_24h_usd": None,
        "market_cap_usd": None,
        "fdv_usd": None,
        "market_cap_from": None,
        "created_ts": None,
        "metrics_source": None,
        "twitter": [],
        "description": "",
        "discovered_from": [],
        "dex_url": f"https://dexscreener.com/solana/{mint}",
        "gmgn_url": f"https://gmgn.ai/sol/token/{mint}",
        "bubble_url": f"https://app.bubblemaps.io/sol/token/{mint}",
    }


def overlay(dest, src, keys):
    for key in keys:
        if src.get(key) not in (None, ""):
            dest[key] = src[key]


def discover(config):
    if config.get("candidate_source", "legacy") != "legacy":
        update("Data Scout", "working", "Reading the explicitly selected discovery adapter (no DexScreener boost scanning).")
        rows, report = source_candidates(MARKET, config)
        queue = []
        for row in rows:
            if row["mint"] in SKIP_MINTS:
                continue
            if MEMORY.mint_rejection(row["mint"]):
                report["skipped_rejected"] += 1
                continue
            row = {**blank(row["mint"]), **row}
            queue.append(row)
        post("Data Scout", report["label"] + ". Real/organic volume is not independently verified. Unknown global fees fail closed unless the separately opted-in PROXY is used.")
        return queue, report
    report = {"gecko": [], "gecko_errors": [], "list_errors": [], "pair_errors": [], "skipped_rejected": 0, "rows": 0}
    update("X/Twitter Scout", "working", "Checking whether a free X API answers, then reading DexScreener boost and profile links.", action="Checking X API")
    x_status = MARKET.probe_x()
    post("X/Twitter Scout", x_status.get("detail") or "X status missing")
    update("Data Scout", "working", "Pulling DexScreener boosts/profiles and GeckoTerminal new and trending pools.", action="Fetching free pair lists")
    birdeye = MARKET.probe_birdeye()
    if not birdeye.get("ok"):
        post("Data Scout", birdeye.get("detail") or "Birdeye unavailable", "error")
    lists, list_errors = MARKET.dexscreener_lists()
    report["list_errors"] = list_errors
    for err in list_errors:
        note_error("Data Scout", "DexScreener list failed: " + err)
    gecko_rows = []
    for kind in ("trending_pools", "new_pools"):
        try:
            rows = MARKET.gecko_pools(kind)
            report["gecko"].append({"kind": kind, "rows": len(rows)})
            gecko_rows.extend(rows)
            log(f"gecko {kind}: {len(rows)}")
        except SourceError as exc:
            report["gecko_errors"].append(f"{kind}: {exc}")
            note_error("Data Scout", f"GeckoTerminal {kind} failed: {exc}")
    by_mint = {}
    for row in gecko_rows:
        mint = row.get("mint") or ""
        if not mint:
            continue
        dest = by_mint.setdefault(mint, blank(mint))
        overlay(dest, row, ["symbol", "name", "pool", "quote_mint", "price_usd", "liquidity_usd", "volume_24h_usd", "market_cap_usd", "fdv_usd", "created_ts", "metrics_source"])
        for src in row.get("discovered_from") or []:
            if src not in dest["discovered_from"]:
                dest["discovered_from"].append(src)
    x_linked = 0
    for row in lists:
        mint = row.get("mint") or ""
        if not mint or mint in SKIP_MINTS:
            continue
        dest = by_mint.setdefault(mint, blank(mint))
        for url in row.get("twitter") or []:
            if url not in dest["twitter"]:
                dest["twitter"].append(url)
        if dest["twitter"]:
            x_linked += 1
        if row.get("description") and not dest["description"]:
            dest["description"] = row["description"][:280]
        label = row.get("list") or "dexscreener"
        if label not in dest["discovered_from"]:
            dest["discovered_from"].append(label)
    report["x_linked"] = sum(1 for c in by_mint.values() if c["twitter"])
    report["discovered"] = len(by_mint)
    if report["x_linked"]:
        examples = [c for c in by_mint.values() if c["twitter"]][:5]
        bits = []
        for c in examples:
            bits.append(f"{c.get('symbol') or c['mint'][:6]} {c['twitter'][0]}")
        post("X/Twitter Scout", f"{report['x_linked']} discovered Solana mints have an X link on DexScreener. No tweet text was fetched. Examples: " + "; ".join(bits))
    else:
        post("X/Twitter Scout", "No X links on the DexScreener rows returned this cycle. No tweets invented.")
    update("X/Twitter Scout", "working", x_status.get("detail") or "X API unavailable", detail=f"{report['x_linked']} X links", action=AGENTS["X/Twitter Scout"]["latest_action"])

    ranked = sorted(by_mint.values(), key=_priority, reverse=True)
    limit = int((config.get("limits") or {}).get("enrich_mints", 30))
    queue = []
    for cand in ranked:
        if cand["mint"] in SKIP_MINTS or (cand.get("symbol") or "").upper() in SKIP_SYMBOLS:
            continue
        if MEMORY.mint_rejection(cand["mint"]):
            report["skipped_rejected"] += 1
            continue
        queue.append(cand)
        if len(queue) >= limit:
            break
    pairs, pair_errors = MARKET.dexscreener_pairs([c["mint"] for c in queue]) if queue else ([], [])
    report["pair_errors"] = pair_errors
    for err in pair_errors:
        note_error("Data Scout", "DexScreener pair batch failed: " + err)
    best = {}
    for pair in pairs:
        mint = pair.get("mint") or ""
        if not mint:
            continue
        current = best.get(mint)
        if current is None or (pair.get("liquidity_usd") or 0) > (current.get("liquidity_usd") or 0):
            best[mint] = pair
    for cand in queue:
        pair = best.get(cand["mint"])
        if not pair:
            continue
        overlay(cand, pair, ["symbol", "name", "pool", "dex", "quote_mint", "quote_symbol", "price_usd", "liquidity_usd", "liquidity_base", "volume_24h_usd", "market_cap_usd", "fdv_usd", "created_ts"])
        cand["metrics_source"] = "dexscreener"
    report["enriched"] = len(queue)
    report["dex_pairs"] = len(pairs)
    return queue, report


def _priority(cand):
    liq = cand.get("liquidity_usd") or 0
    twitter = 50000 if cand.get("twitter") else 0
    trending = 20000 if any("trending" in s for s in cand.get("discovered_from") or []) else 0
    return liq + twitter + trending


def screen(candidates, config):
    filters = dict(config["filters"])
    new_source = config.get("candidate_source", "legacy") != "legacy"
    if new_source:
        filters["min_market_cap_usd"] = config.get("new_source_min_market_cap_usd", 6000)
        filters["strict_market_cap"] = True
    now = time.time()
    passed = []
    rejected = []
    counts = {}
    for cand in candidates:
        reason = (fee_filter_reason(cand, config) if new_source else None) or _filter_reason(cand, filters, now)
        if reason is None:
            blocks = MEMORY.blocks(cand)
            if blocks:
                reason = "lesson: " + blocks[0]
        if reason:
            counts[reason] = counts.get(reason, 0) + 1
            cand = dict(cand)
            cand["filter_reason"] = reason
            cand["age_hours"] = _age_hours(cand, now)
            rejected.append(cand)
        else:
            cand["age_hours"] = _age_hours(cand, now)
            if cand.get("market_cap_usd") and cand.get("liquidity_usd") is not None:
                cand["liq_to_mcap"] = cand["liquidity_usd"] / cand["market_cap_usd"]
            passed.append(cand)
    passed.sort(key=lambda c: c.get("liquidity_usd") or 0, reverse=True)
    rejected.sort(key=lambda c: c.get("liquidity_usd") or 0, reverse=True)
    return passed, rejected, counts


def _age_hours(cand, now):
    if not cand.get("created_ts"):
        return None
    return round((now - cand["created_ts"]) / 3600.0, 2)


def _filter_reason(cand, filters, now):
    symbol = (cand.get("symbol") or "").upper()
    if symbol in SKIP_SYMBOLS or cand.get("mint") in SKIP_MINTS:
        return "quote asset"
    quote = cand.get("quote_mint")
    if quote and quote not in SKIP_MINTS:
        return "quote is not SOL, USDC, or USDT"
    if not quote:
        return "quote asset unknown"
    if not cand.get("created_ts"):
        return "pair age unknown"
    age_h = (now - cand["created_ts"]) / 3600.0
    if age_h < float(filters["min_pair_age_hours"]):
        return "pair younger than minimum age"
    if age_h > float(filters["max_pair_age_days"]) * 24.0:
        return "pair older than maximum age"
    if cand.get("liquidity_usd") is None:
        return "liquidity unknown"
    if cand["liquidity_usd"] < float(filters["min_liquidity_usd"]):
        return "liquidity below minimum"
    if cand.get("volume_24h_usd") is None:
        return "volume unknown"
    if cand["volume_24h_usd"] < float(filters["min_volume_24h_usd"]):
        return "volume below minimum"
    mcap = cand.get("market_cap_usd")
    if mcap is None and not filters.get("strict_market_cap") and cand.get("fdv_usd") is not None:
        cand["market_cap_usd"] = cand["fdv_usd"]
        cand["market_cap_from"] = "fdv"
        mcap = cand["fdv_usd"]
    if mcap is None:
        return "market cap unknown"
    if mcap < float(filters["min_market_cap_usd"]):
        return "market cap below minimum"
    if mcap > float(filters["max_market_cap_usd"]):
        return "market cap above maximum"
    return None


def review_candidates(candidates, config):
    limits = config.get("limits") or {}
    deep = candidates[: int(limits.get("deep_dives", 4))]
    holder_limit = float(config.get("holder_fail_pct", 3.5))
    reviewed = []
    for cand in deep:
        label = cand.get("symbol") or cand["mint"][:6]
        update("Risk Manager", "working", f"Checking mint and freeze authority and Token-2022 extensions on {label}.", action=f"RPC review {label}")
        update("Bubble Map Analyst", "working", f"Measuring holder concentration on {label}. Fail line is one non-LP, non-program wallet above {holder_limit}%.", action=f"Holders {label}")
        try:
            safety = review_token(MARKET.rpc, cand["mint"], cand.get("liquidity_base"), holder_limit, require_complete=config.get("candidate_source", "legacy") != "legacy" or config.get("rpc_resilience_enabled", False))
        except Exception as exc:
            note_error("Risk Manager", f"{label} safety review crashed: {exc}")
            log(traceback.format_exc())
            safety = {"status": "incomplete", "summary": str(exc), "hard_fails": [str(exc)], "warnings": [], "checks": []}
        cand["safety"] = safety
        reviewed.append(cand)
    # Link samples run after every mint review so a signature lookup cannot
    # starve the next token's authority and holder checks.
    cluster_left = int(limits.get("cluster_tokens", 2))
    for cand in reviewed:
        safety = cand["safety"]
        if safety.get("status") == "incomplete" or not safety.get("humans") or cluster_left <= 0:
            safety["cluster"] = {"flags": [], "fail": False, "detail": "linked-wallet sample not run (incomplete review, no human holder, or RPC budget reserved for the mint checks)"}
            safety["cluster_fail"] = False
            continue
        cluster_left -= 1
        label = cand.get("symbol") or cand["mint"][:6]
        try:
            cluster = sample_links(MARKET.rpc, safety.get("humans") or [], holder_limit)
        except Exception as exc:
            cluster = {"flags": [], "fail": False, "error": str(exc), "detail": str(exc)}
            note_error("Bubble Map Analyst", f"{label} link sample failed: {exc}")
        safety["cluster"] = cluster
        if cluster.get("fail"):
            safety["cluster_fail"] = True
            safety["status"] = "fail"
            safety.setdefault("hard_fails", []).append("linked wallets share a funding source and together exceed 3.5%")
            safety["summary"] = "FAIL " + "; ".join(safety["hard_fails"])
        else:
            safety["cluster_fail"] = False
    for cand in reviewed:
        safety = cand["safety"]
        label = cand.get("symbol") or cand["mint"][:6]
        if safety.get("status") == "fail":
            MEMORY.learn_from_safety(cand)
            speaker = "Bubble Map Analyst" if safety.get("holder_over_3_5") or safety.get("cluster_fail") else "Risk Manager"
            post(speaker, f"FAIL {label}: {safety.get('summary')} {cand['bubble_url']}", "error")
        elif safety.get("status") == "incomplete":
            post("Risk Manager", f"{label} safety check incomplete: {safety.get('summary')}. Not treated as a pass.", "error")
        else:
            post("Risk Manager", f"PASS {label}: {safety.get('summary')}")
            if safety.get("warnings"):
                post("Bubble Map Analyst", f"{label} warnings: " + "; ".join(safety["warnings"][:3]))
            else:
                detail = (safety.get("cluster") or {}).get("detail") or ""
                post("Bubble Map Analyst", f"{label} holder check passed. Top non-LP non-program wallet {safety.get('top_human_pct')}%. {detail} {cand['bubble_url']}")
        blocks = MEMORY.blocks(cand)
        cand["lesson_blocks"] = blocks
        cand["eligible"] = safety.get("status") == "pass" and not blocks
        if cand["eligible"]:
            post("Strategist", f"{label} is eligible for a paper dip test.")
        elif blocks and safety.get("status") == "pass":
            post("Strategist", f"{label} passed the chain checks and is still blocked by a lesson: {blocks[0]}", "error")
            cand["eligible"] = False
    return reviewed


ATH_NOTE = (
    "ATH is the max high across fetched GeckoTerminal daily candles (up to the configured limit) "
    "and hourly candles. When the free endpoint returns a shorter window, this is not a lifetime ATH. "
    "The backtest seeds its running high with daily highs that printed before the first hourly bar only."
)


def load_history(token, config):
    limits = config.get("limits") or {}
    pool = token.get("pool")
    if not pool:
        token["history_error"] = "no pool address"
        return False
    daily_bars = []
    hourly_bars = []
    try:
        daily = MARKET.gecko_ohlcv(pool, "day", limits.get("daily_bars", 90))
        daily_bars = daily["bars"]
        token["daily_bars"] = len(daily_bars)
        if daily.get("base_symbol") and not token.get("symbol"):
            token["symbol"] = daily["base_symbol"]
        if daily.get("base_name") and not token.get("name"):
            token["name"] = daily["base_name"]
    except SourceError as exc:
        token["history_error"] = f"daily OHLCV: {exc}"
        note_error("Backtester", f"{token.get('symbol') or token['mint']} daily OHLCV failed: {exc}")
    try:
        hourly = MARKET.gecko_ohlcv(pool, "hour", limits.get("hourly_bars", 168))
        hourly_bars = hourly["bars"]
        token["hourly_bars"] = len(hourly_bars)
        if hourly.get("base_symbol") and not token.get("symbol"):
            token["symbol"] = hourly["base_symbol"]
        if hourly.get("base_name") and not token.get("name"):
            token["name"] = hourly["base_name"]
    except SourceError as exc:
        token["history_error"] = (token.get("history_error") or "") + f" hourly OHLCV: {exc}"
        note_error("Backtester", f"{token.get('symbol') or token['mint']} hourly OHLCV failed: {exc}")
    highs = [b["h"] for b in daily_bars] + [b["h"] for b in hourly_bars]
    if not highs:
        return False
    ath = max(highs)
    token["window_ath"] = ath
    token["ath_note"] = ATH_NOTE
    price = hourly_bars[-1]["c"] if hourly_bars else token.get("price_usd")
    token["last_price"] = price
    if price and ath:
        token["ath_frac"] = price / ath
        zone = config.get("entry_zone") or {}
        token["in_entry_zone"] = float(zone.get("min_frac_of_ath", 0.2)) <= token["ath_frac"] <= float(zone.get("max_frac_of_ath", 0.45))
    seed = None
    if hourly_bars and daily_bars:
        prior = [b["h"] for b in daily_bars if b["t"] < hourly_bars[0]["t"]]
        if prior:
            seed = max(prior)
    token["seed_ath"] = seed
    token["bars"] = hourly_bars
    token["history_start"] = hourly_bars[0]["t"] if hourly_bars else None
    token["history_end"] = hourly_bars[-1]["t"] if hourly_bars else None
    return len(hourly_bars) >= int((config.get("paper") or {}).get("min_hourly_bars", 30))


def daily_stop_status(config, announce=False):
    status = DailyStop(ROOT).status(config)
    STATE["daily_stop"] = status
    if announce:
        post("Risk Manager", f"Daily profit stop {'HALTED — no new team votes/entries until ET midnight' if status['halted'] else ('armed' if status['enabled'] else 'OFF')}: ${status['realized_pnl_usd']:.2f} realized in {status['mode']} / ${status['target_usd']:.0f}. {status['basis']}.", publish_feed=False)
    return status


def run_variants(tokens, config):
    paper = config.get("paper") or {}
    limits = config.get("limits") or {}
    proposed = []
    for variant in variant_catalog():
        if MEMORY.can_test(variant["id"]):
            proposed.append(variant)
        if len(proposed) >= int(limits.get("variants_per_cycle", 2)):
            break
    if not proposed:
        post("Strategist", "Every catalogued dip variant is already tried, rejected, or the champion. No retest.")
        return {"proposed": [], "results": []}
    names = "; ".join(v["id"] for v in proposed)
    post("Strategist", "Proposing " + names + ". " + proposed[0]["name"])
    update("Strategist", "working", "Ranked untested dip variants and handed them to the backtester.", detail=names, action="Proposed " + names)
    if not tokens:
        post("Backtester", "No eligible pool has enough hourly history. Variants were not tested and were not marked tried or rejected.")
        update("Backtester", "working", "No eligible hourly history this cycle.", action="No paper trades")
        return {"proposed": [v["id"] for v in proposed], "results": [], "skipped": "no eligible history"}
    results = []
    champion = MEMORY.champion()
    champion_oos = (champion or {}).get("oos")
    feed_budget = int(limits.get("feed_trades_per_cycle", 40))
    posted = 0
    team_taken = 0
    team_rejected = 0
    tokens_by_mint = {t["mint"]: t for t in tokens}
    x_status = (MARKET.source_status or {}).get("x_twitter") or {}
    goal_low, goal_high, notional = goal_settings(config)
    window = oos_window_seconds(tokens, paper)
    for variant in proposed:
        update("Backtester", "working", f"Simulating {variant['id']} on {len(tokens)} eligible pools.", action=f"Simulating {variant['id']}")
        trades = []
        for token in tokens:
            trades.extend(simulate(token["bars"], variant, token, paper, seed_ath=token.get("seed_ath")))
        # Variant scoring uses every simulated fill. The shared team ledger
        # only records fills the six agents approved by vote.
        ins, oos = split_samples(trades)
        ins_m = metrics(ins)
        oos_m = metrics(oos)
        mode = mode_for(config)
        if mode != "legacy:backtest":
            for trade in trades:
                trade["mode"] = mode
                trade["id"] = mode + ":" + trade["id"]
        known = MEMORY.known_trade_ids()
        unseen = [t for t in trades if t["id"] not in known]
        update("Risk Manager", "working", f"Team vote on {len(unseen)} proposed paper trades from {variant['id']}.", action=f"Voting {variant['id']}")
        # Check BEFORE any team vote, then after each newly realized fill.
        # No batch of approvals can slip through a newly reached profit stop.
        daily = daily_stop_status(config)
        if config.get("daily_stop_enabled", False):
            fresh, vetoed = [], []
            economic = set()
            for path in MEMORY.ledger_dir.glob("????-??-??.json"):
                for t in json.loads(path.read_text()).get("trades", []):
                    if t.get("mode", "legacy:backtest") == mode:
                        economic.add(fill_key(t))
            def entry_guard(trade):
                daily = daily_stop_status(config)
                closed = close_time(trade)
                if not closed or closed.timestamp() > time.time() or fill_key(trade) in economic:
                    return False
                if daily["halted"]:
                    post("Risk Manager", "DAILY PROFIT HALT: blocked a new paper entry before team vote; resumes at ET midnight.", publish_feed=False)
                    return False
                return True

            def record_approved(trade):
                recorded = MEMORY.record_trades([trade])
                fresh.extend(recorded)
                economic.update(fill_key(t) for t in recorded)
                daily_stop_status(config)

            approved, vetoed = review_trades(unseen, tokens_by_mint, variant, config, x_status,
                                            MEMORY.can_test(variant["id"]), entry_guard=entry_guard,
                                            on_approved=record_approved)
        else:
            approved, vetoed = review_trades(unseen, tokens_by_mint, variant, config, x_status, MEMORY.can_test(variant["id"]))
            fresh = MEMORY.record_trades(approved)
        MEMORY.learn_from_losses(fresh)
        team_taken += len(fresh)
        team_rejected += len(vetoed)
        for trade in fresh:
            if posted >= feed_budget:
                break
            team = trade.get("team") or {}
            text = (
                f"PAPER / SIMULATED {trade['symbol']} ({trade['name']}) proposed by {trade.get('proposed_by')}, "
                f"team {team.get('tally')} ({team.get('rule')}). "
                f"entry {trade['entry_time']} @ {trade['entry_price']} "
                f"exit {trade['exit_time']} @ {trade['exit_price']} "
                f"P&L ${trade['pnl_usd']:.2f}. {trade['dex_url']} {trade['gmgn_url']}"
            )
            post(trade.get("proposed_by") or "Backtester", text, "trade", trade)
            posted += 1
        if len(fresh) > posted:
            post("Backtester", f"{len(fresh) - max(posted, 0)} more team-approved paper trades from {variant['id']} are in the daily ledger and were not each repeated on the feed.")
        if vetoed:
            why = {}
            for t in vetoed:
                r = (t.get("team") or {}).get("rule") or "rejected"
                why[r] = why.get(r, 0) + 1
            sample = vetoed[0]
            no_votes = [v for v in (sample.get("team") or {}).get("votes", []) if v["vote"] == "reject"]
            reason = f" e.g. {sample['symbol']}: {no_votes[0]['agent']} — {no_votes[0]['reason']}" if no_votes else ""
            post("Risk Manager", f"Team turned down {len(vetoed)} proposed {variant['id']} paper trades ({'; '.join(f'{k}: {n}' for k, n in why.items())}).{reason}")
        min_oos = int(paper.get("min_oos_trades", 5))
        projection = goal_projection(oos_m, window, notional, goal_low, goal_high)
        if oos_m["trades"] < min_oos:
            status = "deferred"
            reason = f"only {oos_m['trades']} out-of-sample paper trades (need {min_oos}); not rejected"
        elif oos_m["expectancy_usd"] is None or oos_m["expectancy_usd"] <= 0:
            status = "rejected"
            reason = f"out-of-sample expectancy ${oos_m['expectancy_usd']} over {oos_m['trades']} trades"
        elif beats_goal(oos_m, projection, champion, min_oos):
            status = "champion"
            reason = f"out-of-sample expectancy ${oos_m['expectancy_usd']} over {oos_m['trades']} trades projects ${projection['monthly_usd']}/mo at ${notional:.0f} tickets, beating the previous champion toward the ${goal_low:,.0f}–${goal_high:,.0f}/mo goal"
        else:
            status = "tried"
            reason = f"out-of-sample expectancy ${oos_m['expectancy_usd']} projects ${projection['monthly_usd']}/mo at ${notional:.0f} tickets and did not beat the champion"
        pools = [{"symbol": t.get("symbol"), "mint": t.get("mint"), "pool": t.get("pool")} for t in tokens]
        record = {
            "id": variant["id"],
            "status": status,
            "reason": reason,
            "name": variant["name"],
            "params": {k: variant[k] for k in ("zone_low", "zone_high", "stop", "target", "hold_bars")},
            "oos": oos_m,
            "ins": ins_m,
            "goal": projection,
            "pools": pools,
            "attempts": 1,
        }
        MEMORY.record_variant(record)
        if status == "champion":
            MEMORY.write_champion_md(variant, oos_m, pools)
            champion_oos = oos_m
            champion = MEMORY.champion()
            post("Strategist", f"BEST_STRATEGY.md replaced by {variant['id']}. {reason}")
        elif status == "rejected":
            post("Strategist", f"Rejected {variant['id']}: {reason}. It will not be retested.", "error")
        else:
            post("Strategist", f"{variant['id']} is {status}: {reason}")
        post("Backtester", f"{variant['id']}: {len(fresh)} team-approved paper trades ({len(vetoed)} turned down), {oos_m['trades']} out of sample, net ${oos_m['net_usd']}.")
        results.append({"id": variant["id"], "status": status, "reason": reason, "oos": oos_m, "in_sample": ins_m, "goal": projection, "new_trades": len(fresh), "team_rejected": len(vetoed)})
        log(f"variant {variant['id']} {status} trades {len(fresh)}")
    return {"proposed": [v["id"] for v in proposed], "results": results, "team_taken": team_taken, "team_rejected": team_rejected}


def goal_settings(config):
    low = float(config.get("monthly_goal_low", 3000))
    high = float(config.get("monthly_goal_high", 5000))
    notional = float((config.get("paper") or {}).get("notional_usd", 100))
    return low, high, notional


def goal_status(config, variant_report):
    """Goal progress across this cycle's candidates and the champion. Only versions that pass the OOS gates count."""
    low, high, notional = goal_settings(config)
    min_oos = int((config.get("paper") or {}).get("min_oos_trades", 5))
    rows = []
    for r in variant_report.get("results") or []:
        g = r.get("goal") or {}
        rows.append({"id": r["id"], "role": "candidate", "status": r.get("status"), **g})
    champ = MEMORY.champion()
    if champ:
        g = champ.get("goal") or {}
        rows.append({"id": champ["id"], "role": "champion", "status": "champion", **g,
                     "oos_trades": (champ.get("oos") or {}).get("trades"), "expectancy_usd": (champ.get("oos") or {}).get("expectancy_usd")})
    for row in rows:
        exp = row.get("expectancy_usd")
        row["qualifies"] = bool(row.get("status") != "rejected" and (row.get("oos_trades") or 0) >= min_oos and exp is not None and exp > 0)
    ranked = sorted([r for r in rows if r["qualifies"] and r.get("monthly_usd") is not None], key=lambda r: r["monthly_usd"], reverse=True)
    best = ranked[0] if ranked else None
    label = f"Goal ${low/1000:g}k–{high/1000:g}k/mo"
    if best:
        line = (f"{label}: best qualifying version {best['id']} ({best['role']}) projects ${best['monthly_usd']:,.2f}/mo at ${notional:.0f} tickets "
                f"({best['trades_per_month']} trades/mo × ${best['expectancy_usd']}/trade OOS); needs ~${best['ticket_for_low_usd']:,.0f}–${best['ticket_for_high_usd']:,.0f} tickets. "
                "Paper projection only; bigger tickets would slip more than modeled.")
        pct = round(best["monthly_usd"] / low * 100, 2) if low else None
    else:
        legacy = champ and not (champ.get("goal") or {}).get("monthly_usd") and (champ.get("oos") or {}).get("expectancy_usd")
        line = (f"{label}: no version qualifies with a monthly projection this cycle (need ≥{min_oos} out-of-sample trades and a positive average). "
                + "".join(f"{r['id']} projects ${r['monthly_usd']:,.2f}/mo ({r['status']}, {r.get('oos_trades')} OOS trades). " for r in rows if r["role"] == "candidate" and r.get("monthly_usd") is not None)
                + (f"Champion {champ['id']} predates the goal and has no measured trade frequency yet. " if legacy else "")
                + "Not loosening the out-of-sample rule to chase the goal.")
        pct = None
    return {
        "monthly_goal_low_usd": low,
        "monthly_goal_high_usd": high,
        "notional_usd": notional,
        "best": best,
        "progress_pct_of_low": pct,
        "candidates": rows,
        "status_line": line,
        "method": "Projected monthly P&L = out-of-sample average $ per trade × out-of-sample trades per month (pooled OOS trade count ÷ the OOS window length × 30.44 days). Ticket needed = $100 × goal ÷ projected monthly. Promotion requires ≥5 OOS trades, a positive average, and a variant that is not rejected; among those, the higher projected monthly P&L wins.",
    }


def public_token(cand):
    safety = cand.get("safety") or None
    if safety:
        safety = {
            "status": safety.get("status"),
            "summary": safety.get("summary"),
            "hard_fails": safety.get("hard_fails") or [],
            "warnings": safety.get("warnings") or [],
            "checks": safety.get("checks") or [],
            "top_human_pct": safety.get("top_human_pct"),
            "top_human": safety.get("top_human"),
            "mint_authority_active": safety.get("mint_authority_active"),
            "freeze_authority_active": safety.get("freeze_authority_active"),
            "risky_extensions": safety.get("risky_extensions") or [],
            "token2022": safety.get("token2022"),
            "lp_matched": safety.get("lp_matched"),
            "lp_locked": safety.get("lp_locked"),
            "lp_burned": safety.get("lp_burned"),
            "program_hold_pct": safety.get("program_hold_pct"),
            "supply_burn_pct": safety.get("supply_burn_pct"),
            "holder_over_3_5": safety.get("holder_over_3_5"),
            "cluster": safety.get("cluster"),
            "extensions": safety.get("extensions") or [],
            "humans": safety.get("humans") or [],
        }
    keys = [
        "mint", "symbol", "name", "pool", "dex", "quote_symbol", "price_usd", "last_price",
        "liquidity_usd", "volume_24h_usd", "market_cap_usd", "market_cap_from", "liq_to_mcap",
        "age_hours", "metrics_source", "twitter", "dex_url", "gmgn_url", "bubble_url",
        "eligible", "lesson_blocks", "filter_reason", "in_entry_zone", "ath_frac", "window_ath",
        "ath_note", "hourly_bars", "daily_bars", "history_error", "description",
        "global_fees_sol", "global_fees_basis", "fees_proxy_sol", "fees_proxy_basis", "fee_filter_basis",
    ]
    out = {k: cand.get(k) for k in keys}
    out["safety"] = safety
    return out


def rank_watchlist(reviewed):
    eligible = [c for c in reviewed if c.get("eligible")]
    failed = [c for c in reviewed if not c.get("eligible")]

    def key(c):
        top = ((c.get("safety") or {}).get("top_human_pct")) or 0
        return (1 if c.get("in_entry_zone") else 0, -top, c.get("liquidity_usd") or 0)

    eligible.sort(key=key, reverse=True)
    return eligible, failed


def cycle(config):
    started = time.monotonic()
    if config.get("rpc_resilience_enabled", False):
        MARKET.rpc = ResilientRpcClient(config.get("rpc_urls") or [], config.get("rpc_min_interval_seconds", 1.25), (config.get("limits") or {}).get("rpc_budget", 64))
    daily_stop_status(config, announce=True)
    STATE["errors"] = []
    STATE["cycle_count"] = int(STATE.get("cycle_count") or 0) + 1
    log(f"cycle {STATE['cycle_count']} start")
    banner = lessons_banner()
    for name in ROLE_NAMES:
        update(name, "working", banner, action="Read lessons")
    post("System", f"Cycle {STATE['cycle_count']} started. {banner} {DISCLAIMER}")
    queue, found = discover(config)
    passed, rejected, counts = screen(queue, config)
    update(
        "Data Scout",
        "working",
        f"Scanned {found.get('discovered', 0)} mints, enriched {found.get('enriched', 0)}, {len(passed)} passed liquidity, volume, age, and market-cap filters.",
        detail=json.dumps(counts)[:180],
        action=f"{len(passed)} passed filters",
    )
    post("Data Scout", f"{found.get('discovered', 0)} mints discovered, {found.get('enriched', 0)} enriched, {len(passed)} passed filters, {found.get('skipped_rejected', 0)} skipped because a lesson already rejected the mint. Reject reasons: {counts or 'none'}.")
    zone = config.get("entry_zone") or {}
    post("Data Scout", f"Preferred entry zone remains {int(zone.get('min_frac_of_ath', 0.2)*100)}–{int(zone.get('max_frac_of_ath', 0.45)*100)}% of the window ATH ({int((1-zone.get('max_frac_of_ath', 0.45))*100)}–{int((1-zone.get('min_frac_of_ath', 0.2))*100)}% off). That zone is the buy rule, not a reason to invent pairs.")
    reviewed = review_candidates(passed, config)
    eligible = [c for c in reviewed if c.get("eligible")]
    limits = config.get("limits") or {}
    histories = []
    for cand in eligible[: int(limits.get("ohlcv_tokens", 3))]:
        label = cand.get("symbol") or cand["mint"][:6]
        update("Backtester", "working", f"Fetching free GeckoTerminal OHLCV for {label}.", action=f"OHLCV {label}")
        ok = load_history(cand, config)
        if ok:
            histories.append(cand)
            frac = cand.get("ath_frac")
            post("Data Scout", f"{label} window ATH fraction now is {None if frac is None else round(frac, 3)} ({'inside' if cand.get('in_entry_zone') else 'outside'} the 20–45% zone).")
        else:
            post("Backtester", f"{label} does not have enough hourly bars ({cand.get('hourly_bars') or 0}). {cand.get('history_error') or ''}", "error")
    variant_report = run_variants(histories, config)
    STATE["goal"] = goal_status(config, variant_report)
    post("Strategist", STATE["goal"]["status_line"])
    MEMORY.write_champion_md_current(STATE["goal"])
    ranked, failed = rank_watchlist(reviewed)
    STATE["watchlist"] = [public_token(c) for c in ranked]
    STATE["rejected_review"] = [public_token(c) for c in failed]
    STATE["filter_rejects_sample"] = [public_token(c) for c in rejected[:8]]
    champ = MEMORY.champion()
    if champ:
        STATE["best"] = {
            "id": champ["id"],
            "name": champ.get("name"),
            "oos": champ.get("oos"),
            "status": "champion",
            "principle": "Buy dips. Never top-tick.",
        }
        STATE["strategist_note"] = f"Living champion {champ['id']}. {champ.get('reason') or ''} {champ.get('name') or ''}"
    else:
        STATE["best"] = {"id": None, "name": describe_variant(0.2, 0.45, 0.12, 0.25, 16), "oos": None, "status": "none", "principle": "Buy dips. Never top-tick."}
        STATE["strategist_note"] = "No out-of-sample champion yet. BEST_STRATEGY.md stays on the standing dip rule until a variant beats it on the latest 30% of each pool."
    fails = [c for c in reviewed if (c.get("safety") or {}).get("status") == "fail"]
    incomplete = [c for c in reviewed if (c.get("safety") or {}).get("status") == "incomplete"]
    STATE["risk_note"] = (
        f"Reviewed {len(reviewed)} tokens. Safety fails {len(fails)}. Incomplete {len(incomplete)}. Eligible {len(ranked)}. "
        "LP lock or burn is reported only when it is visible on the largest accounts. Creator wallets are not labeled by the free mint account."
    )
    update("Risk Manager", "idle", STATE["risk_note"], action=AGENTS["Risk Manager"].get("latest_action") or "Review finished")
    bub_fails = sum(1 for c in reviewed if (c.get("safety") or {}).get("holder_over_3_5") or (c.get("safety") or {}).get("cluster_fail"))
    update("Bubble Map Analyst", "idle", f"{bub_fails} concentration or cluster fails this cycle. Links are https://app.bubblemaps.io/sol/token/<mint>.", action=AGENTS["Bubble Map Analyst"].get("latest_action") or "Holder pass")
    ledger = MEMORY.index
    recent = MEMORY.recent_trades(12)
    STATE["recent_trades"] = recent
    STATE["ledger"] = {k: ledger.get(k) for k in ("timezone", "label", "updated", "total_pnl_usd", "trade_count", "days")}
    STATE["lessons_preview"] = {
        "rules": MEMORY.data.get("rules") or [],
        "observations": list(reversed(MEMORY.data.get("observations") or []))[:12],
        "variants": MEMORY.data.get("variants") or [],
        "rejected_mints": (MEMORY.data.get("rejected_mints") or [])[-12:],
    }
    STATE["summary"] = {
        "discovered": found.get("discovered", 0),
        "enriched": found.get("enriched", 0),
        "passed_filters": len(passed),
        "reviewed": len(reviewed),
        "eligible": len(ranked),
        "paper_trades_total": ledger.get("trade_count") or 0,
        "paper_pnl_usd": ledger.get("total_pnl_usd") or 0,
        "new_paper_trades": sum(r.get("new_trades") or 0 for r in variant_report.get("results") or []),
    }
    STATE["summary"]["team_rejected"] = variant_report.get("team_rejected") or 0
    STATE["team"] = {
        "model": "One team, one shared paper P&L. Each trade is proposed by one agent; all six vote. Majority of voting agents approves; a Risk Manager or Bubble Map Analyst reject is a veto. X/Twitter Scout abstains while the X API is unavailable.",
        "members": ROLE_NAMES,
        "veto": ["Risk Manager", "Bubble Map Analyst"],
        "team_pnl_usd": ledger.get("total_pnl_usd") or 0,
        "team_trades": ledger.get("trade_count") or 0,
        "last_cycle_taken": variant_report.get("team_taken") or 0,
        "last_cycle_rejected": variant_report.get("team_rejected") or 0,
    }
    STATE["sources"] = MARKET.source_status
    STATE["sources"]["solana_rpc"] = {
        "ok": not MARKET.rpc.disabled and not (MARKET.rpc.errors and not MARKET.rpc.used),
        "calls": MARKET.rpc.calls,
        "endpoints": MARKET.rpc.used,
        "errors": MARKET.rpc.errors[-5:],
        "detail": "public RPC only, no key",
    }
    if found.get("gecko") and not found.get("gecko_errors"):
        STATE["sources"]["geckoterminal"] = {"ok": True, "detail": found["gecko"]}
    else:
        STATE["sources"]["geckoterminal"] = {"ok": bool(found.get("gecko")), "detail": found.get("gecko"), "errors": found.get("gecko_errors")}
    STATE["report"] = {
        "discovered": found,
        "filter_counts": counts,
        "passed_filters": len(passed),
        "reviewed": len(reviewed),
        "eligible": len(ranked),
        "histories": len(histories),
        "variants": variant_report,
        "safety_fail": len(fails),
        "safety_incomplete": len(incomplete),
        "holder_or_cluster_fails": bub_fails,
        "x_linked": found.get("x_linked", 0),
        "rpc_calls": MARKET.rpc.calls,
        "new_paper_trades": STATE["summary"]["new_paper_trades"],
        "ledger_trades": STATE["summary"]["paper_trades_total"],
        "ledger_pnl_usd": STATE["summary"]["paper_pnl_usd"],
    }
    any_source = bool(found.get("discovered")) or bool(MARKET.source_status.get("dexscreener_lists", {}).get("ok"))
    STATE["ok"] = bool(any_source)
    STATE["data_status"] = (
        f"{found.get('discovered', 0)} mints · {len(passed)} passed filters · {len(ranked)} eligible · "
        f"{STATE['summary']['new_paper_trades']} new paper trades"
    )
    STATE["cycle_duration_seconds"] = round(time.monotonic() - started, 3)
    daily_stop_status(config)
    STATE["last_cycle"] = now_iso()
    STATE["next_cycle"] = datetime.fromtimestamp(time.time() + int(config.get("cycle_seconds", 1800)), timezone.utc).isoformat()
    update("Strategist", "idle", STATE["strategist_note"], action=AGENTS["Strategist"].get("latest_action") or "No champion change")
    update("Data Scout", "idle", STATE["data_status"], action=AGENTS["Data Scout"].get("latest_action") or "Scan complete")
    update("Backtester", "idle", f"Ledger {ledger.get('trade_count') or 0} paper trades, net ${ledger.get('total_pnl_usd') or 0}.", action=AGENTS["Backtester"].get("latest_action") or "Ledger updated")
    update("X/Twitter Scout", "idle", MARKET.source_status.get("x_twitter", {}).get("detail") or "X API not reachable", action=AGENTS["X/Twitter Scout"].get("latest_action") or "No tweets invented")
    post("System", f"Cycle {STATE['cycle_count']} finished. {STATE['data_status']}.")
    save_state()
    maybe_publish_full(force=True)
    log("cycle done " + STATE["data_status"])
    return STATE


def light_scan(config):
    if config.get("candidate_source", "legacy") != "legacy":
        rows, report = source_candidates(MARKET, config)
        post("Data Scout", f"Light scan: {report['label']}, {len(rows)} rows; no entries or safety passes on a light scan.")
        return
    seen_path = ROOT / "data" / "cache" / "seen_mints.json"
    try:
        seen = set(json.loads(seen_path.read_text()))
    except Exception:
        seen = set()
    update("X/Twitter Scout", "working", "Light scan of DexScreener boost and profile links.", action="Light scan")
    update("Data Scout", "working", "Light scan of new GeckoTerminal pools. No safety review on this pass.", action="Light scan")
    try:
        lists, errors = MARKET.dexscreener_lists()
        for err in errors:
            note_error("X/Twitter Scout", "Light scan DexScreener list failed: " + err)
        fresh_links = []
        for row in lists:
            mint = row.get("mint")
            if not mint or mint in seen:
                continue
            seen.add(mint)
            if row.get("twitter"):
                fresh_links.append(row)
        if fresh_links:
            bits = [f"{(r.get('mint') or '')[:6]} {r['twitter'][0]}" for r in fresh_links[:5]]
            post("X/Twitter Scout", f"Light scan found {len(fresh_links)} new Solana rows with an X link. Not tweets. " + "; ".join(bits))
    except Exception as exc:
        note_error("X/Twitter Scout", f"Light scan failed: {exc}")
    try:
        pools = MARKET.gecko_pools("new_pools")
        novel = [p for p in pools if p.get("mint") and p["mint"] not in seen]
        for row in novel:
            seen.add(row["mint"])
        if novel:
            above = [p for p in novel if (p.get("liquidity_usd") or 0) >= float(config["filters"]["min_liquidity_usd"])]
            post("Data Scout", f"Light scan: {len(novel)} new pools, {len(above)} already at the liquidity filter. No paper trades on a light scan.")
    except SourceError as exc:
        note_error("Data Scout", f"Light scan GeckoTerminal new pools failed: {exc}")
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = seen_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sorted(seen)[-3000:]))
    tmp.replace(seen_path)
    update("X/Twitter Scout", "idle", AGENTS["X/Twitter Scout"].get("task") or "Light scan idle", action=AGENTS["X/Twitter Scout"].get("latest_action"))
    update("Data Scout", "idle", AGENTS["Data Scout"].get("task") or "Light scan idle", action=AGENTS["Data Scout"].get("latest_action"))


def health(config, allow_publish=True):
    limit = float(config.get("stale_agent_seconds", 1200))
    stale = [role for role, ts in HEARTS.items() if time.time() - ts > limit]
    for role in ROLE_NAMES:
        HEARTS[role] = time.time()
        AGENTS[role]["heartbeat"] = now_iso()
    local_url = config.get("local_url", "http://127.0.0.1:8795").rstrip("/") + "/data/feed.json"
    public = config.get("public_url", "").rstrip("/") + "/data/feed.json"
    local_ok, local_err = _reachable(local_url)
    remote_ok, remote_err = _reachable(public) if public else (False, "no public url")
    STATE["health"] = {
        "local": local_ok,
        "local_error": None if local_ok else local_err,
        "site_reachable": remote_ok,
        "site_error": None if remote_ok else remote_err,
        "public_url": config.get("public_url"),
        "checked_at": now_iso(),
        "stale_agents": stale,
        "last_published": (STATE.get("health") or {}).get("last_published"),
    }
    if stale:
        post("System", "Stale agents before this health refresh: " + ", ".join(stale), "error", publish_feed=False)
    save_state()
    if allow_publish:
        maybe_publish_full(force=False)
    log(f"health local={local_ok} site={remote_ok} stale={stale}")


def _reachable(url):
    import urllib.request
    try:
        req = urllib.request.Request(url + "?health=" + str(int(time.time())), headers={"User-Agent": "TrenchfloorResearch/1.0"})
        with urllib.request.urlopen(req, timeout=12) as res:
            ok = 200 <= res.status < 400
            return ok, None if ok else f"HTTP {res.status}"
    except Exception as exc:
        return False, str(exc)[:200]


def cycle_due(config):
    if (ROOT / "data" / "cycle.requested").exists():
        return True
    if not STATE.get("last_cycle"):
        return True
    try:
        then = datetime.fromisoformat(STATE["last_cycle"]).timestamp()
    except ValueError:
        return True
    return time.time() - then >= float(config.get("cycle_seconds", 1800))


def main():
    global NO_PUBLISH, ROOT, emit
    parser = argparse.ArgumentParser(description="Trenchfloor paper-research loop")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    parser.add_argument("--no-publish", action="store_true", help="do not push gh-pages")
    parser.add_argument("--dry-run", action="store_true", help="one cycle on an isolated temporary copy of data; no publish")
    parser.add_argument("--candidate-source", choices=["legacy", "gmgn_substitute", "gmgn"], help="dry-run only")
    parser.add_argument("--fee-proxy", action="store_true", help="dry-run only: opt into an explicitly labeled, non-global fee proxy")
    parser.add_argument("--report-json", type=Path, help="dry-run only: destination for summary")
    args = parser.parse_args()
    NO_PUBLISH = args.no_publish or __import__("os").environ.get("TRENCHFLOOR_SKIP_PUBLISH") == "1"
    if not args.dry_run and (args.candidate_source or args.fee_proxy or args.report_json):
        parser.error("source/proxy/report overrides require --dry-run")
    config = load_config()
    sandbox = None
    if args.dry_run:
        # Isolate telemetry as well as disk state. Dry cycles are not live floor
        # activity and must not be sent to the separate local event service.
        import team
        emit = lambda *a, **k: None
        team.emit = emit
        try:
            import events
            events.emit = emit
        except ModuleNotFoundError:
            pass
        import tempfile, shutil
        sandbox = tempfile.TemporaryDirectory(prefix="trenchfloor-dry-")
        previous_root = ROOT
        ROOT = Path(sandbox.name)
        shutil.copytree(previous_root / "data", ROOT / "data")
        config.update(candidate_source=args.candidate_source or "gmgn_substitute", daily_stop_enabled=True, rpc_resilience_enabled=True, fee_proxy_enabled=args.fee_proxy)
        (ROOT / "config.json").write_text(json.dumps(config))
        NO_PUBLISH = True
    boot(config)
    if args.once or args.dry_run:
        try:
            cycle(config)
        except Exception as exc:
            note_error("System", f"Cycle crashed: {exc}")
            log(traceback.format_exc())
            STATE["ok"] = False
            save_state()
        if args.dry_run:
            report = {"dry_run": True, "config": {k: config[k] for k in ("candidate_source", "daily_stop_enabled", "fee_proxy_enabled", "rpc_resilience_enabled")}, "cycle_duration_seconds": STATE.get("cycle_duration_seconds"), "daily_stop": STATE.get("daily_stop"), "report": STATE.get("report"), "errors": STATE.get("errors")}
            if args.report_json:
                args.report_json.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
            sandbox.cleanup()
            return 0 if STATE.get("ok") else 1
        health(config, allow_publish=False)
        (ROOT / "data" / "cycle.requested").unlink(missing_ok=True)
        print(json.dumps(STATE.get("report") or {}, indent=2), flush=True)
        return 0 if STATE.get("ok") else 1
    next_health = time.time() + 15
    next_light = time.time() + float(config.get("light_scan_seconds", 300))
    while True:
        config = load_config()
        try:
            if cycle_due(config):
                (ROOT / "data" / "cycle.requested").unlink(missing_ok=True)
                cycle(config)
                next_light = time.time() + float(config.get("light_scan_seconds", 300))
            elif time.time() >= next_light:
                light_scan(config)
                next_light = time.time() + float(config.get("light_scan_seconds", 300))
            if time.time() >= next_health:
                health(config, allow_publish=True)
                next_health = time.time() + float(config.get("health_seconds", 180))
            maybe_publish_feed()
        except Exception as exc:
            note_error("System", f"Loop error: {exc}")
            log(traceback.format_exc())
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
