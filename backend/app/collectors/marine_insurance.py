from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import httpx


BEINSURE_BASE_URL = 'https://beinsure.com'
USER_AGENT = 'Mozilla/5.0 macro-stress-dashboard/0.1'
MAX_CANDIDATES = 24
MAX_ARTICLES = 8
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
    candidate_urls: list[str] = []
    seen_urls: set[str] = set()
    article_assessments: list[ArticleAssessment] = []

    with httpx.Client(timeout=timeout_seconds, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        for seed_url in SEED_URLS:
            try:
                response = client.get(seed_url)
                response.raise_for_status()
            except Exception:
                # Seed URL failure is non-fatal: skip and continue with any
                # candidate URLs already gathered from other seed pages.
                continue
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
