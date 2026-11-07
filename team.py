"""One-team vote on every paper trade.

All six agents share one paper P&L. A trade is attributed to the agent that
proposed it, but it is only taken (written to the ledger) when the team
approves it:

* every agent casts approve / reject / abstain with a one-line reason taken
  from its real check results (nothing is invented; an agent with no data
  abstains);
* Risk Manager and Bubble Map Analyst rejections are hard vetoes;
* otherwise a strict majority of the agents that voted (not abstained) must
  approve.

Paper trading / research only. No wallet. No real trades.
"""
from __future__ import annotations

from events import emit

ROLES = ["Risk Manager", "Bubble Map Analyst", "X/Twitter Scout", "Data Scout", "Backtester", "Strategist"]
VETO_ROLES = {"Risk Manager", "Bubble Map Analyst"}
APPROVE, REJECT, ABSTAIN = "approve", "reject", "abstain"


def _vote(agent, vote, reason):
    emit(agent, "vote", f"{vote}: {reason[:200]}")
    return {"agent": agent, "vote": vote, "reason": reason[:200]}


def risk_vote(token):
    safety = token.get("safety") or {}
    status = safety.get("status")
    if status != "pass":
        fails = "; ".join(safety.get("hard_fails") or []) or safety.get("summary") or "no safety result"
        return _vote("Risk Manager", REJECT, f"Chain safety {status or 'missing'}: {fails}")
    if token.get("lesson_blocks"):
        return _vote("Risk Manager", REJECT, f"Blocked by lesson: {token['lesson_blocks'][0]}")
    bits = []
    bits.append("mint authority " + ("active" if safety.get("mint_authority_active") else "revoked"))
    bits.append("freeze " + ("active" if safety.get("freeze_authority_active") else "revoked"))
    if safety.get("risky_extensions"):
        return _vote("Risk Manager", REJECT, "Risky Token-2022 extensions: " + ", ".join(map(str, safety["risky_extensions"])))
    return _vote("Risk Manager", APPROVE, "Safety pass: " + ", ".join(bits) + ".")


def bubble_vote(token, holder_limit=3.5):
    safety = token.get("safety") or {}
    top = safety.get("top_human_pct")
    if safety.get("holder_over_3_5") or (top is not None and float(top) > holder_limit):
        return _vote("Bubble Map Analyst", REJECT, f"One wallet holds {top}% (> {holder_limit}% fail line).")
    if safety.get("cluster_fail"):
        return _vote("Bubble Map Analyst", REJECT, f"Linked wallets share a funder and together exceed {holder_limit}%.")
    if top is None:
        return _vote("Bubble Map Analyst", REJECT, "Holder concentration was not measured; not treated as a pass.")
    return _vote("Bubble Map Analyst", APPROVE, f"Top non-LP wallet {top}% (≤ {holder_limit}%), no linked-wallet fail.")


def x_vote(token, x_status):
    x_status = x_status or {}
    if x_status.get("ok"):
        # The X API is reachable: still no per-token sentiment model, so the
        # scout only reports what it can see and does not swing the vote.
        return _vote("X/Twitter Scout", ABSTAIN, "X API reachable but no per-token read was run; abstaining.")
    code = x_status.get("status")
    link = "has an X link" if token.get("twitter") else "has no X link"
    return _vote("X/Twitter Scout", ABSTAIN, f"X API unavailable ({code or 'no access'}); token {link}. No tweets read, abstaining.")


def data_vote(trade, token, config):
    filters = config.get("filters") or {}
    zone = config.get("entry_zone") or {}
    lo = float(zone.get("min_frac_of_ath", 0.2))
    hi = float(zone.get("max_frac_of_ath", 0.45))
    liq = token.get("liquidity_usd") or 0
    vol = token.get("volume_24h_usd") or 0
    frac = trade.get("entry_frac_of_ath")
    if liq < float(filters.get("min_liquidity_usd", 0)):
        return _vote("Data Scout", REJECT, f"Liquidity ${liq:,.0f} under the ${float(filters.get('min_liquidity_usd', 0)):,.0f} floor.")
    if vol < float(filters.get("min_volume_24h_usd", 0)):
        return _vote("Data Scout", REJECT, f"24h volume ${vol:,.0f} under the floor.")
    if frac is None:
        return _vote("Data Scout", REJECT, "Entry fraction of ATH unknown.")
    if not (lo <= frac <= hi):
        return _vote("Data Scout", REJECT, f"Entry at {frac*100:.0f}% of window ATH is outside the {lo*100:.0f}–{hi*100:.0f}% zone.")
    return _vote("Data Scout", APPROVE, f"Entry at {frac*100:.0f}% of window ATH, liq ${liq:,.0f}, vol ${vol:,.0f}.")


