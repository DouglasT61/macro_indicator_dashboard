from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx


YAHOO_CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
GDELT_DOC_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'
GOOGLE_NEWS_RSS_URL = 'https://news.google.com/rss/search'
FED_RSS_URLS = [
    'https://www.federalreserve.gov/feeds/press_monetary.xml',
    'https://www.federalreserve.gov/feeds/clp.xml',
    'https://www.federalreserve.gov/feeds/h41.xml',
]
USER_AGENT = 'Mozilla/5.0 macro-stress-dashboard/0.1'
GEO_REQUIRED_TERMS = ('shipping', 'tanker', 'maritime', 'oil', 'hormuz', 'red sea', 'bab el-mandeb', 'gulf of aden')
GOV_REQUIRED_TERMS = ('irgc', 'revolutionary guard', 'provincial', 'governor', 'commander', 'central command', 'tehran')
INTERCEPTOR_REQUIRED_TERMS = ('interceptor', 'intercepted', 'missile defense', 'ballistic', 'uav', 'drone', 'houthi', 'red sea', 'barrage')
PNI_SEED_URLS = [
    'https://www.ukpandi.com/news-and-resources/circulars/',
    'https://www.japanpandi.or.jp/en/member/circulars/',
    'https://www.swedishclub.com/loss-prevention/maritime-security/',
]
PNI_ALLOWED_DOMAINS = (
    'ukpandi.com',
    'japanpandi.or.jp',
    'swedishclub.com',
)
PNI_GENERIC_PAGE_TERMS = (
    'circulars |',
    'news and resources',
    'uk p&i - circulars',
    'member circulars',
    'member/circulars',
    'maritime security',
    'loss prevention',
)
PNI_REQUIRED_TERMS = (
    'notice of cancellation',
    'war notice',
    'listed area',
    'additional premium',
    'case-by-case',
    'write back',
    'persian gulf',
    'arabian gulf',
    'hormuz',
    'red sea',
    'war risk',
    'war risks',
    'reinstatement',
)
IAEA_SEED_URLS = [
    'https://www.iaea.org/newscenter/focus/iran',
    'https://www.iaea.org/newscenter',
]
CENTCOM_SEED_URLS = [
    'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
]


@dataclass(slots=True)
class OverlayAssessment:
    key: str
    value: float
    source: str
    notes: str


@dataclass(slots=True)
class PriceSnapshot:
    symbol: str
    latest: float
    previous: float
    trailing_max: float


@dataclass(slots=True)
class ArticleSignal:
    title: str
    url: str
    score: float
    date: str | None = None


def _parse_isoish_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _strip_html(value: str) -> str:
    without_scripts = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', value, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', without_scripts)
    return re.sub(r'\s+', ' ', text).strip()


def _extract_title(html: str) -> str:
    match = re.search(r'<title>(.*?)</title>', html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ''
    return re.sub(r'\s+', ' ', match.group(1)).strip()


def _extract_article_date(text: str) -> str | None:
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}', text)
    return match.group(0) if match else None


def _same_domain(url: str, domain: str | tuple[str, ...]) -> bool:
    netloc = urlparse(url).netloc
    if isinstance(domain, tuple):
        return any(netloc.endswith(candidate) for candidate in domain)
    return netloc.endswith(domain)


def _extract_links(
    html: str,
    source_url: str,
    domain: str | tuple[str, ...],
    url_terms: tuple[str, ...],
    limit: int = 16,
) -> list[str]:
    matches = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    seen: set[str] = set()
    results: list[str] = []
    for raw in matches:
        absolute = urljoin(source_url, raw).split('#', 1)[0]
        if not _same_domain(absolute, domain):
            continue
        lowered = absolute.lower()
        if url_terms and not any(term in lowered for term in url_terms):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        results.append(absolute)
        if len(results) >= limit:
            break
    return results


def _score_terms(text: str, weights: dict[str, float]) -> float:
    lowered = text.lower()
    return sum(weight for term, weight in weights.items() if term in lowered)


