from datetime import date

from app.collectors.marine_insurance import (
    ArticleAssessment,
    SecFilingAssessment,
    aggregate_article_assessments,
    aggregate_sec_filing_assessments,
    extract_relevant_links,
    score_article,
    _score_sec_filing_text,
)


def test_extract_relevant_links_filters_for_beinsure_marine_topics() -> None:
    html = '''
    <a href="https://beinsure.com/marine-insurance-face-soft-market/">Marine</a>
    <a href="https://beinsure.com/gulf-war-rates-could-increase/">War risk</a>
    <a href="https://example.com/not-relevant/">Offsite</a>
    <a href="/shipping-insurance-market-update/">Shipping</a>
    <a href="/europe-insurance-news/">Generic roundup</a>
    '''
    links = extract_relevant_links(html, 'https://beinsure.com/news/')
    assert 'https://beinsure.com/marine-insurance-face-soft-market/' in links
    assert 'https://beinsure.com/gulf-war-rates-could-increase/' in links
    assert 'https://beinsure.com/shipping-insurance-market-update/' in links
    assert 'https://beinsure.com/europe-insurance-news/' not in links
    assert all('example.com' not in link for link in links)


def test_score_article_penalizes_generic_roundup_titles() -> None:
    html = '''
    <html><head><title>Europe Insurance News: Rates, Laws & Market Updates</title></head><body>
      <p>Insurance news roundup.</p>
      <p>Marine insurance is mentioned once.</p>
    </body></html>
    '''
    assessment = score_article('https://beinsure.com/europe-insurance-news/', html)
    assert assessment.relevance < 10


def test_score_article_balances_soft_market_and_war_risk_language() -> None:
    html = '''
    <html><head><title>Marine insurance face soft market</title></head><body>
      <p>Marine insurance remains in a soft market.</p>
      <p>War risk, red sea disruption, and longer, riskier routes still matter.</p>
    </body></html>
    '''
    assessment = score_article('https://beinsure.com/marine-insurance-face-soft-market/', html)
    assert 30 < assessment.score < 70
    assert assessment.relevance >= 10


def test_aggregate_article_assessments_weights_more_relevant_articles() -> None:
    articles = [
        ArticleAssessment(url='u1', title='High relevance', score=70, relevance=18, article_date='Mar 01, 2026'),
        ArticleAssessment(url='u2', title='Lower relevance', score=20, relevance=10, article_date='Feb 20, 2026'),
    ]
    aggregate = aggregate_article_assessments(articles)
    assert aggregate.score > 50
    assert aggregate.article_count == 2
    assert aggregate.source == 'beinsure/site_scan'


def test_score_sec_filing_text_detects_shipping_and_war_risk_language() -> None:
    text = '''
    The Red Sea security environment forced rerouting around the Cape of Good Hope.
    War risk insurance premium increases affected voyage economics.
    Management disclosed additional marine insurance costs and transit disruption.
    '''
    score, highlights = _score_sec_filing_text(text)
    assert score >= 50
    assert 'red sea' in highlights
    assert 'war risk' in highlights


def test_aggregate_sec_filing_assessments_prefers_recent_high_signal_filings() -> None:
    filings = [
        SecFilingAssessment(
            ticker='STNG',
            company_name='Scorpio Tankers',
            form='6-K',
            filed_at=date(2026, 3, 20),
            score=72.0,
            highlights=['red sea', 'war risk'],
        ),
        SecFilingAssessment(
            ticker='ACGL',
            company_name='Arch Capital',
            form='10-K',
            filed_at=date(2026, 2, 10),
            score=48.0,
            highlights=['insurance premium'],
        ),
    ]
    aggregate = aggregate_sec_filing_assessments(filings)
    assert aggregate.score > 55
    assert aggregate.source == 'sec/edgar-watchlist'
    assert aggregate.article_count == 2
