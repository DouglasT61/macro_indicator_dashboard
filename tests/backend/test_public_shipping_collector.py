from datetime import UTC, datetime

from app.collectors.public_shipping import (
    build_hormuz_transit_stress_history,
    score_eia_chokepoint_page,
)


def test_score_eia_chokepoint_page_detects_disruption_language() -> None:
    html = '''
    <html><body>
      <table>
        <tr><td>Total oil flows through Bab el-Mandeb Strait</td><td>6.6</td><td>6.7</td><td>6.9</td><td>4.8</td><td>4.2</td><td>4.1</td></tr>
      </table>
      <p>Security concerns and high insurance rates increased after Red Sea attacks.</p>
      <p>Some ships avoided the Bab el-Mandeb route.</p>
    </body></html>
    '''
    assessment = score_eia_chokepoint_page(html)
    assert assessment.score > 50
    assert assessment.source == 'eia/chokepoints'


def test_build_hormuz_transit_stress_history_rises_when_tanker_calls_drop() -> None:
    rows: list[dict[str, object]] = []
    for day in range(1, 41):
        tanker_calls = 14 if day <= 20 else 7
        tanker_capacity = 28 if day <= 20 else 13
        rows.append(
            {
                'date': datetime(2026, 2 if day <= 28 else 3, day if day <= 28 else day - 28, tzinfo=UTC).timestamp() * 1000,
                'portname': 'Strait of Hormuz',
                'portid': 'strait_of_hormuz',
                'n_tanker': tanker_calls,
                'n_total': 22,
                'capacity_tanker': tanker_capacity,
                'capacity': 40,
            }
        )

    history = build_hormuz_transit_stress_history(rows)

    assert len(history) == 40
    assert history[-1][1] > history[10][1]
    assert history[-1][1] >= 55.0
