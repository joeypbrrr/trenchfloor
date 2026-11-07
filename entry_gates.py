"""Fail-closed hard entry gates for both paper tiers.

Public reads only: RPC account/signature lookups and an optional pump.fun HTTP
coin document. No wallet, signature, or swap.

A check passes only with positive evidence. A missing read, a rate limit, or a
truncated RPC budget is unknown and blocks entry. A full signature page proves
a wallet is at least as old as that page; it is not treated as a fresh wallet,
and it is not treated as a failed read.

Thresholds (config `entry_gates`, defaults below):
- Pair age >= 15 minutes. Same floor the primary market filter already used.
  Unknown age blocks. The five reviewed coins were all older than this.
- Top 10 holders, after dropping the pool and burn addresses, <= 40% of supply.
  The old primary cap was 65% and fallback did not veto. 40% still allows a
  broad holder set and rejects a majority-control cluster.
- Fresh-wallet cluster: a wallet is fresh only when its signature page is
  shorter than the fetch limit (so the oldest signature is its first activity)
  and that timestamp is under 24 hours old. Block at 3 such wallets in the top
  sample, or at 2+ whose combined supply is >= 8%. Wallet-hunters treats a
  shared funder as a link; two top holders funded by the same SOL source and
  together holding >= 5% also block. 24h matches the existing PumpPortal
  `wallet_min_history_seconds`.
- Bundle / sniper: 3+ sampled token accounts whose first observed signature
  shares one slot (a same-slot buy), or a sniper group of 3+ wallets that
  acquired within 5 slots of the earliest sampled acquisition and still hold
  >= 15% combined. 15% is the low end of the usual "coordinated supply" band.
- Wash: a sampled signer whose smaller side is >= 30% of the whole sampled
  pool flow, or an explicit upstream wash flag. An unreadable sample blocks.
  A two-sided fill that is only a small slice of the sample does not.
- LP: the chosen pool's own LP mint must exist and have supply 0, with mint
  authority revoked or set to the pool. Anything else, including "not visible",
  blocks. PumpSwap's pool `lp_supply` field stays non-zero after that burn, so
  it is not used as the lock proof.
- Global fees >= 1.5 SOL. Verified cumulative fees (complete create-to-now
  coverage, or a pump.fun coin field that is explicitly cumulative) can pass
  or fail. Otherwise the PumpSwap pool's unclaimed protocol+creator lamports
  are only a lower bound, because sweeps remove them. A lower bound already
  >= 1.5 SOL passes. A smaller or unreadable bound stays unknown and blocks.
  Reported DEX volume is not a fee proxy.
"""
from __future__ import annotations

import base64
import hashlib
import struct
import time

from safety import BURN_OWNERS, extract_funders
from sources import SOL_MINT, SourceError, num

PUMP_AMM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
POOL_DISC = hashlib.sha256(b"account:Pool").digest()[:8]
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

DEFAULTS = {
    "min_pair_age_hours": 0.25,
    "max_top10_pct": 40.0,
    "fresh_wallet_seconds": 86400,
    "min_fresh_wallets": 3,
    "max_fresh_cluster_pct": 8.0,
    "min_linked_wallets": 2,
    "max_linked_funder_pct": 5.0,
    "same_slot_min_wallets": 3,
    "max_bundle_sniper_pct": 15.0,
    "sniper_slot_window": 5,
    "max_wash_roundtrip_fraction": 0.30,
    "min_global_fees_sol": 1.5,
    "holder_sample": 5,
    "signature_limit": 20,
    "funder_tx_budget": 5,
    "wash_tx_budget": 6,
}

GLOBAL_FEES_POLICY = (
    "ENFORCED fail-closed: need verified cumulative global fees >= 1.5 SOL, "
    "or an on-chain PumpSwap unclaimed protocol+creator lower bound already >= 1.5 SOL. "
    "Unreadable or unproven lifetime fees block entry. No DexScreener volume proxy."
)

# pump.fun coin JSON keys that mean lifetime protocol+creator fees in SOL,
# not a pending vault balance and not a per-trade gas figure.
_CUMULATIVE_FEE_KEYS = (
    "cumulative_global_fees_sol",
    "global_fees_sol",
    "total_global_fees_sol",
    "cumulative_fees_sol",
)


