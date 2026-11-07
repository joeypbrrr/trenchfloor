"""Read-only discovery adapters. No wallet, signing, cookies, or browser bypass.

GMGN's unauthenticated website is blocked from this box. `gmgn_substitute`
uses GeckoTerminal explicitly, never impersonates GMGN. An optional API key
is read ONLY from GMGN_API_KEY, never persisted or printed.
"""
import os
import time
import uuid
from urllib.parse import urlencode

from sources import SourceError, http_json, num, parse_time


def gmgn_request(route, payload=None, **query):
    key = os.environ.get('GMGN_API_KEY')
    if not key:
        raise SourceError('GMGN adapter off: GMGN_API_KEY is not configured; no website requests attempted')
    if route not in ('/v1/market/rank', '/v1/trenches'):
        raise ValueError('Only read-only discovery routes are allowed')
    query.update(timestamp=int(time.time()), client_id=str(uuid.uuid4()))
    # GMGN CLI 1.7.1's documented key-only authentication. No signing key.
    url = 'https://openapi.gmgn.ai' + route + '?' + urlencode(query)
    try:
        data, _ = http_json(url, payload, headers={'X-APIKEY': key}, attempts=1, timeout=15)
    except SourceError as exc:
        # Do not expose response bodies or auth values in the feed.
        raise SourceError(f'GMGN read-only API unavailable (HTTP {exc.status}); no retries/bypass', status=exc.status) from None
    if not isinstance(data, dict) or data.get('code') not in (None, 0, 200):
        raise SourceError('GMGN API returned an error; no retries')
    return data.get('data') or {}


def parse_gmgn(rows, label):
    out = []
    for row in rows:
        if not isinstance(row, dict) or not row.get('address'):
            continue
        out.append({
            'mint': row['address'], 'symbol': row.get('symbol'), 'name': row.get('name'),
            'price_usd': num(row.get('price')),
            'market_cap_usd': num(row.get('market_cap', row.get('usd_market_cap'))),
            'liquidity_usd': num(row.get('liquidity')),
            'volume_24h_usd': num(row.get('volume_24h', row.get('volume'))),
            'created_ts': parse_time(row.get('creation_timestamp', row.get('created_timestamp'))),
            'metrics_source': label, 'discovered_from': [label], 'twitter': [],
            'is_wash_trading': row.get('is_wash_trading'),
            # gas_fee is average gas/transaction, NOT total/global fees. Units
            # of raw total_fee aren't specified consistently in free docs.
            # Never reinterpret either as verified lifetime SOL global fees.
            'global_fees_sol': None, 'global_fees_basis': 'unavailable: verified cumulative SOL fees not exposed',
        })
    return out


def candidates(market, config):
    source = config.get('candidate_source', 'legacy')
    if source == 'pumpportal':
        from pumpportal_source import candidates as pump_candidates
        return pump_candidates(market, config)
    report = {'source': source, 'discovered': 0, 'enriched': 0, 'skipped_rejected': 0, 'errors': []}
    if source == 'gmgn':
        rank = gmgn_request('/v1/market/rank', chain='sol', interval='24h', limit=50, order_by='volume', direction='desc')
        time.sleep(1)  # below Free plan's documented weighted request bucket
        new = gmgn_request('/v1/trenches', {'version': 'v2', 'new_creation': {'filters': ['offchain', 'onchain'], 'launchpad_platform_v2': True, 'limit': 50}}, chain='sol')
        rows = parse_gmgn(rank.get('rank') or [], 'gmgn:trending')
        rows += parse_gmgn(new.get('new_creation') or [], 'gmgn:new_creation')
        # GMGN's rank lacks pool/quote identifiers: DexScreener is enrichment
        # only, never a candidate list or paid-boost discovery source here.
        pairs, errors = market.dexscreener_pairs([r['mint'] for r in rows])
        report['errors'] += errors
        by_mint = {}
        for pair in pairs:
            if (pair.get('liquidity_usd') or 0) > (by_mint.get(pair['mint'], {}).get('liquidity_usd') or -1):
                by_mint[pair['mint']] = pair
        for row in rows:
            for k in ('pool', 'quote_mint', 'quote_symbol', 'liquidity_base', 'dex'):
                row[k] = by_mint.get(row['mint'], {}).get(k)
        report['label'] = 'GMGN authenticated read-only API (untested without a key)'
    elif source == 'gmgn_substitute':
        rows = []
        for kind in ('trending_pools', 'new_pools'):
            try:
                rows.extend(market.gecko_pools(kind))
            except SourceError as exc:
                report['errors'].append(f'{kind}: {exc}')
        report['label'] = 'GMGN substitute: GeckoTerminal trending + new Solana pools (not GMGN data)'
    else:
        raise SourceError(f'Unknown candidate_source: {source}')
    unique = {}
    for row in rows:
        if row.get('mint') and ((row.get('liquidity_usd') or 0) > (unique.get(row['mint'], {}).get('liquidity_usd') or -1)):
            unique[row['mint']] = row
    rows = sorted(unique.values(), key=lambda r: r.get('volume_24h_usd') or 0, reverse=True)
    report['discovered'] = len(rows)
    rows = rows[:int(config.get('limits', {}).get('enrich_mints', 30))]
    report['enriched'] = len(rows)
    for row in rows:
        row.setdefault('global_fees_sol', None)
        row.setdefault('global_fees_basis', 'unknown; GeckoTerminal does not report global SOL fees')
        row['fees_proxy_sol'] = None
    if config.get('fee_proxy_enabled', False) and rows:
        # EXPERIMENT ONLY: assumed 30bps DEX fees on reported 24h USD volume,
        # converted using a fresh SOL quote. Not lifetime network/global fees,
        # not proof of organic volume. Never silently replace actual fees.
        try:
            from sources import SOL_MINT
            payload, _ = http_json('https://api.geckoterminal.com/api/v2/simple/networks/solana/token_price/' + SOL_MINT,
                                   limiter=market.gecko, attempts=1, timeout=15)
            sol_usd = num((payload.get('data', {}).get('attributes', {}).get('token_prices') or {}).get(SOL_MINT))
            if sol_usd and sol_usd > 0:
                for row in rows:
                    vol = num(row.get('volume_24h_usd'))
                    if vol is not None:
                        row['fees_proxy_sol'] = vol * 0.003 / sol_usd
                        row['fees_proxy_basis'] = 'PROXY ONLY: reported 24h volume × assumed 0.3% DEX fee / fresh SOL USD; NOT global fees or real-volume proof'
        except SourceError as exc:
            report['errors'].append('Fee proxy SOL quote unavailable: ' + str(exc))
    market.source_status['candidate_source'] = {'ok': bool(rows), **report}
    return rows, report


def fee_filter_reason(cand, config):
    if cand.get('is_wash_trading') is True:
        return 'wash trading flagged'
    fee = num(cand.get('global_fees_sol'))
    if fee is None:
        if config.get('candidate_source') == 'pumpportal':
            return 'PumpPortal global fees unknown: complete trade coverage unavailable (no proxy allowed)'
        if not config.get('fee_proxy_enabled', False):
            return 'global fees unknown (strict fail closed)'
        fee = num(cand.get('fees_proxy_sol'))
        if fee is None:
            return 'fee proxy unavailable (fail closed)'
        cand['fee_filter_basis'] = cand.get('fees_proxy_basis') or 'PROXY ONLY'
    else:
        cand['fee_filter_basis'] = 'verified cumulative global fees in SOL'
    if fee < float(config.get('new_source_min_global_fees_sol', 1.5)):
        return 'global fees or explicit proxy below 1.5 SOL'
    return None