def backtest_vote(trade, prior):
    """prior: simulated trades on the same pool and variant that closed before this entry."""
    if len(prior) < 3:
        return _vote("Backtester", APPROVE, f"{len(prior)} earlier simulated fills on this pool; no evidence against.")
    net = sum(t.get("pnl_usd") or 0 for t in prior)
    if net < 0:
        return _vote("Backtester", REJECT, f"{len(prior)} earlier fills on this pool net ${net:.2f}.")
    return _vote("Backtester", APPROVE, f"{len(prior)} earlier fills on this pool net +${net:.2f}.")


def strategist_vote(trade, variant, can_test):
    frac = trade.get("entry_frac_of_ath")
    if not can_test:
        return _vote("Strategist", REJECT, f"{variant['id']} is already rejected; not trading it.")
    if frac is not None and frac > float(variant.get("zone_high", 0.45)):
        return _vote("Strategist", REJECT, "Entry above the variant's dip zone; that is a top tick.")
    return _vote("Strategist", APPROVE, f"Dip entry under {variant['id']} (stop {variant['stop']*100:.0f}%, target {variant['target']*100:.0f}%).")


def proposer_for(token):
    """Data Scout proposes a token it flagged inside the entry zone now; otherwise the Strategist's variant triggered it."""
    return "Data Scout" if token.get("in_entry_zone") else "Strategist"


def decide(votes):
    tally = {APPROVE: 0, REJECT: 0, ABSTAIN: 0}
    for v in votes:
        tally[v["vote"]] += 1
    vetoes = [v["agent"] for v in votes if v["agent"] in VETO_ROLES and v["vote"] == REJECT]
    voting = tally[APPROVE] + tally[REJECT]
    majority = voting > 0 and tally[APPROVE] * 2 > voting
    approved = majority and not vetoes
    if vetoes:
        rule = "vetoed by " + " and ".join(vetoes)
    elif approved:
        rule = f"majority {tally[APPROVE]}/{voting} of voting agents"
    else:
        rule = f"no majority ({tally[APPROVE]}/{voting})"
    return {
        "approved": approved,
        "approve": tally[APPROVE],
        "reject": tally[REJECT],
        "abstain": tally[ABSTAIN],
        "tally": f"{tally[APPROVE]}/{len(votes)} approve",
        "rule": rule,
        "vetoes": vetoes,
    }


def team_review(trade, token, variant, prior, config, x_status, can_test=True):
    votes = [
        risk_vote(token),
        bubble_vote(token, float(config.get("holder_fail_pct", 3.5))),
        x_vote(token, x_status),
        data_vote(trade, token, config),
        backtest_vote(trade, prior),
        strategist_vote(trade, variant, can_test),
    ]
    result = decide(votes)
    result["votes"] = votes
    result["proposed_by"] = proposer_for(token)
    return result


def review_trades(trades, tokens_by_mint, variant, config, x_status, can_test=True, entry_guard=None, on_approved=None):
    """Return (approved, rejected) with team fields attached to each trade."""
    approved, rejected = [], []
    by_pool = {}
    for trade in sorted(trades, key=lambda t: t.get("entry_ts") or 0):
        # Guard is evaluated before any of the six votes. Exit processing must
        # remain outside this entry-only gate.
        if entry_guard is not None and not entry_guard(trade):
            continue
        token = tokens_by_mint.get(trade.get("mint")) or {}
        history = by_pool.setdefault(trade.get("mint"), [])
        prior = [t for t in history if (t.get("exit_ts") or 0) <= (trade.get("entry_ts") or 0)]
        result = team_review(trade, token, variant, prior, config, x_status, can_test)
        history.append(trade)
        trade["proposed_by"] = result["proposed_by"]
        trade["team"] = {k: result[k] for k in ("approved", "approve", "reject", "abstain", "tally", "rule", "vetoes", "votes")}
        (approved if result["approved"] else rejected).append(trade)
        if result["approved"] and on_approved is not None:
            on_approved(trade)
    return approved, rejected