def _b58(raw):
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, rem = divmod(n, 58)
        out = _B58[rem] + out
    pad = 0
    for byte in raw:
        if byte == 0:
            pad += 1
        else:
            break
    return "1" * pad + (out or "")


def decode_pumpswap_pool(data):
    """Return pool fields, or None when the account is not a PumpSwap pool."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 287 or data[:8] != POOL_DISC:
        return None
    off = 8
    off += 1  # bump
    off += 2  # index

    def pubkey():
        nonlocal off
        value = _b58(data[off:off + 32])
        off += 32
        return value

    creator = pubkey()
    base_mint = pubkey()
    quote_mint = pubkey()
    lp_mint = pubkey()
    base_vault = pubkey()
    quote_vault = pubkey()
    off += 8  # lp_supply is not the SPL mint supply; ignored on purpose
    coin_creator = pubkey()
    off += 2  # mayhem, cashback flags
    off += 16  # virtual quote reserves
    off += 8  # creator fee bps
    off += 2  # two bools
    protocol_fees = struct.unpack_from("<Q", data, off)[0]
    off += 8
    creator_fees = struct.unpack_from("<Q", data, off)[0]
    return {
        "creator": creator,
        "base_mint": base_mint,
        "quote_mint": quote_mint,
        "lp_mint": lp_mint,
        "base_vault": base_vault,
        "quote_vault": quote_vault,
        "coin_creator": coin_creator,
        "protocol_fees_lamports": protocol_fees,
        "creator_fees_lamports": creator_fees,
    }


def _settings(config):
    raw = {}
    if isinstance(config, dict):
        raw = config.get("entry_gates") if isinstance(config.get("entry_gates"), dict) else config
    out = dict(DEFAULTS)
    for key, value in (raw or {}).items():
        if key in DEFAULTS and value is not None:
            out[key] = value
    return out


def _add(checks, name, passed, detail):
    checks.append({"name": name, "pass": passed, "detail": detail})


def _fresh_rows(holders, now, fresh_seconds):
    fresh = []
    for row in holders:
        if row.get("history_complete") is not True:
            continue
        oldest = num(row.get("oldest_ts"))
        if oldest is None:
            continue
        if now - oldest < float(fresh_seconds):
            fresh.append(row)
    return fresh


def assess_entry_gates(evidence, config=None, now=None):
    """Pure gate list. `pass` is True, False, or None (unknown / fail closed)."""
    evidence = evidence or {}
    settings = _settings(config)
    now = now if now is not None else evidence.get("now") or time.time()
    checks = []
    created = num(evidence.get("created_ts"))
    if created is None:
        _add(checks, "min_pair_age", None, "UNKNOWN / FAIL CLOSED: pair age was not read; missing created time blocks entry")
    else:
        hours = (now - created) / 3600.0
        floor = float(settings["min_pair_age_hours"])
        if hours < floor:
            _add(checks, "min_pair_age", False, f"FAIL pair age {hours:.2f}h is under the {floor:g}h hard minimum")
        else:
            _add(checks, "min_pair_age", True, f"pair age {hours:.2f}h >= {floor:g}h")

    top10 = num(evidence.get("top10_ex_pool_burn_pct"))
    cap = float(settings["max_top10_pct"])
    if top10 is None:
        _add(checks, "top10_ex_pool_burn", None, "UNKNOWN / FAIL CLOSED: top-10 concentration excluding pool and burn accounts was not measured")
    elif top10 > cap:
        _add(checks, "top10_ex_pool_burn", False, f"FAIL top-10 non-pool non-burn holders are {top10:.2f}% (cap {cap:g}%)")
    else:
        _add(checks, "top10_ex_pool_burn", True, f"top-10 non-pool non-burn holders are {top10:.2f}% (cap {cap:g}%)")

    holders = evidence.get("holders") if isinstance(evidence.get("holders"), list) else None
    holder_ok = evidence.get("holder_read_ok") is True and holders is not None
    fresh = _fresh_rows(holders or [], now, settings["fresh_wallet_seconds"])
    fresh_pct = sum(float(row.get("pct") or 0) for row in fresh)
    fresh_fail = (
        len(fresh) >= int(settings["min_fresh_wallets"])
        or (len(fresh) >= 2 and fresh_pct >= float(settings["max_fresh_cluster_pct"]))
    )
    linked_fail = None
    by_funder = {}
    for row in holders or []:
        if row.get("funder_known") is not True:
            continue
        for funder in row.get("funders") or []:
            by_funder.setdefault(funder, []).append(row)
    for funder, rows in by_funder.items():
        seen = []
        pct = 0.0
        for row in rows:
            if row.get("owner") in seen:
                continue
            seen.append(row.get("owner"))
            pct += float(row.get("pct") or 0)
        if len(seen) >= int(settings["min_linked_wallets"]) and pct >= float(settings["max_linked_funder_pct"]):
            linked_fail = (funder, seen, pct)
            break
    if fresh_fail:
        _add(checks, "fresh_wallet_cluster", False,
             f"FAIL {len(fresh)} fresh wallets in the top-holder sample (block at {int(settings['min_fresh_wallets'])}) "
             f"holding {fresh_pct:.2f}% combined (block 2+ wallets at {float(settings['max_fresh_cluster_pct']):g}%); "
             "fresh means a complete signature page whose oldest transaction is under "
             f"{int(settings['fresh_wallet_seconds']) / 3600:g}h")
    elif linked_fail:
        funder, seen, pct = linked_fail
        _add(checks, "fresh_wallet_cluster", False,
             f"FAIL {len(seen)} top holders share funder {funder} and hold {pct:.2f}% "
             f"(cap {float(settings['max_linked_funder_pct']):g}%)")
    elif not holder_ok:
        err = evidence.get("holder_read_error") or "holder signature sample missing"
        _add(checks, "fresh_wallet_cluster", None, "UNKNOWN / FAIL CLOSED: " + str(err)[:240])
    else:
        _add(checks, "fresh_wallet_cluster", True,
             f"no fresh-wallet cluster in {len(holders)} sampled top holders; {len(fresh)} fresh, {fresh_pct:.2f}% combined")

    slot_rows = [row for row in (holders or []) if row.get("acquire_known") is True and row.get("acquire_slot") is not None]
    by_slot = {}
    for row in slot_rows:
        by_slot.setdefault(row["acquire_slot"], []).append(row)
    bundle = None
    for slot, rows in by_slot.items():
        owners = []
        for row in rows:
            if row.get("owner") not in owners:
                owners.append(row.get("owner"))
        if len(owners) >= int(settings["same_slot_min_wallets"]):
            bundle = (slot, owners, sum(float(r.get("pct") or 0) for r in rows))
            break
    sniper = None
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
            sniper = (len(owners), share, first)
    if bundle:
        slot, owners, pct = bundle
        _add(checks, "bundle_sniper_share", False,
             f"FAIL {len(owners)} top holders acquired in slot {slot} ({pct:.2f}% combined); same-slot buys are a bundle")
    elif sniper:
        count, share, first = sniper
        _add(checks, "bundle_sniper_share", False,
             f"FAIL {count} early buyers within {int(settings['sniper_slot_window'])} slots of {first} still hold {share:.2f}% "
             f"(cap {float(settings['max_bundle_sniper_pct']):g}%)")
    elif not holder_ok:
        err = evidence.get("holder_read_error") or "acquisition slots were not read"
        _add(checks, "bundle_sniper_share", None, "UNKNOWN / FAIL CLOSED: " + str(err)[:240])
    else:
        _add(checks, "bundle_sniper_share", True,
             f"no same-slot bundle and no sniper share at the cap in {len(slot_rows)} known acquisition slots")

    if evidence.get("is_wash_trading") is True:
        _add(checks, "wash_trade", False, "FAIL upstream wash-trading flag is set")
    else:
        trades = evidence.get("trades") if isinstance(evidence.get("trades"), list) else None
        trade_ok = evidence.get("trade_read_ok") is True and trades is not None
        roundtrip = None
        if trades:
            flow = {}
            total = 0.0
            for trade in trades:
                signer = trade.get("signer")
                side = trade.get("side")
                amount = num(trade.get("amount"))
                if not signer or side not in ("buy", "sell") or amount is None:
                    continue
                slot = flow.setdefault(signer, {"buy": 0.0, "sell": 0.0})
                slot[side] += amount
                total += amount
            fraction = float(settings["max_wash_roundtrip_fraction"])
            for signer, sides in flow.items():
                turned = min(sides["buy"], sides["sell"])
                if total > 0 and sides["buy"] > 0 and sides["sell"] > 0 and turned / total >= fraction:
                    roundtrip = (signer, turned / total)
                    break
        if roundtrip:
            signer, ratio = roundtrip
            _add(checks, "wash_trade", False,
                 f"FAIL signer {signer} round-tripped {ratio * 100:.0f}% of the sampled pool flow "
                 f"(cap {float(settings['max_wash_roundtrip_fraction']) * 100:.0f}%)")
        elif not trade_ok:
            err = evidence.get("trade_read_error") or "pool trade sample missing"
            _add(checks, "wash_trade", None, "UNKNOWN / FAIL CLOSED: " + str(err)[:240])
        else:
            _add(checks, "wash_trade", True, f"no wash round-trip in {len(trades)} sampled pool fills")

    if evidence.get("lp_visible") is True and evidence.get("lp_burned_or_locked") is True:
        _add(checks, "lp_locked_or_burned", True, evidence.get("lp_detail") or "LP mint supply is zero")
    elif evidence.get("lp_visible") is True and evidence.get("lp_burned_or_locked") is False:
        _add(checks, "lp_locked_or_burned", False, "FAIL " + (evidence.get("lp_detail") or "LP is unlocked"))
    else:
        _add(checks, "lp_locked_or_burned", None,
             "UNKNOWN / FAIL CLOSED: " + (evidence.get("lp_detail") or "LP lock/burn is not visible on the chosen pool"))

    need = float(settings["min_global_fees_sol"])
    verified = evidence.get("global_fees_verified") is True
    fees = num(evidence.get("global_fees_sol"))
    lower = num(evidence.get("fee_lower_bound_sol"))
    if verified and fees is not None and fees >= need:
        _add(checks, "global_fees_sol", True, f"verified cumulative global fees {fees:g} SOL >= {need:g} SOL")
    elif verified and fees is not None:
        _add(checks, "global_fees_sol", False, f"FAIL verified cumulative global fees {fees:g} SOL < {need:g} SOL")
    elif lower is not None and lower >= need:
        _add(checks, "global_fees_sol", True,
             f"unclaimed on-chain protocol+creator fees {lower:g} SOL already meet {need:g} SOL (lower bound)")
    elif lower is not None:
        _add(checks, "global_fees_sol", None,
             f"UNKNOWN / FAIL CLOSED: unclaimed on-chain protocol+creator fees are {lower:.6f} SOL. "
             f"Sweeps remove them, so this is not proof of lifetime global fees >= {need:g} SOL")
    else:
        _add(checks, "global_fees_sol", None,
             "UNKNOWN / FAIL CLOSED: " + str(evidence.get("fee_detail") or "cumulative global fees were not read")[:240])
    return checks


def measure_entry_signals(evidence, config=None, now=None):
    """Numeric readings behind the hard gates.

    Read-only. `assess_entry_gates` is still the pass/fail decision, and this
    function does not change that decision or the default thresholds. Missing
    reads stay None. A zero is returned only when the underlying sample was
    actually read and showed no qualifying cluster.
    """
    evidence = evidence or {}
    settings = _settings(config)
    now = now if now is not None else evidence.get("now") or time.time()
    checks = assess_entry_gates(evidence, config=config, now=now)
    created = num(evidence.get("created_ts"))
    pair_age_hours = None if created is None else (float(now) - created) / 3600.0
    holders = evidence.get("holders") if isinstance(evidence.get("holders"), list) else None
    holder_ok = evidence.get("holder_read_ok") is True and holders is not None

    fresh_measured = bool(holder_ok and all(isinstance(row, dict) and "history_complete" in row for row in holders))
    fresh = _fresh_rows(holders or [], now, settings["fresh_wallet_seconds"]) if fresh_measured else []
    fresh_count = len(fresh) if fresh_measured else None
    fresh_pct = sum(float(row.get("pct") or 0) for row in fresh) if fresh_measured else None

    linked_measured = bool(holder_ok and any(isinstance(row, dict) and row.get("funder_known") is True for row in holders))
    linked_pct = None
    linked_wallets = None
    if linked_measured:
        best_pct = 0.0
        best_n = 0
        by_funder = {}
        for row in holders:
            if row.get("funder_known") is not True:
                continue
            for funder in row.get("funders") or []:
                by_funder.setdefault(funder, []).append(row)
        for rows in by_funder.values():
            seen = []
            pct = 0.0
            for row in rows:
                owner = row.get("owner")
                if owner in seen:
                    continue
                seen.append(owner)
                pct += float(row.get("pct") or 0)
            if len(seen) >= int(settings["min_linked_wallets"]) and pct >= best_pct:
                best_pct = pct
                best_n = len(seen)
        linked_pct = best_pct
        linked_wallets = best_n

    slot_rows = [
        row for row in (holders or [])
        if isinstance(row, dict) and row.get("acquire_known") is True and row.get("acquire_slot") is not None
    ]
    same_slot_pct = None
    same_slot_wallets = None
    sniper_pct = None
    sniper_wallets = None
    if slot_rows:
        best_n = 0
        best_pct = 0.0
        by_slot = {}
        for row in slot_rows:
            by_slot.setdefault(row["acquire_slot"], []).append(row)
        min_wallets = int(settings["same_slot_min_wallets"])
        for rows in by_slot.values():
            seen = []
            pct = 0.0
            for row in rows:
                owner = row.get("owner")
                if owner in seen:
                    continue
                seen.append(owner)
                pct += float(row.get("pct") or 0)
            if len(seen) >= min_wallets and pct >= best_pct:
                best_n = len(seen)
                best_pct = pct
        same_slot_wallets = best_n
        same_slot_pct = best_pct
        first = min(row["acquire_slot"] for row in slot_rows)
        window = int(settings["sniper_slot_window"])
        early = [row for row in slot_rows if row["acquire_slot"] <= first + window]
        seen = []
        share = 0.0
        for row in early:
            owner = row.get("owner")
            if owner in seen:
                continue
            seen.append(owner)
            share += float(row.get("pct") or 0)
        sniper_wallets = len(seen)
        sniper_pct = share

    parts = []
    min_wallets = int(settings["same_slot_min_wallets"])
    if same_slot_pct is not None and (same_slot_wallets or 0) >= min_wallets:
        parts.append(same_slot_pct)
    if sniper_pct is not None and (sniper_wallets or 0) >= min_wallets:
        parts.append(sniper_pct)
    if linked_pct is not None and (linked_wallets or 0) >= int(settings["min_linked_wallets"]):
        parts.append(linked_pct)
    bundle_measured = bool(slot_rows) or linked_measured
    bundle_supply_pct = (max(parts) if parts else 0.0) if bundle_measured else None

    wash = None
    if evidence.get("is_wash_trading") is True:
        wash = 1.0
    else:
        trades = evidence.get("trades") if isinstance(evidence.get("trades"), list) else None
        trade_ok = evidence.get("trade_read_ok") is True and trades is not None
        if trade_ok:
            flow = {}
            total = 0.0
            for trade in trades:
                signer = trade.get("signer")
                side = trade.get("side")
                amount = num(trade.get("amount"))
                if not signer or side not in ("buy", "sell") or amount is None:
                    continue
                slot = flow.setdefault(signer, {"buy": 0.0, "sell": 0.0})
                slot[side] += amount
                total += amount
            wash = 0.0
            if total > 0:
                for sides in flow.values():
                    turned = min(sides["buy"], sides["sell"])
                    if sides["buy"] > 0 and sides["sell"] > 0:
                        wash = max(wash, turned / total)

    dev_hold = num(evidence.get("dev_hold_pct"))
    if dev_hold is None:
        dev_hold = num(evidence.get("creator_hold_pct"))
    dev_sold_fraction = num(evidence.get("dev_sold_fraction"))
    if "dev_dumped" in evidence or "dev_sold" in evidence:
        dev_sold_flag = 1.0 if evidence.get("dev_dumped") is True or evidence.get("dev_sold") is True else 0.0
    else:
        dev_sold_flag = None

    def _round(value):
        return None if value is None else round(float(value), 6)

    return {
        "pair_age_hours": _round(pair_age_hours),
        "top10_ex_pool_burn_pct": num(evidence.get("top10_ex_pool_burn_pct")),
        "fresh_wallet_count": fresh_count,
        "fresh_cluster_pct": _round(fresh_pct),
        "linked_funder_pct": _round(linked_pct),
        "linked_funder_wallets": linked_wallets,
        "bundle_same_slot_pct": _round(same_slot_pct),
        "bundle_same_slot_wallets": same_slot_wallets,
        "sniper_supply_pct": _round(sniper_pct),
        "sniper_wallets": sniper_wallets,
        "bundle_supply_pct": _round(bundle_supply_pct),
        "wash_roundtrip_fraction": _round(wash),
        "dev_hold_pct": dev_hold,
        "dev_sold_fraction": dev_sold_fraction,
        "dev_sold_flag": dev_sold_flag,
        "holder_measured": bool(holder_ok),
        "bundle_measured": bundle_measured,
        "fresh_measured": fresh_measured,
        "checks": checks,
    }


def _rpc(rpc, method, params):
    try:
        return rpc.call(method, params), None
    except (SourceError, TypeError, ValueError, AttributeError, OSError, KeyError) as exc:
        return None, str(exc)


def _account_bytes(value):
    data = (value or {}).get("data") if isinstance(value, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], str):
        try:
            return base64.b64decode(data[0])
        except (ValueError, TypeError):
            return None
    if isinstance(data, str):
        try:
            return base64.b64decode(data)
        except (ValueError, TypeError):
            return None
    return None


def trades_from_transaction(tx, mint):
    """One signer fill for `mint`, or None when the transaction cannot be read."""
    if not isinstance(tx, dict):
        return None
    message = ((tx.get("transaction") or {}).get("message") or {})
    keys = []
    for key in message.get("accountKeys") or []:
        if isinstance(key, str):
            keys.append({"pubkey": key, "signer": False})
        elif isinstance(key, dict) and key.get("pubkey"):
            keys.append({"pubkey": key.get("pubkey"), "signer": key.get("signer") is True})
    signers = [key["pubkey"] for key in keys if key["signer"]]
    signer = signers[0] if signers else (keys[0]["pubkey"] if keys else None)
    if not signer:
        return None

    def owned(rows):
        total = 0.0
        for row in rows or []:
            if not isinstance(row, dict) or row.get("mint") != mint or row.get("owner") != signer:
                continue
            ui = (row.get("uiTokenAmount") or {}).get("uiAmount")
            if ui is None:
                raw = (row.get("uiTokenAmount") or {}).get("amount")
                decimals = (row.get("uiTokenAmount") or {}).get("decimals") or 0
                try:
                    ui = int(raw) / (10 ** int(decimals))
                except (TypeError, ValueError):
                    return None
            total += float(ui)
        return total

    meta = tx.get("meta") or {}
    pre = owned(meta.get("preTokenBalances"))
    post = owned(meta.get("postTokenBalances"))
    if pre is None or post is None:
        return None
    delta = post - pre
    if abs(delta) < 1e-12:
        return []
    return [{"signer": signer, "side": "buy" if delta > 0 else "sell", "amount": abs(delta)}]


def _cumulative_fee_from_coin(payload):
    if not isinstance(payload, dict):
        return None
    for key in _CUMULATIVE_FEE_KEYS:
        value = num(payload.get(key))
        if value is not None:
            return value, key
    return None


def gather_entry_evidence(candidate, market, chain, config=None, http_get=None, now=None):
    """Bounded public reads. Failures stay on the evidence object and do not raise."""
    settings = _settings(config)
    now = now or time.time()
    chain = chain or {}
    candidate = candidate or {}
    evidence = {
        "now": now,
        "created_ts": candidate.get("created_ts"),
        "top10_ex_pool_burn_pct": num(chain.get("top10_measured_pct")),
        "holders": [],
        "holder_read_ok": False,
        "holder_read_error": None,
        "trades": [],
        "trade_read_ok": False,
        "trade_read_error": None,
        "is_wash_trading": candidate.get("is_wash_trading") is True,
        "lp_visible": False,
        "lp_burned_or_locked": None,
        "lp_detail": "LP lock/burn is not visible on the chosen pool",
        "global_fees_verified": candidate.get("global_fees_verified") is True and num(candidate.get("global_fees_sol")) is not None,
        "global_fees_sol": num(candidate.get("global_fees_sol")) if candidate.get("global_fees_verified") is True else None,
        "fee_lower_bound_sol": None,
        "fee_read_ok": False,
        "fee_detail": "cumulative global fees were not read",
        "creator": None,
        "coin_creator": None,
        "creator_detail": "creator wallet was not read",
    }
    if evidence["top10_ex_pool_burn_pct"] is None and chain.get("status") == "incomplete":
        evidence["top10_ex_pool_burn_pct"] = None
    rpc = getattr(market, "rpc", None)
    pool = candidate.get("pool")
    mint = candidate.get("mint")
    if rpc is None:
        evidence["holder_read_error"] = "RPC client missing; holder, bundle, wash, LP, and fee reads were not attempted"
        evidence["trade_read_error"] = evidence["holder_read_error"]
        evidence["fee_detail"] = evidence["holder_read_error"]
        evidence["lp_detail"] = evidence["holder_read_error"]
        evidence["creator_detail"] = evidence["holder_read_error"]
        return evidence

    humans = []
    for row in chain.get("humans") or []:
        owner = row.get("owner")
        if not owner or owner == pool or owner in BURN_OWNERS:
            continue
        humans.append(row)
    humans = humans[:int(settings["holder_sample"])]
    limit = int(settings["signature_limit"])
    holder_error = None
    prepared = []
    for row in humans:
        owner_sigs, err = _rpc(rpc, "getSignaturesForAddress", [row["owner"], {"limit": limit}])
        if err or not isinstance(owner_sigs, list) or len(owner_sigs) == 0:
            holder_error = err or "holder signature list was empty or unreadable; wallet age is unknown"
            if holder_error and "429" in holder_error:
                holder_error = "RPC rate limit (429) on holder signatures; " + holder_error
            break
        times = [sig.get("blockTime") for sig in owner_sigs if isinstance(sig, dict) and sig.get("blockTime") is not None]
        oldest_sig = None
        for sig in reversed(owner_sigs):
            if isinstance(sig, dict) and sig.get("signature"):
                oldest_sig = sig.get("signature")
                break
        token_account = row.get("token_account")
        acquire_slot = None
        acquire_known = False
        if token_account:
            token_sigs, token_err = _rpc(rpc, "getSignaturesForAddress", [token_account, {"limit": limit}])
            if token_err or not isinstance(token_sigs, list):
                holder_error = token_err or "token-account signatures were not a list"
                break
            if len(token_sigs) < limit:
                for sig in reversed(token_sigs):
                    if isinstance(sig, dict) and sig.get("slot") is not None:
                        acquire_slot = sig.get("slot")
                        acquire_known = True
                        break
        prepared.append({
            "owner": row["owner"],
            "pct": float(row.get("pct") or 0),
            "history_complete": len(owner_sigs) < limit and len(owner_sigs) > 0,
            "oldest_ts": min(times) if times else None,
            "oldest_signature": oldest_sig,
            "funders": [],
            "funder_known": False,
            "acquire_slot": acquire_slot,
            "acquire_known": acquire_known,
        })
    funder_budget = int(settings["funder_tx_budget"])
    for row in prepared:
        if funder_budget <= 0:
            break
        if row["history_complete"] is not True or not row.get("oldest_signature"):
            continue
        funder_budget -= 1
        tx, err = _rpc(rpc, "getTransaction", [row["oldest_signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
        if err:
            holder_error = err
            break
        if not isinstance(tx, dict):
            continue
        row["funders"] = sorted(extract_funders(tx, row["owner"]))
        row["funder_known"] = True
    evidence["holders"] = prepared
    if holder_error:
        evidence["holder_read_error"] = holder_error
    elif not humans and num(chain.get("top10_measured_pct")) is None and chain.get("status") == "incomplete":
        evidence["holder_read_error"] = "holder accounts were not read completely"
    else:
        evidence["holder_read_ok"] = True

    decoded = None
    if pool:
        info, err = _rpc(rpc, "getAccountInfo", [pool, {"encoding": "base64"}])
        value = (info or {}).get("value") if isinstance(info, dict) else None
        raw = _account_bytes(value)
        decoded = decode_pumpswap_pool(raw) if raw else None
        if decoded and mint in (decoded["base_mint"], decoded["quote_mint"]):
            evidence["creator"] = decoded["creator"]
            evidence["coin_creator"] = decoded["coin_creator"]
            evidence["creator_detail"] = "PumpSwap pool creator and coin_creator pubkeys"
            lp_mint = decoded["lp_mint"]
            supply, supply_err = _rpc(rpc, "getTokenSupply", [lp_mint])
            mint_info, mint_err = _rpc(rpc, "getAccountInfo", [lp_mint, {"encoding": "jsonParsed"}])
            mint_value = (mint_info or {}).get("value") if isinstance(mint_info, dict) else None
            parsed = (((mint_value or {}).get("data") or {}).get("parsed") or {}) if isinstance(mint_value, dict) else {}
            mint_fields = parsed.get("info") if parsed.get("type") == "mint" else None
            amount = ((supply or {}).get("value") or {}).get("amount") if isinstance(supply, dict) else None
            if supply_err or mint_err or not isinstance(mint_fields, dict) or amount is None:
                evidence["lp_detail"] = "LP lock/burn is not visible: " + (supply_err or mint_err or "LP mint supply/authority unreadable")
            else:
                authority = mint_fields.get("mintAuthority")
                try:
                    supply_raw = int(amount)
                except (TypeError, ValueError):
                    supply_raw = None
                if supply_raw == 0 and (authority is None or authority == pool):
                    evidence["lp_visible"] = True
                    evidence["lp_burned_or_locked"] = True
                    evidence["lp_detail"] = "chosen pool LP mint supply is 0 and mint authority is the pool or revoked"
                elif supply_raw is not None and supply_raw > 0:
                    evidence["lp_visible"] = True
                    evidence["lp_burned_or_locked"] = False
                    evidence["lp_detail"] = f"LP mint {lp_mint} still has supply {supply_raw}"
                else:
                    evidence["lp_detail"] = "LP lock/burn is not visible: mint authority is neither the pool nor revoked"
            if decoded["quote_mint"] == SOL_MINT:
                lamports = int(decoded["protocol_fees_lamports"]) + int(decoded["creator_fees_lamports"])
                evidence["fee_lower_bound_sol"] = lamports / 1_000_000_000
                evidence["fee_read_ok"] = True
                evidence["fee_detail"] = "PumpSwap pool unclaimed protocol+creator lamports; sweeps make this a lower bound, not lifetime fees"
            elif evidence["global_fees_sol"] is None:
                evidence["fee_detail"] = "pool quote is not SOL, so unclaimed fees are not a SOL global-fee total"
        else:
            evidence["lp_detail"] = err or "LP lock/burn is not visible: chosen pool is not a decoded PumpSwap pool for this mint"
            if not evidence["global_fees_verified"]:
                evidence["fee_detail"] = evidence["lp_detail"]
    if not evidence.get("creator") and not evidence.get("coin_creator"):
        evidence["creator_detail"] = evidence.get("lp_detail") or evidence.get("holder_read_error") or evidence.get("creator_detail")
    if evidence["global_fees_verified"]:
        evidence["fee_read_ok"] = True
        evidence["fee_detail"] = "verified cumulative global fees"

    if http_get is not None and not evidence["global_fees_verified"] and mint:
        try:
            payload, _status = http_get("https://frontend-api-v3.pump.fun/coins-v2/" + mint, timeout=8, attempts=1)
            found = _cumulative_fee_from_coin(payload if isinstance(payload, dict) else None)
            if found is not None:
                evidence["global_fees_sol"] = found[0]
                evidence["global_fees_verified"] = True
                evidence["fee_read_ok"] = True
                evidence["fee_detail"] = "pump.fun coin field " + found[1]
        except (SourceError, TypeError, ValueError, OSError):
            # HTTP 403/unavailable does not become a zero. The on-chain bound above still applies.
            pass

    if pool and mint:
        sigs, err = _rpc(rpc, "getSignaturesForAddress", [pool, {"limit": int(settings["wash_tx_budget"])}])
        if err or not isinstance(sigs, list):
            evidence["trade_read_error"] = err or "pool signature sample was not a list"
            if evidence["trade_read_error"] and "429" in evidence["trade_read_error"]:
                evidence["trade_read_error"] = "RPC rate limit (429) on pool trades; " + evidence["trade_read_error"]
        else:
            trades = []
            failed = None
            for sig in sigs:
                signature = sig.get("signature") if isinstance(sig, dict) else None
                if not signature:
                    continue
                tx, tx_err = _rpc(rpc, "getTransaction", [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
                if tx_err:
                    failed = tx_err
                    break
                parsed = trades_from_transaction(tx, mint)
                if parsed is None:
                    failed = "a pool transaction could not be parsed"
                    break
                trades.extend(parsed)
            evidence["trades"] = trades
            if failed:
                evidence["trade_read_error"] = failed
            else:
                evidence["trade_read_ok"] = True
    else:
        evidence["trade_read_error"] = "pool or mint missing; wash sample not read"
    if holder_error and evidence["holder_read_ok"] is not True:
        evidence["holder_read_error"] = holder_error
    return evidence
