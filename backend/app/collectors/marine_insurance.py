from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urljoin, urlparse

import httpx


BEINSURE_BASE_URL = 'https://beinsure.com'
SEC_COMPANY_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik}.json'
SEC_ARCHIVES_URL = 'https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession}/{document}'
USER_AGENT = 'Mozilla/5.0 macro-stress-dashboard/0.1'
MAX_CANDIDATES = 24
MAX_ARTICLES = 8
MAX_SEC_FILINGS = 16
SEC_FORMS = {'8-K', '6-K', '10-Q', '10-K', '20-F', '40-F'}
SEC_WATCHLIST = [
    ('FRO', 'Frontline'),
    ('STNG', 'Scorpio Tankers'),
    ('TNK', 'Teekay Tankers'),
    ('INSW', 'International Seaways'),
    ('DHT', 'DHT Holdings'),
    ('ZIM', 'ZIM Integrated Shipping'),
    ('ACGL', 'Arch Capital'),
    ('RNR', 'RenaissanceRe'),
    ('WRB', 'W. R. Berkley'),
    ('AJG', 'Arthur J. Gallagher'),
]
SEC_KEYWORD_WEIGHTS = {
    'red sea': 10.0,
    'bab el mandeb': 10.0,
    'strait of hormuz': 12.0,
    'war risk': 10.0,
    'marine insurance': 8.0,
    'rerouting': 7.0,
    'rerouted': 7.0,
    'shipping disruption': 7.0,
    'transit disruption': 7.0,
    'insurance premium': 8.0,
    'premiums increased': 7.0,
    'premium increases': 7.0,
    'listed area': 6.0,
    'middle east': 5.0,
    'suez canal': 6.0,
    'gulf of aden': 7.0,
    'security incident': 6.0,
    'hostilities': 6.0,
}
SEC_NEGATIVE_WEIGHTS = {
    'no material impact': 10.0,
    'not material': 8.0,
    'immaterial': 8.0,
    'no significant impact': 8.0,
}
SEED_URLS = [
    'https://beinsure.com/news/',
    'https://beinsure.com/faq_category/marine-insurance/',
    'https://beinsure.com/marine-insurance-face-soft-market/',
]
STRONG_URL_TERMS = {
    'marine-insurance': 8.0,
    'war-risk': 9.0,
    'shipping-insurance': 8.0,
    'tanker': 7.0,
    'red-sea': 8.0,
    'hormuz': 8.0,
    'gulf-war': 8.0,
    'reinsurance': 5.0,
}
STRONG_TEXT_TERMS = {
    'marine insurance': 7.0,
    'war risk': 8.0,
    'shipping insurance': 7.0,
    'tanker': 6.0,
    'hull war': 7.0,
    'red sea': 7.0,
    'strait of hormuz': 9.0,
    'political risk cover': 7.0,
    'marine hull': 6.0,
}
GENERIC_PENALTY_TERMS = {
    'europe insurance news': 12.0,
    'latest us insurance news': 12.0,
    'rates, laws': 10.0,
    'market updates': 8.0,
    'global insurance industry': 9.0,
    'insurance news': 8.0,
}
STRESS_TERMS = {
    'war risk': 8.0,
    'war volatility': 7.0,
    'armed attacks': 7.0,
    'red sea': 6.0,
    'ukraine': 4.0,
    'piracy': 5.0,
    'rising claims': 6.0,
    'premiums climb': 5.0,
    'premiums rose': 5.0,
    'longer, riskier routes': 7.0,
    'riskier routes': 6.0,
    'fractured trade flows': 5.0,
    'geopolitical shocks': 6.0,
    'political risk cover': 5.0,
    'dangerous waters': 6.0,
    'coverage pulled': 7.0,
    'withdraw coverage': 7.0,
    'coverage withdrawn': 7.0,
    'premiums near 1%': 8.0,
    'premiums higher': 5.0,
    'rates have risen sharply': 6.0,
    'rates could increase': 6.0,
    'capacity can withdraw overnight': 7.0,
}
SOFTENING_TERMS = {
    'soft market': 8.0,
    'soft cycle': 7.0,
    'softening back in play': 6.0,
    'pressure on rates': 5.0,
    'actual loss experience': 4.0,
    'does not guarantee sustainable rates': 5.0,
    'modest premium growth': 3.0,
    'plenty of capacity': 4.0,
    'adequate capacity': 4.0,
}


@dataclass(slots=True)
class ArticleAssessment:
    url: str
    title: str
    score: float
    relevance: float
    article_date: str | None


@dataclass(slots=True)
class SecFilingAssessment:
    ticker: str
    company_name: str
    form: str
    filed_at: date
    score: float
    highlights: list[str]


@dataclass(slots=True)
class MarineInsuranceAssessment:
    score: float
    source: str
    notes: str
    article_date: str | None
    article_count: int
    top_articles: list[str]


