"""Post-loss review for one closed paper trade.

Re-reads the coin with the same public holder, cluster, bundle, wash, and LP
checks the entry gates already use. Recorded entry and exit prices, liquidity,
and volume are reported as stored. A missing read is retried, then written as
the check that failed and why. The review never invents a measurement and
never comes back as an empty string. It does not change entry gates or config.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from entry_gates import _fresh_rows, _settings, assess_entry_gates
from sources import num

CHECK_NAMES = (
    "holder_distribution",
    "fresh_wallet_cluster",
    "linked_wallet_cluster",
    "bundle_sniper_share",
    "dev_creator",
    "liquidity",
    "volume_profile",
    "price_mcap_path",
    "on_chain_anomalies",
)

# Same deterioration line the recorded-facts review already uses. Not a new gate.
_DROP_LIMIT = 0.80


def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _fmt_px(value):
    number = _finite(value)
    if number is None:
        return None
    return f"{number:.8g}"


def _fmt_usd(value):
    number = _finite(value)
    if number is None:
        return None
    return f"${number:,.2f}"


def _fmt_pct(value):
    number = _finite(value)
    if number is None:
        return None
    return f"{number:.2f}%"


def _change_pct(before, after):
    start, end = _finite(before), _finite(after)
    if start is None or end is None or start == 0:
        return None
    return (end / start - 1.0) * 100.0


def _extra_warnings(chain):
    extras = []
    for warning in (chain or {}).get("warnings") or []:
        text = str(warning)
        if "LP vault was not matched" in text or "not proof the LP token was burned" in text:
            continue
        extras.append(text)
    return extras


def _clip(text, limit=420):
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _has_digit(text):
    return any(ch.isdigit() for ch in str(text or ""))


def _with_number(detail, trade):
    detail = _clip(detail)
    if _has_digit(detail):
        return detail
    price = _fmt_px(trade.get("exit_price"))
    pnl = _finite(trade.get("pnl_usd"))
    if price is not None:
        return _clip(f"{detail} Recorded exit price {price}.")
    if pnl is not None:
        return _clip(f"{detail} Recorded P&L ${pnl:.2f}.")
    return detail or "no detail was recorded"


def review_is_complete(doc):
    """A written review: non-empty analysis, an improve-entries line, and every check."""
    if not isinstance(doc, dict):
        return False
    text = doc.get("text")
    improve = doc.get("improve_entries")
    checks = doc.get("checks")
    if not isinstance(text, str) or not text.strip():
        return False
    if not isinstance(improve, str) or not improve.strip():
        return False
    if not isinstance(checks, list):
        return False
    by_name = {}
    for check in checks:
        if isinstance(check, dict) and check.get("name"):
            by_name[check["name"]] = check
    if any(name not in by_name for name in CHECK_NAMES):
        return False
    for name in CHECK_NAMES:
        check = by_name[name]
        if check.get("result") not in ("flag", "clean", "failed"):
            return False
        if not str(check.get("detail") or "").strip():
            return False
    factors = doc.get("factors") if isinstance(doc.get("factors"), list) else None
    if factors is None:
        return False
    flagged = [name for name in CHECK_NAMES if by_name[name].get("result") == "flag"]
    named = {factor.get("check") for factor in factors if isinstance(factor, dict)}
    if any(name not in named for name in flagged):
        return False
    if flagged and not any(str(factor.get("text") or "").strip() for factor in factors if isinstance(factor, dict)):
        return False
    if not flagged and any(by_name[name].get("result") not in ("clean", "failed") for name in CHECK_NAMES):
        return False
    return True


def failed_review(trade, reason, attempts=2):
    """Every check failed, with the reason. Still a written review."""
    trade = trade or {}
    reason = _clip(reason or "no error text was returned")
    detail = f"failed after {max(1, int(attempts))} attempts: {reason}"
    checks = [{"name": name, "result": "failed", "detail": detail} for name in CHECK_NAMES]
    improve = "Improve entries: " + ", ".join(CHECK_NAMES) + f" failed after retry ({reason}). No entry filter is added from unread data."
    text = _render(trade, checks, [], improve)
    return _document(trade, checks, [], improve, text, attempts)


def _document(trade, checks, factors, improve, text, attempts):
    pnl = _finite(trade.get("pnl_usd"))
    return {
        "version": 1,
        "trade_id": trade.get("id"),
        "mint": trade.get("mint"),
        "symbol": trade.get("symbol"),
        "pnl_usd": pnl,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "attempts": int(attempts or 1),
        "factors": factors,
        "checks": checks,
        "improve_entries": improve,
        "text": text,
    }


def _render(trade, checks, factors, improve):
    pnl = _finite(trade.get("pnl_usd"))
    pnl_text = f"${pnl:.2f}" if pnl is not None else "P&L not recorded"
    symbol = trade.get("symbol") or "?"
    reason = trade.get("exit_reason") if isinstance(trade.get("exit_reason"), str) and trade.get("exit_reason") else "not recorded"
    lines = [f"POST-LOSS REVIEW / {symbol} / {pnl_text} / exit {reason}."]
    if factors:
        lines.append("Contributing factors:")
        for factor in factors:
            lines.append("- " + str(factor.get("text") or "").strip())
    else:
        lines.append("Contributing factors: none. Every check is listed with its result.")
    lines.append("Checks:")
    for check in checks:
        lines.append(f"- {check['name']}: {str(check['result']).upper()} {check['detail']}")
    lines.append(improve)
    return "\n".join(lines)


def _read_pair(market, mint, pool):
    if market is None or not hasattr(market, "dexscreener_pairs"):
        return None, "pair read was not attempted: market client has no dexscreener_pairs"
    try:
        rows, errors = market.dexscreener_pairs([mint] if mint else [])
    except Exception as exc:
        return None, str(exc)
    match = None
    for row in rows or []:
        if isinstance(row, dict) and pool and row.get("pool") == pool:
            match = row
            break
    if match is None:
        for row in rows or []:
            if isinstance(row, dict) and mint and row.get("mint") == mint:
                match = row
                break
    if match is None:
        if errors:
            return None, "; ".join(str(err) for err in errors)
        return None, "pair read returned no row for this mint"
    return match, None


def _gather(trade, market, config, review_token_fn, gather_fn, now):
    mint = trade.get("mint")
    pool = trade.get("pool")
    chain, chain_error = {}, None
    try:
        chain = review_token_fn(
            getattr(market, "rpc", None),
            mint,
            trade.get("exit_liquidity_usd"),
            20,
            require_complete=True,
            excluded_owners={pool} if pool else set(),
            aggregate_holders=True,
            conservative_tail=False,
        ) or {}
        if not isinstance(chain, dict):
            chain_error = "holder review did not return an object"
            chain = {}
    except Exception as exc:
        chain_error = str(exc)
        chain = {}
    evidence, evidence_error = {}, None
    candidate = {
        "mint": mint,
        "pool": pool,
        "created_ts": trade.get("created_ts"),
        "is_wash_trading": trade.get("is_wash_trading") is True,
    }
    try:
        evidence = gather_fn(candidate, market, chain, config, now=now) or {}
        if not isinstance(evidence, dict):
            evidence_error = "entry evidence did not return an object"
            evidence = {}
    except Exception as exc:
        evidence_error = str(exc)
        evidence = {}
    if chain_error:
        evidence.setdefault("holder_read_error", chain_error)
        evidence["holder_read_ok"] = False
    if evidence_error:
        evidence["holder_read_ok"] = False
        evidence["holder_read_error"] = evidence.get("holder_read_error") or evidence_error
        evidence["trade_read_ok"] = False
        evidence["trade_read_error"] = evidence.get("trade_read_error") or evidence_error
        evidence["creator_detail"] = evidence.get("creator_detail") or evidence_error
        evidence["lp_detail"] = evidence.get("lp_detail") or evidence_error
    pair, pair_error = _read_pair(market, mint, pool)
    return {
        "chain": chain,
        "evidence": evidence,
        "pair": pair,
        "pair_error": pair_error,
        "chain_error": chain_error,
        "evidence_error": evidence_error,
    }


def _sources_failed(ctx):
    evidence = ctx.get("evidence") or {}
    chain = ctx.get("chain") or {}
    if ctx.get("chain_error") or ctx.get("evidence_error") or ctx.get("pair_error"):
        return True
    if evidence.get("holder_read_ok") is not True or evidence.get("trade_read_ok") is not True:
        return True
    if evidence.get("lp_visible") is not True and evidence.get("lp_burned_or_locked") is None:
        return True
    if chain.get("status") == "incomplete":
        return True
    if _finite(chain.get("top_human_pct")) is None and _finite(evidence.get("top10_ex_pool_burn_pct")) is None:
        return True
    if not evidence.get("creator") and not evidence.get("coin_creator"):
        return True
    return False


def _fail_detail(reason, attempts):
    return _clip(f"failed after {max(1, int(attempts))} attempts: {reason or 'no error text was returned'}")


def _add(checks, factors, trade, name, result, detail):
    detail = _with_number(detail, trade)
    if result not in ("flag", "clean", "failed"):
        result = "failed"
    checks.append({"name": name, "result": result, "detail": detail})
    if result == "flag":
        factors.append({"check": name, "text": detail})


def _holder_cap(config):
    tiers = config.get("tiers") if isinstance(config, dict) else None
    primary = tiers.get("primary") if isinstance(tiers, dict) else None
    if isinstance(primary, dict):
        return _finite(primary.get("max_holder_pct"))
    return None


def _linked_groups(holders, settings):
    by_funder = {}
    for row in holders or []:
        if row.get("funder_known") is not True:
            continue
        for funder in row.get("funders") or []:
            by_funder.setdefault(funder, []).append(row)
    groups = []
    for funder, rows in by_funder.items():
        seen, pct = [], 0.0
        for row in rows:
            if row.get("owner") in seen:
                continue
            seen.append(row.get("owner"))
            pct += float(row.get("pct") or 0)
        groups.append((funder, seen, pct))
    groups.sort(key=lambda item: item[2], reverse=True)
    fail = None
    for funder, seen, pct in groups:
        if len(seen) >= int(settings["min_linked_wallets"]) and pct >= float(settings["max_linked_funder_pct"]):
            fail = (funder, seen, pct)
            break
    return groups, fail


def _bundle(holders, settings):
    slot_rows = [row for row in holders or [] if row.get("acquire_known") is True and row.get("acquire_slot") is not None]
    by_slot = {}
    for row in slot_rows:
        by_slot.setdefault(row["acquire_slot"], []).append(row)
    for slot, rows in by_slot.items():
        owners = []
        for row in rows:
            if row.get("owner") not in owners:
                owners.append(row.get("owner"))
        if len(owners) >= int(settings["same_slot_min_wallets"]):
            return ("bundle", slot, owners, sum(float(row.get("pct") or 0) for row in rows), slot_rows)
    if slot_rows:
        first = min(row["acquire_slot"] for row in slot_rows)
        window = int(settings["sniper_slot_window"])
        early = [row for row in slot_rows if row["acquire_slot"] <= first + window]
        owners = []
        for row in early:
            if row.get("owner") not in owners:
                owners.append(row.get("owner"))
        share = sum(float(row.get("pct") or 0) for row in early)
        if len(owners) >= int(settings["same_slot_min_wallets"]) and share >= float(settings["max_bundle_sniper_pct"]):
            return ("sniper", first, owners, share, slot_rows)
    return (None, None, [], 0.0, slot_rows)


def _build(trade, ctx, config, now):
    trade = trade or {}
    ctx = ctx or {}
    attempts = int(ctx.get("attempt") or 1)
    chain = ctx.get("chain") if isinstance(ctx.get("chain"), dict) else {}
    evidence = ctx.get("evidence") if isinstance(ctx.get("evidence"), dict) else {}
    settings = _settings(config)
    now = _finite(ctx.get("now")) or now or time.time()
    checks, factors = [], []
    holders = evidence.get("holders") if isinstance(evidence.get("holders"), list) else []
    holder_ok = evidence.get("holder_read_ok") is True
    holder_error = evidence.get("holder_read_error") or ctx.get("chain_error") or "holder signature sample missing"
    top1 = _finite(chain.get("top_human_pct"))
    top10 = _finite(chain.get("top10_measured_pct"))
    if top10 is None:
        top10 = _finite(evidence.get("top10_ex_pool_burn_pct"))
    top_cap = float(settings["max_top10_pct"])
    one_cap = _holder_cap(config)
    entry_top = _finite(trade.get("top_human_pct"))

    if chain.get("status") == "incomplete" or top1 is None or top10 is None:
        partial = []
        if top1 is not None:
            partial.append(f"partial top-1 {_fmt_pct(top1)}")
        if top10 is not None:
            partial.append(f"partial top-10 {_fmt_pct(top10)}")
        extra = ("; " + ", ".join(partial)) if partial else ""
        summary = chain.get("summary") or chain.get("hard_fails") or holder_error
        _add(checks, factors, trade, "holder_distribution", "failed",
             _fail_detail(f"top-1/top-10 excluding pool and burn was not fully read: {summary}{extra}", attempts))
    else:
        bits = [f"top-1 {_fmt_pct(top1) if top1 is not None else 'not measured'}",
                f"top-10 {_fmt_pct(top10) if top10 is not None else 'not measured'}",
                "excluding pool and burn"]
        if entry_top is not None:
            bits.append(f"entry snapshot top non-LP holder {_fmt_pct(entry_top)}")
        over = []
        if top10 is not None and top10 > top_cap:
            over.append(f"top-10 {top10:.2f}% is above the existing {top_cap:g}% cap")
        if top1 is not None and one_cap is not None and top1 > one_cap:
            over.append(f"top-1 {top1:.2f}% is above the existing {one_cap:g}% single-holder cap")
        if over:
            _add(checks, factors, trade, "holder_distribution", "flag", "; ".join(bits) + ". " + "; ".join(over))
        else:
            _add(checks, factors, trade, "holder_distribution", "clean", "; ".join(bits))

    if not holder_ok:
        fresh_detail = _fail_detail(holder_error, attempts)
        _add(checks, factors, trade, "fresh_wallet_cluster", "failed", fresh_detail)
        _add(checks, factors, trade, "linked_wallet_cluster", "failed", fresh_detail)
        _add(checks, factors, trade, "bundle_sniper_share", "failed", _fail_detail(evidence.get("holder_read_error") or "acquisition slots were not read", attempts))
    else:
        fresh = _fresh_rows(holders, now, settings["fresh_wallet_seconds"])
        fresh_pct = sum(float(row.get("pct") or 0) for row in fresh)
        fresh_fail = (
            len(fresh) >= int(settings["min_fresh_wallets"])
            or (len(fresh) >= 2 and fresh_pct >= float(settings["max_fresh_cluster_pct"]))
        )
        fresh_text = (
            f"{len(fresh)} fresh wallets in {len(holders)} sampled top holders "
            f"holding {fresh_pct:.2f}% combined "
            f"(block at {int(settings['min_fresh_wallets'])} wallets, or 2+ wallets at {float(settings['max_fresh_cluster_pct']):g}%)"
        )
        _add(checks, factors, trade, "fresh_wallet_cluster", "flag" if fresh_fail else "clean", fresh_text)
        groups, linked_fail = _linked_groups(holders, settings)
        if linked_fail:
            funder, seen, pct = linked_fail
            _add(checks, factors, trade, "linked_wallet_cluster", "flag",
                 f"{len(seen)} top holders share funder {funder} and hold {pct:.2f}% (existing cap {float(settings['max_linked_funder_pct']):g}%)")
        else:
            known = sum(1 for row in holders if row.get("funder_known") is True)
            if groups:
                funder, seen, pct = groups[0]
                linked_text = f"largest shared funder {funder} has {len(seen)} wallet(s) and {pct:.2f}%; {known} holders had a known funder"
            else:
                linked_text = f"no shared funder in the sample; {known} of {len(holders)} holders had a known funder (funder reads run on complete short histories)"
            _add(checks, factors, trade, "linked_wallet_cluster", "clean", linked_text)
        kind, slot, owners, share, slot_rows = _bundle(holders, settings)
        if kind == "bundle":
            _add(checks, factors, trade, "bundle_sniper_share", "flag",
                 f"{len(owners)} top holders acquired in slot {slot} ({share:.2f}% combined); same-slot buys are a bundle")
        elif kind == "sniper":
            _add(checks, factors, trade, "bundle_sniper_share", "flag",
                 f"{len(owners)} early buyers within {int(settings['sniper_slot_window'])} slots of {slot} still hold {share:.2f}% (existing cap {float(settings['max_bundle_sniper_pct']):g}%)")
        else:
            _add(checks, factors, trade, "bundle_sniper_share", "clean",
                 f"no same-slot bundle and no sniper share at the cap in {len(slot_rows)} known acquisition slots")

    creators = [value for value in (evidence.get("creator"), evidence.get("coin_creator")) if value]
    trade_ok = evidence.get("trade_read_ok") is True and isinstance(evidence.get("trades"), list)
    trades = evidence.get("trades") if trade_ok else []
    if not creators:
        creator_reason = evidence.get("creator_detail") or ctx.get("evidence_error") or "creator wallet was not labeled by the pool read"
        _add(checks, factors, trade, "dev_creator", "failed", _fail_detail(creator_reason, attempts))
    else:
        humans = chain.get("humans") if isinstance(chain.get("humans"), list) else []
        held = [row for row in humans if row.get("owner") in creators]
        held_bits = [f"{row.get('owner')} {_fmt_pct(row.get('pct'))}" for row in held]
        holding = ", ".join(held_bits) if held_bits else "not in the top holder sample"
        sell_count, sell_amount = 0, 0.0
        if trade_ok:
            for fill in trades:
                if fill.get("signer") in creators and fill.get("side") == "sell":
                    amount = _finite(fill.get("amount"))
                    if amount is None:
                        continue
                    sell_count += 1
                    sell_amount += amount
        names = ", ".join(creators)
        if not trade_ok:
            _add(checks, factors, trade, "dev_creator", "failed",
                 _fail_detail(f"creator {names} holding {holding}; sells were not read: {evidence.get('trade_read_error') or ctx.get('evidence_error') or 'pool trade sample missing'}", attempts))
        else:
            sell_text = f"{sell_count} creator sell(s) totaling {sell_amount:.6g} tokens in {len(trades)} sampled pool fills"
            dev_text = f"creator wallets {names}; holding {holding}; {sell_text}"
            creator_pct = sum(float(row.get("pct") or 0) for row in held)
            over_cap = one_cap is not None and creator_pct > one_cap
            if sell_count or over_cap:
                if over_cap:
                    dev_text += f"; creator holding {creator_pct:.2f}% is above the existing {one_cap:g}% single-holder cap"
                _add(checks, factors, trade, "dev_creator", "flag", dev_text)
            else:
                _add(checks, factors, trade, "dev_creator", "clean", dev_text)

    gates = {check["name"]: check for check in assess_entry_gates(evidence, config, now=now)}
    lp_gate = gates.get("lp_locked_or_burned") or {}
    wash_gate = gates.get("wash_trade") or {}
    entry_liq, exit_liq = _finite(trade.get("entry_liquidity_usd")), _finite(trade.get("exit_liquidity_usd"))
    liq_change = _change_pct(entry_liq, exit_liq)
    liq_bits = []
    if entry_liq is None or exit_liq is None:
        liq_bits.append("entry/exit liquidity was not both recorded")
    else:
        liq_bits.append(f"liquidity {_fmt_usd(entry_liq)} at entry → {_fmt_usd(exit_liq)} at exit ({liq_change:.1f}%)")
    lp_state = lp_gate.get("pass")
    lp_detail = lp_gate.get("detail") or evidence.get("lp_detail") or "LP lock/burn was not read"
    liq_bits.append(f"LP {lp_detail}")
    liq_drop = liq_change is not None and liq_change < -((1.0 - _DROP_LIMIT) * 100.0)
    entry_lp_locked = None
    for saved in trade.get("hard_rug_checks") or []:
        if isinstance(saved, dict) and saved.get("name") in ("LP_locked_or_burned", "lp_locked_or_burned"):
            entry_lp_locked = saved.get("pass") is True
    if entry_lp_locked and lp_state is False:
        liq_bits.append("LP was locked or burned at entry and is not now")
    if lp_state is False or liq_drop:
        _add(checks, factors, trade, "liquidity", "flag", ". ".join(liq_bits))
    elif lp_state is None or (entry_liq is None or exit_liq is None):
        reason = lp_detail if lp_state is None else "entry/exit liquidity was not both recorded"
        if entry_liq is not None and exit_liq is not None:
            reason = f"{lp_detail}. Recorded " + liq_bits[0]
        _add(checks, factors, trade, "liquidity", "failed", _fail_detail(reason, attempts))
    else:
        _add(checks, factors, trade, "liquidity", "clean", ". ".join(liq_bits))

    entry_vol, exit_vol = _finite(trade.get("entry_volume_usd")), _finite(trade.get("exit_volume_usd"))
    vol_change = _change_pct(entry_vol, exit_vol)
    vol_bits = []
    if entry_vol is None or exit_vol is None:
        vol_bits.append("entry/exit volume was not both recorded")
    else:
        vol_bits.append(f"volume {_fmt_usd(entry_vol)} at entry → {_fmt_usd(exit_vol)} at exit ({vol_change:.1f}%)")
    wash_state = wash_gate.get("pass")
    wash_detail = wash_gate.get("detail") or evidence.get("trade_read_error") or "pool trade sample missing"
    vol_bits.append(f"wash {wash_detail}")
    vol_drop = vol_change is not None and vol_change < -((1.0 - _DROP_LIMIT) * 100.0)
    if wash_state is False or vol_drop:
        _add(checks, factors, trade, "volume_profile", "flag", ". ".join(vol_bits))
    elif wash_state is None or entry_vol is None or exit_vol is None:
        reason = wash_detail if wash_state is None else "entry/exit volume was not both recorded"
        if entry_vol is not None and exit_vol is not None:
            reason = f"{wash_detail}. Recorded " + vol_bits[0]
        _add(checks, factors, trade, "volume_profile", "failed", _fail_detail(reason, attempts))
    else:
        _add(checks, factors, trade, "volume_profile", "clean", ". ".join(vol_bits))

    entry_px, exit_px = _finite(trade.get("entry_price")), _finite(trade.get("exit_price"))
    price_change = _change_pct(entry_px, exit_px)
    pair = ctx.get("pair") if isinstance(ctx.get("pair"), dict) else None
    mcap = num(pair.get("market_cap_usd")) if pair else None
    held = None
    if _finite(trade.get("entry_ts")) is not None and _finite(trade.get("exit_ts")) is not None:
        held = (_finite(trade.get("exit_ts")) - _finite(trade.get("entry_ts"))) / 60.0
    if entry_px is None or exit_px is None:
        _add(checks, factors, trade, "price_mcap_path", "failed",
             _fail_detail("entry or exit price was not recorded; no price path was invented", attempts))
    elif ctx.get("pair_error"):
        path = f"price {_fmt_px(entry_px)} → {_fmt_px(exit_px)} ({price_change:.1f}%)"
        if held is not None:
            path += f" over {held:.1f} minutes"
        _add(checks, factors, trade, "price_mcap_path", "failed",
             _fail_detail(f"{path}. Market-cap pair read failed: {ctx.get('pair_error')}", attempts))
    else:
        path = f"price {_fmt_px(entry_px)} → {_fmt_px(exit_px)} ({price_change:.1f}%)"
        if held is not None:
            path += f" over {held:.1f} minutes"
        frac = _finite(trade.get("entry_frac_of_ath"))
        if frac is not None:
            path += f"; entry was {frac * 100:.1f}% of the recorded window ATH"
        if mcap is not None:
            path += f"; market cap at review {_fmt_usd(mcap)}"
        else:
            path += "; market cap was not in the pair payload"
        stop = _finite(trade.get("stop_fraction"))
        if stop is not None:
            path += f"; recorded stop {stop * 100:.0f}%"
        _add(checks, factors, trade, "price_mcap_path", "clean", path)

    extras = _extra_warnings(chain)
    if chain.get("mint_authority_active") is None and chain.get("freeze_authority_active") is None and not extras:
        _add(checks, factors, trade, "on_chain_anomalies", "failed",
             _fail_detail(ctx.get("chain_error") or chain.get("summary") or "mint authority and freeze authority were not read", attempts))
    else:
        anomalies = []
        if chain.get("mint_authority_active") is True:
            anomalies.append("mint authority is active")
        elif chain.get("mint_authority_active") is None:
            anomalies.append("mint authority was not read")
        if chain.get("freeze_authority_active") is True:
            anomalies.append("freeze authority is active")
        elif chain.get("freeze_authority_active") is None:
            anomalies.append("freeze authority was not read")
        anomalies.extend(extras)
        unread = [item for item in anomalies if item.endswith("was not read")]
        active = [item for item in anomalies if item not in unread]
        if active:
            known = []
            if chain.get("mint_authority_active") is False:
                known.append("mint authority is not active")
            if chain.get("freeze_authority_active") is False:
                known.append("freeze authority is not active")
            _add(checks, factors, trade, "on_chain_anomalies", "flag", "; ".join(active + known))
        elif unread:
            _add(checks, factors, trade, "on_chain_anomalies", "failed", _fail_detail("; ".join(unread), attempts))
        else:
            _add(checks, factors, trade, "on_chain_anomalies", "clean", "mint authority is not active; freeze authority is not active; no extra on-chain warning")

    present = {check["name"] for check in checks}
    for name in CHECK_NAMES:
        if name not in present:
            _add(checks, factors, trade, name, "failed", _fail_detail("check did not run", attempts))
    ordered = []
    by_name = {check["name"]: check for check in checks}
    for name in CHECK_NAMES:
        ordered.append(by_name[name])
    factors = [factor for factor in factors if factor.get("check") in present]
    improve = _improve(trade, ordered, factors)
    text = _render(trade, ordered, factors, improve)
    return _document(trade, ordered, factors, improve, text, attempts)


def _improve(trade, checks, factors):
    symbol = trade.get("symbol") or "this coin"
    by_name = {check["name"]: check for check in checks}
    failed = [check for check in checks if check.get("result") == "failed"]
    if factors:
        cited = "; ".join(factor["text"] for factor in factors)
        line = f"Improve entries: {symbol} showed {cited}. This does not change entry gates or config thresholds."
    elif failed:
        reasons = "; ".join(f"{check['name']} ({check['detail']})" for check in failed)
        line = f"Improve entries: do not add a filter from {symbol}; these checks failed after retry: {reasons}."
    else:
        price = by_name.get("price_mcap_path", {}).get("detail") or "price path was clean"
        line = (
            f"Improve entries: no red flag was measured on {symbol}. {price}. "
            "Holder, cluster, bundle, creator, liquidity, volume, and authority checks were clean. "
            "Do not add an entry filter from this close."
        )
    return _clip(line, limit=700)


def review_losing_trade(trade, market, config=None, review_token_fn=None, gather_fn=None, attempts=2, now=None):
    """Review one losing close. Retries a failed read once, then writes the failure."""
    if review_token_fn is None:
        from safety import review_token as review_token_fn
    if gather_fn is None:
        from entry_gates import gather_entry_evidence as gather_fn
    now = now if now is not None else time.time()
    attempts = max(1, int(attempts))
    ctx = None
    for attempt in range(1, attempts + 1):
        ctx = _gather(trade or {}, market, config, review_token_fn, gather_fn, now)
        ctx["attempt"] = attempt
        ctx["now"] = now
        if not _sources_failed(ctx) or attempt == attempts:
            break
    try:
        doc = _build(trade or {}, ctx, config, now)
    except Exception as exc:
        doc = failed_review(trade, f"{type(exc).__name__}: {exc}", attempts=attempts)
    if not review_is_complete(doc):
        doc = failed_review(trade, "internal review builder returned an incomplete document", attempts=attempts)
    return doc
