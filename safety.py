"""Rug and holder checks on data the public Solana RPC actually returned.

Nothing here is inferred when the account data is missing. Incomplete checks
are not passes.
"""
from __future__ import annotations

from sources import SourceError, num

TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
TOKEN_LEGACY = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
BURN_OWNERS = {
    "1nc1nerator11111111111111111111111111111111",
    "11111111111111111111111111111111",
}
# Executable-owner is the real program test. This list only labels known venues.
KNOWN_AMM = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium AMM v4
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",  # Raydium CLMM
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",  # Raydium CPMM
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",  # Orca Whirlpool
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",  # Orca v2
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",  # Meteora DLMM
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB",  # Meteora pools
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",  # pump.fun
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",  # PumpSwap
}
RISKY_EXTENSIONS = {
    "permanentdelegate": "permanentDelegate",
    "transferhook": "transferHook",
    "nontransferable": "nonTransferable",
    "transferfeeconfig": "transferFeeConfig",
    "defaultaccountstate": "defaultAccountState",
}


def _ext_name(ext):
    if not isinstance(ext, dict):
        return ""
    return str(ext.get("extension") or "").replace("_", "").lower()


def assess_mint(mint_value, largest, owner_meta, supply_raw, decimals, liquidity_base, holder_fail_pct=3.5):
    """Pure assessment. `owner_meta` maps wallet -> {'executable': bool|None}."""
    checks = []
    hard = []
    warnings = []

    if not mint_value or not isinstance(mint_value, dict):
        return _result("incomplete", ["mint account missing"], checks, warnings, {})

    data = mint_value.get("data")
    parsed = data.get("parsed") if isinstance(data, dict) else None
    if not isinstance(parsed, dict) or parsed.get("type") != "mint":
        return _result("incomplete", ["account is not a parsed mint"], checks, warnings, {})
    info = parsed.get("info") or {}
    program = mint_value.get("owner")
    token2022 = program == TOKEN_2022
    extensions = info.get("extensions") or []
    risky = []
    for ext in extensions if isinstance(extensions, list) else []:
        key = _ext_name(ext)
        if key in RISKY_EXTENSIONS:
            risky.append(RISKY_EXTENSIONS[key])

    mint_auth = info.get("mintAuthority")
    freeze_auth = info.get("freezeAuthority")
    mint_active = bool(mint_auth)
    freeze_active = bool(freeze_auth)
    checks.append({"name": "Mint authority revoked", "pass": not mint_active, "detail": "null" if not mint_active else str(mint_auth)})
    checks.append({"name": "Freeze authority revoked", "pass": not freeze_active, "detail": "null" if not freeze_active else str(freeze_auth)})
    if mint_active:
        hard.append("live mint authority")
    if freeze_active:
        hard.append("live freeze authority")
    if risky:
        hard.append("risky Token-2022 extensions: " + ", ".join(risky))
    checks.append({
        "name": "Token-2022 risky extensions",
        "pass": not risky,
        "detail": "none of permanentDelegate, transferHook, nonTransferable, transferFeeConfig, defaultAccountState" if not risky else ", ".join(risky),
    })

    try:
        supply = int(supply_raw)
    except (TypeError, ValueError):
        supply = 0
    if supply <= 0:
        return _result("incomplete", ["token supply missing or zero"], checks, warnings, {
            "token_program": program,
            "token2022": token2022,
            "risky_extensions": risky,
            "mint_authority_active": mint_active,
            "freeze_authority_active": freeze_active,
        })

    humans = []
    excluded = []
    burned_raw = 0
    program_raw = 0
    lp_matched = False
    for row in largest or []:
        amount = int(row.get("amount") or 0)
        owner = row.get("owner")
        meta = owner_meta.get(owner) or {}
        executable = meta.get("executable")
        pct = amount / supply * 100.0
        ui = amount / (10 ** decimals) if decimals is not None else None
        is_burn = owner in BURN_OWNERS or row.get("address") in BURN_OWNERS
        is_lp = False
        if liquidity_base and ui is not None and liquidity_base > 0:
            if abs(ui - liquidity_base) / liquidity_base <= 0.25:
                is_lp = True
                lp_matched = True
        is_program = executable is True or owner in KNOWN_AMM
        entry = {
            "owner": owner,
            "token_account": row.get("address"),
            "pct": round(pct, 4),
            "ui_amount": ui,
            "executable": executable,
            "excluded_as": None,
        }
        if is_burn:
            entry["excluded_as"] = "burn"
            burned_raw += amount
            excluded.append(entry)
        elif is_lp:
            entry["excluded_as"] = "lp_vault"
            excluded.append(entry)
        elif is_program:
            entry["excluded_as"] = "program"
            program_raw += amount
            excluded.append(entry)
        else:
            humans.append(entry)

    humans.sort(key=lambda h: h["pct"], reverse=True)
    top = humans[0]["pct"] if humans else 0.0
    holder_fail = top > float(holder_fail_pct)
    if holder_fail:
        hard.append(f"non-LP non-program holder owns {top:.2f}% (limit {holder_fail_pct}%)")
    checks.append({
        "name": f"No single wallet above {holder_fail_pct}%",
        "pass": not holder_fail,
        "detail": "no qualifying wallet in the largest-account list" if not humans else f"top wallet {top:.2f}%",
    })
    if not lp_matched:
        warnings.append("LP vault was not matched to DexScreener base liquidity on the largest accounts; lock/burn of the LP token is not visible")
    if burned_raw:
        warnings.append(f"{burned_raw / supply * 100:.2f}% of supply sits in a burn address (this is a supply burn, not proof the LP token was burned)")
    program_pct = program_raw / supply * 100.0
    if program_pct >= 20:
        warnings.append(f"executable or known-venue programs hold {program_pct:.2f}% and those balances were excluded from the 3.5% wallet test")
    liq_note = "matched a largest account within 25% of DexScreener base liquidity" if lp_matched else "not visible on the largest base-token accounts"
    checks.append({"name": "LP locked or burned", "pass": None, "detail": liq_note})
    checks.append({
        "name": "Creator or dev wallet",
        "pass": None,
        "detail": "not identifiable from the free mint account. The largest non-LP non-program holder is reported, but the RPC mint data does not label a creator.",
    })

    status = "fail" if hard else "pass"
    extra = {
        "token_program": program,
        "token2022": token2022,
        "risky_extensions": risky,
        "mint_authority_active": mint_active,
        "freeze_authority_active": freeze_active,
        "holder_over_3_5": holder_fail,
        "top_human_pct": round(top, 4),
        "top_human": humans[0]["owner"] if humans else None,
        "humans": humans[:8],
        "excluded": excluded[:8],
        "lp_matched": lp_matched,
        "lp_locked": False,
        "lp_burned": False,
        "supply_burn_pct": round(burned_raw / supply * 100.0, 4),
        "program_hold_pct": round(program_pct, 4),
        "holder_fail_pct": holder_fail_pct,
        "extensions": [ext.get("extension") for ext in extensions if isinstance(ext, dict)],
    }
    return _result(status, hard, checks, warnings, extra)


