"""Free public market-data clients. No API keys. No GMGN. No wallets.

GMGN is never requested. Callers may format https://gmgn.ai/sol/token/<mint>
as a convenience link; this module does not know that host.
"""
from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = "TrenchfloorResearch/1.0 (+https://github.com/joeypbrrr/trenchfloor)"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
QUOTE_MINTS = {SOL_MINT, USDC_MINT, USDT_MINT}
SKIP_MINTS = set(QUOTE_MINTS)
SKIP_SYMBOLS = {"SOL", "WSOL", "USDC", "USDT", "USD1"}


class SourceError(RuntimeError):
    def __init__(self, message, url=None, status=None):
        super().__init__(message)
        self.url = url
        self.status = status


class Limiter:
    def __init__(self, min_interval):
        self.min_interval = float(min_interval)
        self.last = 0.0

    def wait(self):
        if self.min_interval <= 0:
            return
        delay = self.last + self.min_interval - time.time()
        if delay > 0:
            time.sleep(delay)
        self.last = time.time()


def num(value):
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def parse_time(value):
    """Return a unix timestamp (seconds) or None. Never invents one."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if v > 10_000_000_000:
            return v / 1000.0
        return v
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def http_json(url, payload=None, headers=None, timeout=20, attempts=3, limiter=None, method=None):
    last = None
    for attempt in range(attempts):
        if limiter:
            limiter.wait()
        hdrs = {"User-Agent": UA, "Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            hdrs["Content-Type"] = "application/json"
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                raw = res.read()
                status = res.status
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise SourceError(f"non-JSON body from {url}: {exc}", url, status) from exc
            return parsed, status
        except SourceError:
            raise
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:240]
            except Exception:
                body = ""
            last = SourceError(f"HTTP {exc.code} {exc.reason} {body}".strip(), url, exc.code)
            if exc.code in (429, 502, 503, 504) and attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise last from exc
        except urllib.error.URLError as exc:
            last = SourceError(f"network error {exc.reason}", url, None)
            if attempt + 1 < attempts:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise last from exc
    raise last or SourceError(f"request failed {url}", url, None)


class RpcClient:
    """Rotating public Solana JSON-RPC. Failures stay failures."""

    def __init__(self, urls, min_interval=1.25, budget=36):
        self.urls = list(urls)
        self.limiter = Limiter(min_interval)
        self.budget = int(budget)
        self.calls = 0
        self.cache = {}
        self.errors = []
        self.used = []
        self.consecutive_failures = 0
        self.disabled = False

    def call(self, method, params):
        if self.disabled:
            raise SourceError("Solana RPC disabled for the rest of this cycle after repeated failures")
        key = method + ":" + json.dumps(params, sort_keys=True, default=str)
        if key in self.cache:
            return self.cache[key]
        if self.calls >= self.budget:
            raise SourceError(f"Solana RPC budget of {self.budget} calls used; not calling further")
        errs = []
        for attempt in range(len(self.urls)):
            url = self.urls[(self.calls + attempt) % len(self.urls)]
            self.limiter.wait()
            self.calls += 1
            try:
                parsed, _status = http_json(
                    url,
                    {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                    timeout=12,
                    attempts=1,
                    limiter=None,
                )
            except SourceError as exc:
                errs.append(f"{url} {exc}")
                self.consecutive_failures += 1
                if self.consecutive_failures >= 5:
                    self.disabled = True
                    msg = "; ".join(errs)
                    self.errors.append(msg)
                    raise SourceError("Solana RPC failed 5 times in a row; stopped. " + msg) from exc
                continue
            if isinstance(parsed, dict) and parsed.get("error"):
                err = parsed["error"]
                errs.append(f"{url} {err}")
                self.consecutive_failures += 1
                code = err.get("code") if isinstance(err, dict) else None
                if code in (429, -32029) or (isinstance(err, dict) and "429" in str(err.get("message", ""))):
                    time.sleep(2.0)
                if self.consecutive_failures >= 5:
                    self.disabled = True
                    msg = "; ".join(str(e) for e in errs)
                    self.errors.append(msg)
                    raise SourceError("Solana RPC failed 5 times in a row; stopped. " + msg)
                continue
            if not isinstance(parsed, dict) or "result" not in parsed:
                errs.append(f"{url} missing result")
                self.consecutive_failures += 1
                continue
            self.consecutive_failures = 0
            if url not in self.used:
                self.used.append(url)
            self.cache[key] = parsed["result"]
            return parsed["result"]
        msg = "; ".join(str(e) for e in errs) or "no RPC endpoints configured"
        self.errors.append(f"{method}: {msg}")
        raise SourceError(f"{method} failed: {msg}")


def as_list(payload, label):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("pairs", "data", "tokens"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise SourceError(f"{label} returned {type(payload).__name__}, not a list")


def _mint_from_gecko_id(value):
    if not isinstance(value, str) or "_" not in value:
        return ""
    prefix, mint = value.split("_", 1)
    if prefix != "solana":
        return ""
    return mint


def parse_gecko_pools(payload, source_label):
    if not isinstance(payload, dict):
        raise SourceError(f"{source_label} payload was {type(payload).__name__}")
    included = {}
    for item in payload.get("included") or []:
        if isinstance(item, dict) and item.get("id"):
            included[item["id"]] = item
    out = []
    for item in payload.get("data") or []:
        if not isinstance(item, dict):
            continue
        attr = item.get("attributes") or {}
        rel = item.get("relationships") or {}
        base = ((rel.get("base_token") or {}).get("data") or {})
        quote = ((rel.get("quote_token") or {}).get("data") or {})
        mint = _mint_from_gecko_id(base.get("id") or "")
        quote_mint = _mint_from_gecko_id(quote.get("id") or "")
        token = (included.get(base.get("id")) or {}).get("attributes") or {}
        name = token.get("name") or attr.get("name")
        symbol = token.get("symbol")
        if not symbol and isinstance(attr.get("name"), str) and " / " in attr["name"]:
            symbol = attr["name"].split(" / ", 1)[0].strip()
        volume = attr.get("volume_usd") or {}
        out.append({
            "mint": mint,
            "symbol": symbol,
            "name": name,
            "pool": attr.get("address"),
            "created_ts": parse_time(attr.get("pool_created_at")),
            "fdv_usd": num(attr.get("fdv_usd")),
            "market_cap_usd": num(attr.get("market_cap_usd")),
            "liquidity_usd": num(attr.get("reserve_in_usd")),
            "volume_24h_usd": num(volume.get("h24") if isinstance(volume, dict) else None),
            "price_usd": num(attr.get("base_token_price_usd")),
            "quote_mint": quote_mint,
            "metrics_source": source_label,
            "twitter": [],
            "discovered_from": [source_label],
        })
    return out


def parse_ohlcv(payload):
    if not isinstance(payload, dict):
        raise SourceError("OHLCV payload was not an object")
    data = payload.get("data") or {}
    attr = data.get("attributes") or {}
    rows = attr.get("ohlcv_list")
    if not isinstance(rows, list):
        raise SourceError("OHLCV response had no ohlcv_list")
    bars = []
    dropped = 0
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            dropped += 1
            continue
        ts, op, hi, lo, cl = row[:5]
        vol = row[5] if len(row) > 5 else None
        try:
            bar = {
                "t": int(ts),
                "o": float(op),
                "h": float(hi),
                "l": float(lo),
                "c": float(cl),
                "v": float(vol) if vol is not None else 0.0,
            }
        except (TypeError, ValueError):
            dropped += 1
            continue
        if min(bar["o"], bar["h"], bar["l"], bar["c"]) <= 0 or bar["h"] < bar["l"]:
            dropped += 1
            continue
        bars.append(bar)
    bars.sort(key=lambda b: b["t"])
    meta = payload.get("meta") or {}
    base = (meta.get("base") or {}) if isinstance(meta, dict) else {}
    return {
        "bars": bars,
        "dropped": dropped,
        "base_symbol": base.get("symbol"),
        "base_name": base.get("name"),
        "base_address": base.get("address"),
    }


def twitter_links(links):
    found = []
    if not isinstance(links, list):
        return found
    for link in links:
        if not isinstance(link, dict):
            continue
        url = link.get("url") or ""
        kind = (link.get("type") or link.get("label") or "").lower()
        if not isinstance(url, str):
            continue
        hostish = url.lower()
        if kind in {"twitter", "x"} or "twitter.com" in hostish or "x.com" in hostish:
            found.append(url)
    return found


def parse_dex_info_rows(payload):
    """token-boosts and token-profiles rows."""
    rows = as_list(payload, "dexscreener")
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("chainId") not in (None, "solana"):
            continue
        mint = row.get("tokenAddress") or ""
        if not mint:
            continue
        out.append({
            "mint": mint,
            "description": row.get("description") or "",
            "twitter": twitter_links(row.get("links")),
            "url": row.get("url"),
        })
    return out


def parse_dex_pairs(payload):
    rows = payload if isinstance(payload, list) else as_list(payload, "dex pairs")
    out = []
    for pair in rows:
        if not isinstance(pair, dict):
            continue
        if pair.get("chainId") not in (None, "solana"):
            continue
        base = pair.get("baseToken") or {}
        quote = pair.get("quoteToken") or {}
        liq = pair.get("liquidity") or {}
        vol = pair.get("volume") or {}
        out.append({
            "mint": base.get("address") or "",
            "symbol": base.get("symbol"),
            "name": base.get("name"),
            "quote_symbol": quote.get("symbol"),
            "quote_mint": quote.get("address") or "",
            "pool": pair.get("pairAddress"),
            "dex": pair.get("dexId"),
            "price_usd": num(pair.get("priceUsd")),
            "liquidity_usd": num(liq.get("usd") if isinstance(liq, dict) else None),
            "liquidity_base": num(liq.get("base") if isinstance(liq, dict) else None),
            "volume_24h_usd": num(vol.get("h24") if isinstance(vol, dict) else None),
            "market_cap_usd": num(pair.get("marketCap")),
            "fdv_usd": num(pair.get("fdv")),
            "created_ts": parse_time(pair.get("pairCreatedAt")),
            "metrics_source": "dexscreener",
        })
    return out


class MarketData:
    def __init__(self, config, cache_path):
        self.config = config
        self.cache_path = cache_path
        self.gecko = Limiter(config.get("gecko_min_interval_seconds", 2.05))
        self.dex = Limiter(config.get("dex_min_interval_seconds", 0.35))
        self.rpc = RpcClient(
            config.get("rpc_urls") or [],
            config.get("rpc_min_interval_seconds", 1.25),
            (config.get("limits") or {}).get("rpc_budget", 36),
        )
        self.source_status = {}

    def _cache(self):
        try:
            return json.loads(self.cache_path.read_text())
        except Exception:
            return {}

    def _cache_put(self, key, detail, status):
        data = self._cache()
        data[key] = {"time": time.time(), "detail": detail, "status": status}
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(self.cache_path)

    def _cached_negative(self, key):
        hours = float(self.config.get("negative_cache_hours", 6))
        row = self._cache().get(key)
        if not row:
            return None
        if time.time() - float(row.get("time") or 0) > hours * 3600:
            return None
        return row

    def probe_birdeye(self):
        cached = self._cached_negative("birdeye")
        if cached:
            detail = f"Birdeye keyless probe still failing from {datetime.fromtimestamp(cached['time'], timezone.utc).isoformat()}: {cached['detail']}"
            self.source_status["birdeye"] = {"ok": False, "detail": detail}
            return self.source_status["birdeye"]
        url = "https://public-api.birdeye.so/defi/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=5"
        try:
            _parsed, status = http_json(url, attempts=1, timeout=15)
        except SourceError as exc:
            detail = f"Birdeye free endpoint refused a keyless request: {exc}. Not used."
            self._cache_put("birdeye", str(exc), exc.status)
            self.source_status["birdeye"] = {"ok": False, "detail": detail, "status": exc.status}
            return self.source_status["birdeye"]
        detail = f"Birdeye returned HTTP {status} without a key; response ignored because the public API is not a documented keyless source for this floor."
        self.source_status["birdeye"] = {"ok": False, "detail": detail, "status": status}
        return self.source_status["birdeye"]

    def probe_x(self):
        cached = self._cached_negative("x")
        if cached:
            detail = (
                "No free X/Twitter API is reachable. "
                f"Last check {datetime.fromtimestamp(cached['time'], timezone.utc).isoformat()}: {cached['detail']} "
                "Not inventing tweets."
            )
            self.source_status["x_twitter"] = {"ok": False, "detail": detail, "status": cached.get("status")}
            return self.source_status["x_twitter"]
        url = "https://api.twitter.com/2/tweets/search/recent?query=solana&max_results=10"
        try:
            parsed, status = http_json(url, attempts=1, timeout=15)
        except SourceError as exc:
            detail = f"No free X/Twitter API is reachable (HTTP {exc.status}). Not inventing tweets."
            self._cache_put("x", str(exc), exc.status)
            self.source_status["x_twitter"] = {"ok": False, "detail": detail, "status": exc.status}
            return self.source_status["x_twitter"]
        tweets = []
        if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
            tweets = [row.get("text") for row in parsed["data"] if isinstance(row, dict) and row.get("text")]
        if tweets:
            self.source_status["x_twitter"] = {"ok": True, "detail": f"X API returned {len(tweets)} tweets.", "tweets": tweets}
        else:
            detail = f"X API HTTP {status} did not include tweet text. Not inventing tweets."
            self.source_status["x_twitter"] = {"ok": False, "detail": detail, "status": status}
        return self.source_status["x_twitter"]

    def dexscreener_lists(self):
        urls = {
            "boosts_latest": "https://api.dexscreener.com/token-boosts/latest/v1",
            "boosts_top": "https://api.dexscreener.com/token-boosts/top/v1",
            "profiles_latest": "https://api.dexscreener.com/token-profiles/latest/v1",
        }
        rows = []
        errors = []
        counts = {}
        for name, url in urls.items():
            try:
                payload, _status = http_json(url, limiter=self.dex, timeout=20)
                parsed = parse_dex_info_rows(payload)
                counts[name] = len(parsed)
                for row in parsed:
                    row["list"] = name
                    rows.append(row)
            except SourceError as exc:
                errors.append(f"{name}: {exc}")
                counts[name] = 0
        ok = any(counts.values())
        self.source_status["dexscreener_lists"] = {
            "ok": ok,
            "detail": "token-boosts latest/top and token-profiles latest",
            "counts": counts,
            "errors": errors,
        }
        return rows, errors

    def dexscreener_pairs(self, mints):
        found = []
        errors = []
        chunk = 30
        for i in range(0, len(mints), chunk):
            part = mints[i:i + chunk]
            url = "https://api.dexscreener.com/tokens/v1/solana/" + ",".join(part)
            try:
                payload, _status = http_json(url, limiter=self.dex, timeout=25)
                found.extend(parse_dex_pairs(payload))
            except SourceError as exc:
                errors.append(str(exc))
        self.source_status["dexscreener_pairs"] = {
            "ok": bool(found),
            "detail": f"{len(found)} pairs from tokens/v1" + (("; " + "; ".join(errors)) if errors else ""),
            "pairs": len(found),
            "errors": errors,
        }
        return found, errors

    def gecko_pools(self, kind):
        url = f"https://api.geckoterminal.com/api/v2/networks/solana/{kind}?page=1&include=base_token,quote_token"
        payload, _status = http_json(url, limiter=self.gecko, timeout=25)
        label = f"geckoterminal:{kind}"
        return parse_gecko_pools(payload, label)

    def gecko_ohlcv(self, pool, timeframe, limit):
        url = (
            f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool}"
            f"/ohlcv/{timeframe}?aggregate=1&limit={int(limit)}&currency=usd"
        )
        payload, _status = http_json(url, limiter=self.gecko, timeout=25)
        parsed = parse_ohlcv(payload)
        parsed["url"] = url
        parsed["timeframe"] = timeframe
        return parsed
