from app.collectors.public_manual_overlays import (
    _filter_geopolitical_titles,
    _filter_titles,
    _parse_rss_items,
    _score_terms,
)


def test_filter_geopolitical_titles_keeps_readable_shipping_headlines() -> None:
    titles = [
        'Oil prices jump as Iran warns Strait of Hormuz cannot be the same',
        'Completely unrelated earnings headline',
        '??????? ??????',
        'Red Sea shipping disruption raises tanker insurance costs',
    ]
    filtered = _filter_geopolitical_titles(titles)
    assert 'Oil prices jump as Iran warns Strait of Hormuz cannot be the same' in filtered
    assert 'Red Sea shipping disruption raises tanker insurance costs' in filtered
    assert all('unrelated' not in title.lower() for title in filtered)
    assert all('??' not in title for title in filtered)


def test_parse_rss_items_extracts_titles_and_dates() -> None:
    xml = '''
    <rss><channel>
      <item>
        <title>Central bank liquidity headline</title>
        <pubDate>Tue, 17 Mar 2026 12:00:00 GMT</pubDate>
        <description>Repo and swap lines discussion.</description>
      </item>
    </channel></rss>
    '''
    items = _parse_rss_items(xml)
    assert items == [
        {
            'title': 'Central bank liquidity headline',
            'pub_date': 'Tue, 17 Mar 2026 12:00:00 GMT',
            'description': 'Repo and swap lines discussion.',
        }
    ]


def test_filter_titles_can_target_governance_fragmentation_terms() -> None:
    titles = [
        'Provincial IRGC commander appears to contradict central command in Tehran',
        'Local sports update from Tehran',
        'Governor and Revolutionary Guard rivalry deepens in province',
    ]
    filtered = _filter_titles(titles, ('irgc', 'revolutionary guard', 'provincial', 'central command'))
    assert 'Provincial IRGC commander appears to contradict central command in Tehran' in filtered
    assert 'Governor and Revolutionary Guard rivalry deepens in province' in filtered
    assert all('sports' not in title.lower() for title in filtered)


def test_score_terms_accumulates_expected_keyword_weights() -> None:
    text = 'War risk notice of cancellation for Iran Persian Gulf listed area with additional premium.'
    score = _score_terms(
        text,
        {
            'war risk': 8.0,
            'notice of cancellation': 12.0,
            'iran': 8.0,
            'listed area': 6.0,
            'additional premium': 7.0,
        },
    )
    assert score == 41.0