def _result(status, hard, checks, warnings, extra):
    out = {
        "status": status,
        "hard_fails": hard,
        "checks": checks,
        "warnings": warnings,
        "summary": _summary(status, hard, warnings),
    }
    out.update(extra)
    return out


def _summary(status, hard, warnings):
    if status == "incomplete":
        return "incomplete: " + "; ".join(hard or ["missing data"])
    if status == "fail":
        return "FAIL " + "; ".join(hard)
    if warnings:
        return "PASS with warnings: " + "; ".join(warnings[:3])
    return "PASS mint, freeze, extensions, and holder concentration"


def cluster_flags(samples, holder_fail_pct=3.5):
    """samples: [{owner, pct, slots, funders}] from a bounded recent-signature sample.

    Shared recent slot is a flag only. A shared SOL funding source in the sample
    fails the token when the flagged wallets together exceed the holder limit.
    This is not a full bubble-map history.
    """
    flags = []
    fail = False
    by_slot = {}
    by_funder = {}
    for row in samples:
        for slot in row.get("slots") or []:
            by_slot.setdefault(slot, []).append(row)
        for funder in row.get("funders") or []:
            by_funder.setdefault(funder, []).append(row)
    for slot, rows in by_slot.items():
        owners = {r["owner"] for r in rows}
        if len(owners) >= 2:
            flags.append({
                "kind": "same_slot",
                "slot": slot,
                "owners": sorted(owners),
                "fail": False,
                "detail": "same slot appears in the recent signature sample; not treated as proof of one buyer",
            })
    for funder, rows in by_funder.items():
        owners = []
        seen = set()
        pct = 0.0
        for row in rows:
            if row["owner"] in seen:
                continue
            seen.add(row["owner"])
            owners.append(row["owner"])
            pct += float(row.get("pct") or 0)
        if len(owners) >= 2:
            linked_fail = pct > float(holder_fail_pct)
            if linked_fail:
                fail = True
            flags.append({
                "kind": "same_funding_source",
                "funder": funder,
                "owners": owners,
                "combined_pct": round(pct, 4),
                "fail": linked_fail,
                "detail": "shared SOL source inside the sampled transactions, which are recent signatures only",
            })
    return {"flags": flags, "fail": fail, "sampled": len(samples)}


def extract_funders(tx, holder):
    if not isinstance(tx, dict):
        return set()
    found = set()

    def walk(ix):
        if not isinstance(ix, dict):
            return
        parsed = ix.get("parsed")
        if not isinstance(parsed, dict):
            return
        if str(ix.get("program") or "").lower() != "system":
            return
        if parsed.get("type") != "transfer":
            return
        info = parsed.get("info") or {}
        lamports = info.get("lamports") or 0
        try:
            lamports = int(lamports)
        except (TypeError, ValueError):
            lamports = 0
        if info.get("destination") == holder and info.get("source") and lamports >= 5_000_000:
            found.add(info["source"])

    message = ((tx.get("transaction") or {}).get("message") or {})
    for ix in message.get("instructions") or []:
        walk(ix)
    for inner in (tx.get("meta") or {}).get("innerInstructions") or []:
        if isinstance(inner, dict):
            for ix in inner.get("instructions") or []:
                walk(ix)
    return found