def _fetch_yahoo_snapshot(client: httpx.Client, symbol: str, lookback_days: int = 120) -> PriceSnapshot:
    period2 = int(datetime.now(UTC).timestamp())
    period1 = int((datetime.now(UTC) - timedelta(days=lookback_days)).timestamp())
    response = client.get(
        YAHOO_CHART_URL.format(symbol=symbol),
        params={'period1': period1, 'period2': period2, 'interval': '1d', 'includePrePost': 'false'},
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get('chart', {}).get('result') or []
    if not result:
        raise ValueError(f'No chart data returned for {symbol}')
    quote = (result[0].get('indicators', {}).get('quote') or [{}])[0]
    closes = [float(item) for item in (quote.get('close') or []) if item is not None]
    if len(closes) < 3:
        raise ValueError(f'Insufficient chart data for {symbol}')
    return PriceSnapshot(symbol=symbol, latest=closes[-1], previous=closes[-2], trailing_max=max(closes))


def collect_private_credit_stress(timeout_seconds: float = 20.0) -> OverlayAssessment:
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        bizd = _fetch_yahoo_snapshot(client, 'BIZD')
        bkln = _fetch_yahoo_snapshot(client, 'BKLN')
        hyg = _fetch_yahoo_snapshot(client, 'HYG')

    def drawdown(snapshot: PriceSnapshot) -> float:
        if snapshot.trailing_max <= 0:
            return 0.0
        return max(0.0, (snapshot.trailing_max - snapshot.latest) / snapshot.trailing_max)

    bizd_drawdown = drawdown(bizd)
    bkln_drawdown = drawdown(bkln)
    hyg_drawdown = drawdown(hyg)
    bizd_momentum = max(0.0, (bizd.previous - bizd.latest) / max(bizd.previous, 0.01))
    bkln_momentum = max(0.0, (bkln.previous - bkln.latest) / max(bkln.previous, 0.01))
    hyg_momentum = max(0.0, (hyg.previous - hyg.latest) / max(hyg.previous, 0.01))

    score = 30.0
    score += min(30.0, bizd_drawdown * 240.0)
    score += min(20.0, bkln_drawdown * 250.0)
    score += min(12.0, hyg_drawdown * 200.0)
    score += min(5.0, bizd_momentum * 500.0)
    score += min(3.0, bkln_momentum * 350.0)
    score += min(3.0, hyg_momentum * 350.0)
    score = max(10.0, min(90.0, score))

    highlights = [
        f'BIZD drawdown {bizd_drawdown * 100.0:.1f}%',
        f'BKLN drawdown {bkln_drawdown * 100.0:.1f}%',
        f'HYG drawdown {hyg_drawdown * 100.0:.1f}%',
    ]
    notes = (
        'Auto-scored from public private-credit market composite; '
        f'source=Yahoo market proxy basket; checked={datetime.now(UTC).isoformat()}; '
        'components=' + ' | '.join(highlights)
    )
    return OverlayAssessment(
        key='private_credit_stress',
        value=round(score, 2),
        source='market/yahoo-private-credit-proxy',
        notes=notes,
    )


def _extract_article_titles(payload: dict[str, object]) -> list[str]:
    raw_articles = payload.get('articles')
    if not isinstance(raw_articles, list):
        return []
    titles: list[str] = []
    for article in raw_articles:
        if not isinstance(article, dict):
            continue
        title = article.get('title')
        if isinstance(title, str) and title.strip():
            titles.append(re.sub(r'\s+', ' ', title).strip())
    return titles


def _parse_rss_items(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        pub_date = (item.findtext('pubDate') or '').strip()
        description = (item.findtext('description') or '').strip()
        if title:
            items.append({'title': title, 'pub_date': pub_date, 'description': description})
    return items


def _fetch_google_news_titles(client: httpx.Client, query: str) -> list[str]:
    response = client.get(
        GOOGLE_NEWS_RSS_URL,
        params={
            'q': query,
            'hl': 'en-US',
            'gl': 'US',
            'ceid': 'US:en',
        },
    )
    response.raise_for_status()
    items = _parse_rss_items(response.text)
    titles: list[str] = []
    for item in items:
        title = re.sub(r'\s+-\s+[^-]+$', '', item['title']).strip()
        if title:
            titles.append(title)
    return titles


def _filter_titles(titles: list[str], required_terms: tuple[str, ...]) -> list[str]:
    filtered: list[str] = []
    seen: set[str] = set()
    for title in titles:
        lowered = title.lower()
        ascii_share = sum(1 for char in title if ord(char) < 128) / max(len(title), 1)
        if ascii_share < 0.65:
            continue
        if not any(term in lowered for term in required_terms):
            continue
        normalized = re.sub(r'\s+', ' ', title).strip()
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        filtered.append(normalized)
    return filtered


def _filter_geopolitical_titles(titles: list[str]) -> list[str]:
    return _filter_titles(titles, GEO_REQUIRED_TERMS)


def _collect_gdelt_titles(client: httpx.Client, query: str, timespan: str = '7days', maxrecords: int = 25) -> list[str]:
    response = client.get(
        GDELT_DOC_URL,
        params={
            'query': query,
            'mode': 'ArtList',
            'format': 'json',
            'maxrecords': maxrecords,
            'sort': 'DateDesc',
            'timespan': timespan,
        },
    )
    response.raise_for_status()
    return _extract_article_titles(response.json())


def collect_geopolitical_escalation_signal(timeout_seconds: float = 20.0) -> OverlayAssessment:
    query = (
        '("Strait of Hormuz" OR "Bab el-Mandeb" OR "Red Sea" OR "Gulf of Aden") '
        '(shipping OR tanker OR maritime OR oil) '
        '(attack OR strike OR missile OR closure OR disruption OR sanctions)'
    )
    titles: list[str] = []
    source = 'news/gdelt-shipping-escalation'
    source_label = 'GDELT shipping escalation query'

    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        try:
            titles = _collect_gdelt_titles(client, query)
        except httpx.HTTPError:
            titles = []

        if not titles:
            titles = _fetch_google_news_titles(client, 'Red Sea OR Hormuz shipping tanker attack oil')
            source = 'news/google-shipping-escalation'
            source_label = 'Google News shipping escalation query'

    titles = _filter_geopolitical_titles(titles)

    keyword_hits = 0.0
    for title in titles:
        lowered = title.lower()
        for term, weight in {
            'hormuz': 2.5,
            'red sea': 2.0,
            'bab el-mandeb': 2.0,
            'attack': 1.75,
            'missile': 1.75,
            'strike': 1.5,
            'closure': 2.25,
            'sanction': 1.25,
            'shipping': 1.25,
            'tanker': 1.5,
            'oil': 1.0,
        }.items():
            if term in lowered:
                keyword_hits += weight

    article_count = len(titles)
    signal = min(100.0, article_count * 6.0 + keyword_hits * 2.5)
    toggle = 1.0 if signal >= 35.0 or article_count >= 4 else 0.0
    notes = (
        'Auto-scored from public geopolitical news scan; '
        f'source={source_label}; checked={datetime.now(UTC).isoformat()}; '
        f'articles={article_count}; signal={signal:.1f}; highlights=' + ' | '.join(titles[:3])
    )
    return OverlayAssessment(
        key='geopolitical_escalation_toggle',
        value=toggle,
        source=source,
        notes=notes,
    )


def collect_central_bank_intervention_signal(timeout_seconds: float = 20.0) -> OverlayAssessment:
    keywords = {
        'swap': 2.5,
        'liquidity': 2.0,
        'repo': 2.25,
        'market functioning': 3.0,
        'temporary open market': 2.0,
        'standing repo': 1.75,
        'fima': 2.75,
        'dollar funding': 2.75,
        'balance sheet': 1.5,
        'backstop': 2.0,
    }
    matches: list[str] = []
    weighted_hits = 0.0
    recent_count = 0
    cutoff = datetime.now(UTC) - timedelta(days=30)

    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        for url in FED_RSS_URLS:
            try:
                response = client.get(url)
                response.raise_for_status()
            except Exception:
                # Individual feed failure is non-fatal; continue with any
                # articles already collected from other Fed RSS URLs.
                continue
            for item in _parse_rss_items(response.text):
                published = _parse_isoish_datetime(item['pub_date'])
                if published is None or published < cutoff:
                    continue
                haystack = f"{item['title']} {item['description']}".lower()
                score = sum(weight for term, weight in keywords.items() if term in haystack)
                if score <= 0:
                    continue
                weighted_hits += score
                recent_count += 1
                matches.append(item['title'])

    toggle = 1.0 if weighted_hits >= 4.0 and recent_count >= 1 else 0.0
    notes = (
        'Auto-scored from official central-bank feeds; '
        f'source=Federal Reserve RSS; checked={datetime.now(UTC).isoformat()}; '
        f'articles={recent_count}; signal={weighted_hits:.1f}; highlights=' + ' | '.join(matches[:3])
    )
    return OverlayAssessment(
        key='central_bank_intervention_toggle',
        value=toggle,
        source='fed/rss-intervention-scan',
        notes=notes,
    )


def _collect_site_signals(
    client: httpx.Client,
    *,
    seed_urls: list[str],
    domain: str | tuple[str, ...],
    url_terms: tuple[str, ...],
    score_terms: dict[str, float],
    limit: int = 10,
    signal_filter: Callable[[str, str, str], bool] | None = None,
) -> list[ArticleSignal]:
    candidates: list[str] = []
    seen: set[str] = set()
    for seed_url in seed_urls:
        try:
            response = client.get(seed_url)
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        if seed_url not in seen:
            candidates.append(seed_url)
            seen.add(seed_url)
        for link in _extract_links(response.text, seed_url, domain, url_terms, limit=limit):
            if link not in seen:
                candidates.append(link)
                seen.add(link)
    signals: list[ArticleSignal] = []
    for url in candidates[:limit]:
        try:
            response = client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        title = _extract_title(response.text) or url
        text = _strip_html(response.text)
        if signal_filter and not signal_filter(title, url, text):
            continue
        combined = f'{title} {text}'
        score = _score_terms(combined, score_terms)
        if score <= 0:
            continue
        signals.append(ArticleSignal(title=re.sub(r'\s+', ' ', title).strip(), url=url, score=score, date=_extract_article_date(text)))
    return sorted(signals, key=lambda item: item.score, reverse=True)



def _is_pni_notice_candidate(title: str, url: str, text: str) -> bool:
    title_lower = re.sub(r'\s+', ' ', title).strip().lower()
    url_lower = url.lower()
    combined = f'{title_lower} {url_lower} {text.lower()}'

    if any(term in title_lower for term in PNI_GENERIC_PAGE_TERMS):
        return False
    if any(url_lower.rstrip('/').endswith(suffix) for suffix in ('/circulars', '/member/circulars', '/maritime-security')):
        return False

    matched_required = sum(1 for term in PNI_REQUIRED_TERMS if term in combined)
    if matched_required == 0:
        return False

    structural_terms = (
        'iran',
        'gulf',
        'hormuz',
        'red sea',
        'yemen',
        'underwriters',
        'cancellation',
        'reinstatement',
        'premium',
    )
    matched_structural = sum(1 for term in structural_terms if term in combined)
    return matched_required >= 2 or matched_structural >= 3



def _weighted_overlay_score(
    signals: list[ArticleSignal],
    *,
    base: float,
    weights: tuple[float, ...],
    article_weight: float,
    floor: float,
    ceiling: float,
) -> float:
    if not signals:
        return floor
    weighted_sum = 0.0
    for index, signal in enumerate(signals[: len(weights)]):
        weighted_sum += signal.score * weights[index]
    weighted_sum += min(len(signals), 6) * article_weight
    return max(floor, min(ceiling, base + weighted_sum))


def _weighted_title_score(
    titles: list[str],
    weights: dict[str, float],
    *,
    base: float,
    per_title: float,
    term_scale: float,
    floor: float,
    ceiling: float,
) -> float:
    term_total = sum(_score_terms(title, weights) for title in titles)
    score = base + min(len(titles), 6) * per_title + term_total * term_scale
    return max(floor, min(ceiling, score))

def _format_overlay_notes(label: str, source_label: str, key: str, signals: list[ArticleSignal], score: float) -> str:
    highlights = ' | '.join(
        f"{signal.title}{f' ({signal.date})' if signal.date else ''}" for signal in signals[:3]
    )
    return (
        f'Auto-scored from {label}; '
        f'source={source_label}; checked={datetime.now(UTC).isoformat()}; '
        f'articles={len(signals)}; signal={score:.1f}; highlights={highlights}'
    )


def collect_p_and_i_circular_stress(timeout_seconds: float = 20.0) -> OverlayAssessment:
    score_terms = {
        'war risk': 8.0,
        'notice of cancellation': 12.0,
        'cancellation': 7.0,
        'reinstatement': -2.5,
        'additional premium': 7.0,
        'listed area': 6.0,
        'iran': 8.0,
        'persian gulf': 8.0,
        'arabian gulf': 7.0,
        'hormuz': 8.0,
        'red sea': 7.0,
        'yemen': 5.0,
        'underwriters': 3.0,
        'case-by-case': 4.0,
        'write back': 5.0,
        'war notice': 8.0,
    }
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        signals = _collect_site_signals(
            client,
            seed_urls=PNI_SEED_URLS,
            domain=PNI_ALLOWED_DOMAINS,
            url_terms=('war', 'risk', 'iran', 'gulf', 'hormuz', 'red-sea', 'notice', 'cancellation', 'premium', 'listed', 'reinstatement'),
            score_terms=score_terms,
            limit=12,
            signal_filter=_is_pni_notice_candidate,
        )
    signal_value = _weighted_overlay_score(
        signals,
        base=14.0,
        weights=(0.44, 0.3, 0.2, 0.12),
        article_weight=1.4,
        floor=8.0,
        ceiling=74.0,
    )
    notes = _format_overlay_notes('official P&I circular scan', 'Official P&I circulars', 'p_and_i_circular_stress', signals, signal_value)
    return OverlayAssessment('p_and_i_circular_stress', round(max(10.0, signal_value), 2), 'insurance/official-pni-scan', notes)


def collect_iaea_nuclear_ambiguity(timeout_seconds: float = 20.0) -> OverlayAssessment:
    score_terms = {
        'iran': 3.0,
        'verification': 7.0,
        'verify': 6.0,
        'safeguards': 7.0,
        'not in a position': 10.0,
        'not able to verify': 10.0,
        'unresolved': 6.0,
        '60%': 6.0,
        'highly enriched': 7.0,
        'uranium': 4.0,
        'stockpile': 5.0,
        'access': 5.0,
        'inspectors': 5.0,
        'monitoring': 4.0,
        'continuity of knowledge': 8.0,
        'diversion': 6.0,
    }
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        signals = _collect_site_signals(
            client,
            seed_urls=IAEA_SEED_URLS,
            domain='iaea.org',
            url_terms=('iran', 'board', 'safeguards', 'verification', 'uranium', 'monitoring'),
            score_terms=score_terms,
            limit=10,
        )
    signal_value = _weighted_overlay_score(signals, base=16.0, weights=(0.5, 0.35, 0.22, 0.14), article_weight=1.6, floor=8.0, ceiling=78.0)
    notes = _format_overlay_notes('official IAEA Iran scan', 'Official IAEA Iran monitoring pages', 'iaea_nuclear_ambiguity', signals, signal_value)
    return OverlayAssessment('iaea_nuclear_ambiguity', round(max(8.0, signal_value), 2), 'iaea/iran-verification-scan', notes)


def collect_interceptor_depletion_signal(timeout_seconds: float = 20.0) -> OverlayAssessment:
    official_signals: list[ArticleSignal] = []
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        try:
            official_signals = _collect_site_signals(
                client,
                seed_urls=CENTCOM_SEED_URLS,
                domain='centcom.mil',
                url_terms=('red-sea', 'rollup', 'houthi', 'missile', 'drone', 'uav', 'attack'),
                score_terms={
                    'intercept': 8.0,
                    'interceptor': 9.0,
                    'destroyed': 5.0,
                    'missile': 5.0,
                    'uav': 4.0,
                    'drone': 4.0,
                    'red sea': 4.0,
                    'ballistic': 6.0,
                    'houthi': 4.0,
                    'multiple': 3.0,
                    'overnight': 3.0,
                },
                limit=8,
            )
        except Exception:
            official_signals = []
        if official_signals:
            signal_value = _weighted_overlay_score(official_signals, base=14.0, weights=(0.45, 0.3, 0.2, 0.12), article_weight=1.8, floor=8.0, ceiling=76.0)
            notes = _format_overlay_notes('official operational depletion scan', 'CENTCOM operational updates', 'interceptor_depletion', official_signals, signal_value)
            return OverlayAssessment('interceptor_depletion', round(max(8.0, signal_value), 2), 'defense/centcom-operational-scan', notes)

        titles: list[str] = []
        source = 'news/gdelt-interceptor-depletion'
        source_label = 'GDELT interceptor depletion query'
        try:
            titles = _collect_gdelt_titles(
                client,
                '(interceptor OR interceptors OR interception OR missile defense OR ballistic OR drone barrage) (Iran OR Israel OR Red Sea OR Houthi)',
                timespan='7days',
                maxrecords=25,
            )
        except httpx.HTTPError:
            titles = []
        if not titles:
            titles = _fetch_google_news_titles(client, 'interceptors OR interception OR missile defense Iran Israel Red Sea')
            source = 'news/google-interceptor-depletion'
            source_label = 'Google News interceptor depletion query'

    filtered = _filter_titles(titles, INTERCEPTOR_REQUIRED_TERMS)
    weights = {
        'interceptor': 3.0,
        'intercepted': 3.0,
        'missile defense': 3.0,
        'ballistic': 2.0,
        'drone': 1.75,
        'uav': 1.75,
        'barrage': 2.5,
        'red sea': 1.5,
        'houthi': 1.5,
    }
    signal_value = _weighted_title_score(filtered, weights, base=12.0, per_title=3.0, term_scale=1.1, floor=6.0, ceiling=70.0)
    notes = (
        'Auto-scored from public operational depletion scan; '
        f'source={source_label}; checked={datetime.now(UTC).isoformat()}; '
        f'articles={len(filtered)}; signal={signal_value:.1f}; highlights=' + ' | '.join(filtered[:3])
    )
    return OverlayAssessment('interceptor_depletion', round(max(6.0, signal_value), 2), source, notes)


def collect_governance_fragmentation_signal(timeout_seconds: float = 20.0) -> OverlayAssessment:
    query = (
        '(IRGC OR "Revolutionary Guard" OR provincial OR governor OR commander OR "central command") '
        '(contradict OR defy OR rival OR split OR fragmented OR local OR province OR faction) '
        '(Iran OR Tehran)'
    )
    titles: list[str] = []
    source = 'news/gdelt-governance-fragmentation'
    source_label = 'GDELT governance fragmentation query'
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        try:
            titles = _collect_gdelt_titles(client, query, timespan='14days', maxrecords=25)
        except httpx.HTTPError:
            titles = []
        if not titles:
            titles = _fetch_google_news_titles(client, 'IRGC provincial commander contradict Tehran governor fragmentation Iran')
            source = 'news/google-governance-fragmentation'
            source_label = 'Google News governance fragmentation query'

    filtered = _filter_titles(titles, GOV_REQUIRED_TERMS)
    weights = {
        'irgc': 2.0,
        'revolutionary guard': 2.0,
        'provincial': 1.75,
        'governor': 1.5,
        'commander': 1.5,
        'central command': 2.5,
        'contradict': 3.0,
        'defy': 2.5,
        'split': 2.5,
        'fragment': 2.5,
        'rival': 2.0,
        'local': 1.0,
    }
    signal_value = _weighted_title_score(filtered, weights, base=8.0, per_title=2.4, term_scale=0.85, floor=4.0, ceiling=58.0)
    notes = (
        'Auto-scored from governance fragmentation scan; '
        f'source={source_label}; checked={datetime.now(UTC).isoformat()}; '
        f'articles={len(filtered)}; signal={signal_value:.1f}; highlights=' + ' | '.join(filtered[:3])
    )
    return OverlayAssessment('governance_fragmentation', round(max(6.0, signal_value), 2), source, notes)