def _strip_html(value: str) -> str:
    without_scripts = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', value, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', without_scripts)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_title(html: str) -> str:
    match = re.search(r'<title>(.*?)</title>', html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ''
    title = re.sub(r'\s+', ' ', match.group(1)).strip()
    return title.replace('| Insurance News: Latest of global insurance industry by Beinsure', '').strip()


def _extract_article_date(text: str) -> str | None:
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2},\s+\d{4}', text)
    return match.group(0) if match else None


def _is_same_site(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc in {'beinsure.com', 'www.beinsure.com'}


def extract_relevant_links(html: str, source_url: str) -> list[str]:
    matches = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    results: list[str] = []
    seen: set[str] = set()
    for raw in matches:
        absolute = urljoin(source_url, raw)
        if '#' in absolute:
            absolute = absolute.split('#', 1)[0]
        if not _is_same_site(absolute):
            continue
        lowered = absolute.lower()
        if any(term in lowered for term in STRONG_URL_TERMS):
            if absolute not in seen:
                seen.add(absolute)
                results.append(absolute)
    return results


def _relevance_score(url: str, title: str, text: str) -> float:
    lowered_url = url.lower()
    lowered_title = title.lower()
    lowered_text = text.lower()
    score = 0.0
    for term, weight in STRONG_URL_TERMS.items():
        if term in lowered_url:
            score += weight
    for term, weight in STRONG_TEXT_TERMS.items():
        if term in lowered_title:
            score += weight * 1.5
        elif term in lowered_text:
            score += weight
    for term, penalty in GENERIC_PENALTY_TERMS.items():
        if term in lowered_title:
            score -= penalty
    if 'faq_category' in lowered_url or '/news/' == urlparse(url).path:
        score -= 8.0
    return score


def score_article(url: str, html: str) -> ArticleAssessment:
    title = _extract_title(html)
    text = _strip_html(html)
    lowered = text.lower()
    positive = sum(weight for term, weight in STRESS_TERMS.items() if term in lowered)
    softening = sum(weight for term, weight in SOFTENING_TERMS.items() if term in lowered)
    score = 38.0 + 0.5 * positive - 0.65 * softening
    score = max(10.0, min(90.0, score))
    relevance = _relevance_score(url, title, lowered)
    return ArticleAssessment(
        url=url,
        title=title or url,
        score=round(score, 2),
        relevance=round(relevance, 2),
        article_date=_extract_article_date(text),
    )


def _safe_json(response: httpx.Response) -> dict | list | None:
    try:
        return response.json()
    except json.JSONDecodeError:
        return None


def _fetch_sec_company_tickers(client: httpx.Client) -> dict[str, str]:
    response = client.get(SEC_COMPANY_TICKERS_URL)
    response.raise_for_status()
    payload = _safe_json(response)
    if not isinstance(payload, dict):
        return {}

    mapping: dict[str, str] = {}
    for value in payload.values():
        if not isinstance(value, dict):
            continue
        ticker = str(value.get('ticker') or '').upper().strip()
        cik = str(value.get('cik_str') or '').strip()
        if not ticker or not cik:
            continue
        mapping[ticker] = cik.zfill(10)
    return mapping


def _score_sec_filing_text(text: str) -> tuple[float, list[str]]:
    lowered = _strip_html(text).lower()
    positive = 0.0
    highlights: list[str] = []
    for term, weight in SEC_KEYWORD_WEIGHTS.items():
        if term in lowered:
            positive += weight
            highlights.append(term)
    negative = sum(weight for term, weight in SEC_NEGATIVE_WEIGHTS.items() if term in lowered)
    score = 28.0 + 0.85 * positive - 0.7 * negative
    return max(10.0, min(90.0, round(score, 2))), highlights[:4]


def _recent_sec_filings(payload: dict[str, object]) -> list[dict[str, str]]:
    filings = payload.get('filings') if isinstance(payload, dict) else None
    recent = filings.get('recent') if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        return []

    forms = recent.get('form')
    dates = recent.get('filingDate')
    accession_numbers = recent.get('accessionNumber')
    primary_documents = recent.get('primaryDocument')
    if not all(isinstance(item, list) for item in [forms, dates, accession_numbers, primary_documents]):
        return []

    rows: list[dict[str, str]] = []
    for form, filing_date, accession, primary_document in zip(forms, dates, accession_numbers, primary_documents):
        rows.append(
            {
                'form': str(form or ''),
                'filing_date': str(filing_date or ''),
                'accession_number': str(accession or ''),
                'primary_document': str(primary_document or ''),
            }
        )
    return rows


def aggregate_sec_filing_assessments(filings: list[SecFilingAssessment]) -> MarineInsuranceAssessment:
    if not filings:
        raise ValueError('No SEC filings matched the marine-insurance watchlist')

    ordered = sorted(filings, key=lambda item: (item.filed_at, item.score), reverse=True)
    selected = ordered[:MAX_SEC_FILINGS]
    weighted_score = 0.0
    total_weight = 0.0
    highlight_labels: list[str] = []
    for index, filing in enumerate(selected):
        recency_weight = max(1.0, len(selected) - index)
        weighted_score += filing.score * recency_weight
        total_weight += recency_weight
        highlight_labels.append(f'{filing.ticker} {filing.form} {filing.filed_at.isoformat()}')

    composite = weighted_score / max(total_weight, 1.0)
    checked_at = datetime.now(UTC).isoformat()
    notes = (
        'Auto-scored from SEC EDGAR watchlist; '
        'source=sec-edgar-watchlist; '
        f'checked={checked_at}; '
        f'items={len(selected)}; '
        f'signal={composite:.2f}; '
        f'highlights={" | ".join(highlight_labels[:4])}'
    )
    return MarineInsuranceAssessment(
        score=round(composite, 2),
        source='sec/edgar-watchlist',
        notes=notes,
        article_date=selected[0].filed_at.isoformat(),
        article_count=len(selected),
        top_articles=highlight_labels[:4],
    )


def aggregate_article_assessments(articles: list[ArticleAssessment]) -> MarineInsuranceAssessment:
    if not articles:
        return MarineInsuranceAssessment(
            score=45.0,
            source='beinsure/site_scan',
            notes='No relevant Beinsure marine or war-risk articles matched the filter on this refresh.',
            article_date=None,
            article_count=0,
            top_articles=[],
        )

    ordered = sorted(articles, key=lambda item: (item.relevance, item.article_date or '', item.score), reverse=True)
    selected = ordered[:MAX_ARTICLES]
    weights = [max(1.0, article.relevance) for article in selected]
    weighted_score = sum(article.score * weight for article, weight in zip(selected, weights)) / sum(weights)
    top_articles = [f"{article.title} ({article.article_date or 'undated'})" for article in selected[:3]]
    latest_date = next((article.article_date for article in selected if article.article_date), None)
    notes = (
        f'Auto-scored from Beinsure site scan; articles={len(selected)}, '
        f'checked={datetime.now(UTC).isoformat()}, top={" | ".join(top_articles)}'
    )
    return MarineInsuranceAssessment(
        score=round(weighted_score, 2),
        source='beinsure/site_scan',
        notes=notes,
        article_date=latest_date,
        article_count=len(selected),
        top_articles=top_articles,
    )


def collect_marine_insurance_assessment(timeout_seconds: float = 20.0) -> MarineInsuranceAssessment:
    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        try:
            ticker_map = _fetch_sec_company_tickers(client)
            assessments: list[SecFilingAssessment] = []
            cutoff = date.today() - timedelta(days=365)
            for ticker, company_name in SEC_WATCHLIST:
                cik = ticker_map.get(ticker)
                if not cik:
                    continue
                response = client.get(SEC_SUBMISSIONS_URL.format(cik=cik))
                response.raise_for_status()
                payload = _safe_json(response)
                if not isinstance(payload, dict):
                    continue
                cik_numeric = str(int(cik))
                for filing in _recent_sec_filings(payload):
                    form = filing['form']
                    if form not in SEC_FORMS:
                        continue
                    try:
                        filed_at = date.fromisoformat(filing['filing_date'])
                    except ValueError:
                        continue
                    if filed_at < cutoff:
                        continue
                    accession_number = filing['accession_number']
                    primary_document = filing['primary_document']
                    if not accession_number or not primary_document:
                        continue
                    document_url = SEC_ARCHIVES_URL.format(
                        cik_numeric=cik_numeric,
                        accession=accession_number.replace('-', ''),
                        document=primary_document,
                    )
                    try:
                        filing_response = client.get(document_url)
                        filing_response.raise_for_status()
                    except Exception:
                        continue
                    score, highlights = _score_sec_filing_text(filing_response.text)
                    if len(highlights) < 2 and score < 45:
                        continue
                    assessments.append(
                        SecFilingAssessment(
                            ticker=ticker,
                            company_name=company_name,
                            form=form,
                            filed_at=filed_at,
                            score=score,
                            highlights=highlights,
                        )
                    )
                    if len(assessments) >= MAX_SEC_FILINGS:
                        break
                if len(assessments) >= MAX_SEC_FILINGS:
                    break
            if assessments:
                return aggregate_sec_filing_assessments(assessments)
        except Exception:
            pass

    candidate_urls: list[str] = []
    seen_urls: set[str] = set()
    article_assessments: list[ArticleAssessment] = []

    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        for seed_url in SEED_URLS:
            response = client.get(seed_url)
            response.raise_for_status()
            if seed_url not in seen_urls:
                seen_urls.add(seed_url)
                candidate_urls.append(seed_url)
            for link in extract_relevant_links(response.text, seed_url):
                if link not in seen_urls:
                    seen_urls.add(link)
                    candidate_urls.append(link)

        for url in candidate_urls[:MAX_CANDIDATES]:
            try:
                response = client.get(url)
                response.raise_for_status()
            except Exception:
                continue
            article = score_article(url, response.text)
            if article.relevance >= 10.0:
                article_assessments.append(article)

    return aggregate_article_assessments(article_assessments)