def review_token(rpc, mint, liquidity_base, holder_fail_pct=3.5):
    """Networked review. Raises SourceError only for unexpected bugs; RPC errors become incomplete."""
    try:
        mint_result = rpc.call("getAccountInfo", [mint, {"encoding": "jsonParsed"}])
        supply_result = rpc.call("getTokenSupply", [mint])
        largest_result = rpc.call("getTokenLargestAccounts", [mint])
    except SourceError as exc:
        return _result("incomplete", [str(exc)], [], [], {"mint": mint})

    mint_value = (mint_result or {}).get("value") if isinstance(mint_result, dict) else None
    supply_value = (supply_result or {}).get("value") if isinstance(supply_result, dict) else None
    if not supply_value:
        return _result("incomplete", ["getTokenSupply returned no value"], [], [], {"mint": mint})
    decimals = int(supply_value.get("decimals") or 0)
    raw_largest = (largest_result or {}).get("value") if isinstance(largest_result, dict) else None
    if not isinstance(raw_largest, list):
        return _result("incomplete", ["getTokenLargestAccounts returned no list"], [], [], {"mint": mint})

    accounts = []
    for row in raw_largest[:20]:
        if isinstance(row, dict) and row.get("address"):
            accounts.append(row)
    owners = {}
    if accounts:
        try:
            multi = rpc.call("getMultipleAccounts", [[a["address"] for a in accounts], {"encoding": "jsonParsed"}])
        except SourceError as exc:
            return _result("incomplete", [f"holder accounts unreadable: {exc}"], [], [], {"mint": mint})
        values = (multi or {}).get("value") if isinstance(multi, dict) else None
        if not isinstance(values, list):
            return _result("incomplete", ["getMultipleAccounts returned no holder list"], [], [], {"mint": mint})
        parsed_rows = []
        owner_ids = []
        for raw, value in zip(accounts, values):
            info = (((value or {}).get("data") or {}).get("parsed") or {}).get("info") if isinstance(value, dict) else None
            if not isinstance(info, dict):
                continue
            owner = info.get("owner")
            amount = (info.get("tokenAmount") or {}).get("amount") or raw.get("amount")
            parsed_rows.append({"address": raw.get("address"), "owner": owner, "amount": amount})
            if owner:
                owner_ids.append(owner)
        owner_meta = {owner: {"executable": None} for owner in owner_ids}
        if owner_ids:
            try:
                owned = rpc.call("getMultipleAccounts", [owner_ids, {"encoding": "base64"}])
                ovalues = (owned or {}).get("value") if isinstance(owned, dict) else None
                if isinstance(ovalues, list):
                    for owner, value in zip(owner_ids, ovalues):
                        if isinstance(value, dict):
                            owner_meta[owner] = {"executable": bool(value.get("executable"))}
            except SourceError as exc:
                return _result("incomplete", [f"holder owners unreadable: {exc}"], [], [], {"mint": mint})
        assessed = assess_mint(mint_value, parsed_rows, owner_meta, supply_value.get("amount"), decimals, num(liquidity_base), holder_fail_pct)
    else:
        assessed = assess_mint(mint_value, [], {}, supply_value.get("amount"), decimals, num(liquidity_base), holder_fail_pct)
    assessed["mint"] = mint
    assessed["decimals"] = decimals
    assessed["supply_ui"] = supply_value.get("uiAmountString") or supply_value.get("uiAmount")
    return assessed


def sample_links(rpc, humans, holder_fail_pct=3.5, tx_budget=2):
    """Bounded link sample. `humans` is the assess list. Uses few RPC calls."""
    samples = []
    tx_left = tx_budget
    try:
        for human in humans[:3]:
            owner = human.get("owner")
            if not owner:
                continue
            sigs = rpc.call("getSignaturesForAddress", [owner, {"limit": 8}])
            slots = []
            signature = None
            if isinstance(sigs, list):
                for sig in sigs:
                    if isinstance(sig, dict) and sig.get("slot") is not None:
                        slots.append(sig.get("slot"))
                        signature = signature or sig.get("signature")
            funders = set()
            if signature and tx_left > 0:
                tx_left -= 1
                tx = rpc.call("getTransaction", [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
                funders = extract_funders(tx, owner)
            samples.append({"owner": owner, "pct": human.get("pct") or 0, "slots": slots, "funders": sorted(funders)})
    except SourceError as exc:
        flags = cluster_flags(samples, holder_fail_pct)
        flags["error"] = str(exc)
        flags["detail"] = "linked-wallet sample stopped early: " + str(exc)
        return flags
    flags = cluster_flags(samples, holder_fail_pct)
    if not samples:
        flags["detail"] = "no human holders to sample"
    else:
        flags["detail"] = f"sampled {len(samples)} wallets, up to 8 recent signatures each; not a full funding history"
    return flags
