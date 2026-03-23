from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROFILE_KEYS = [
    'brent_prompt_spread',
    'wti_prompt_spread',
    'tanker_freight_proxy',
    'tanker_disruption_score',
    'marine_insurance_stress',
    'jpy_usd_basis',
    'eur_usd_basis',
    'sofr_spread',
    'move_index',
    'auction_stress',
    'treasury_liquidity_proxy',
    'treasury_basis_proxy',
    'fima_repo_usage',
    'fed_swap_line_usage',
    'private_credit_stress',
    'payroll_momentum',
    'unemployment_rate',
    'wage_stickiness',
    'hours_worked_momentum',
    'temp_help_stress',
    'employment_tax_base_proxy',
    'geopolitical_escalation_toggle',
    'central_bank_intervention_toggle',
]

CLUSTER_LABELS = {
    'shipping': 'Shipping / Insurance Shock',
    'funding': 'Dollar Funding Squeeze',
    'plumbing': 'Treasury Plumbing Break',
    'energy': 'Energy / Inflation Shock',
}


@dataclass(frozen=True)
class EpisodeTemplate:
    key: str
    label: str
    period: str
    regime_bias: str
    cluster: str
    summary: str
    profile: dict[str, float]
    regime_scores: dict[str, float]


BASE_PROFILE = {
    'brent_prompt_spread': 18.0,
    'wti_prompt_spread': 16.0,
    'tanker_freight_proxy': 14.0,
    'tanker_disruption_score': 10.0,
    'marine_insurance_stress': 10.0,
    'jpy_usd_basis': 18.0,
    'eur_usd_basis': 16.0,
    'sofr_spread': 14.0,
    'move_index': 24.0,
    'auction_stress': 18.0,
    'treasury_liquidity_proxy': 18.0,
    'treasury_basis_proxy': 16.0,
    'fima_repo_usage': 12.0,
    'fed_swap_line_usage': 10.0,
    'private_credit_stress': 18.0,
    'payroll_momentum': 48.0,
    'unemployment_rate': 22.0,
    'wage_stickiness': 38.0,
    'hours_worked_momentum': 18.0,
    'temp_help_stress': 26.0,
    'employment_tax_base_proxy': 42.0,
    'geopolitical_escalation_toggle': 0.0,
    'central_bank_intervention_toggle': 0.0,
}


def _profile(**overrides: float) -> dict[str, float]:
    profile = dict(BASE_PROFILE)
    profile.update({key: float(value) for key, value in overrides.items()})
    return profile


EPISODE_TEMPLATES: list[EpisodeTemplate] = [
    EpisodeTemplate(
        key='dash_for_cash_2020',
        label='March 2020 Dash for Cash',
        period='Mar 2020',
        regime_bias='break',
        cluster='plumbing',
        summary='Treasury depth collapsed, basis pressure surged, and Fed plumbing intervention dominated the regime.',
        profile=_profile(
            brent_prompt_spread=18.0,
            wti_prompt_spread=16.0,
            tanker_freight_proxy=18.0,
            tanker_disruption_score=12.0,
            marine_insurance_stress=18.0,
            jpy_usd_basis=82.0,
            eur_usd_basis=78.0,
            sofr_spread=74.0,
            move_index=95.0,
            auction_stress=62.0,
            treasury_liquidity_proxy=98.0,
            treasury_basis_proxy=92.0,
            fima_repo_usage=88.0,
            fed_swap_line_usage=72.0,
            private_credit_stress=58.0,
            payroll_momentum=18.0,
            unemployment_rate=82.0,
            wage_stickiness=28.0,
            hours_worked_momentum=76.0,
            temp_help_stress=84.0,
            employment_tax_base_proxy=86.0,
            central_bank_intervention_toggle=1.0,
        ),
        regime_scores={'sticky': 28.0, 'convex': 54.0, 'break': 92.0},
    ),
    EpisodeTemplate(
        key='uk_gilt_ldi_2022',
        label='UK Gilt / LDI Shock',
        period='Sep 2022',
        regime_bias='break',
        cluster='plumbing',
        summary='Duration clearing failed quickly, forcing intervention into sovereign plumbing before broader inflation pressures faded.',
        profile=_profile(
            brent_prompt_spread=42.0,
            wti_prompt_spread=38.0,
            tanker_freight_proxy=24.0,
            tanker_disruption_score=18.0,
            marine_insurance_stress=20.0,
            jpy_usd_basis=60.0,
            eur_usd_basis=54.0,
            sofr_spread=40.0,
            move_index=88.0,
            auction_stress=78.0,
            treasury_liquidity_proxy=84.0,
            treasury_basis_proxy=76.0,
            fima_repo_usage=42.0,
            fed_swap_line_usage=18.0,
            private_credit_stress=65.0,
            payroll_momentum=28.0,
            unemployment_rate=36.0,
            wage_stickiness=54.0,
            hours_worked_momentum=34.0,
            temp_help_stress=42.0,
            employment_tax_base_proxy=38.0,
            central_bank_intervention_toggle=1.0,
        ),
        regime_scores={'sticky': 34.0, 'convex': 58.0, 'break': 80.0},
    ),
    EpisodeTemplate(
        key='regional_bank_funding_2023',
        label='Regional Bank Funding Stress',
        period='Mar 2023',
        regime_bias='convex',
        cluster='funding',
        summary='Funding stress and intervention pressure rose faster than oil or shipping stress, producing a convex but not fully repressive regime.',
        profile=_profile(
            brent_prompt_spread=24.0,
            wti_prompt_spread=22.0,
            tanker_freight_proxy=16.0,
            tanker_disruption_score=12.0,
            marine_insurance_stress=14.0,
            jpy_usd_basis=70.0,
            eur_usd_basis=62.0,
            sofr_spread=58.0,
            move_index=72.0,
            auction_stress=36.0,
            treasury_liquidity_proxy=58.0,
            treasury_basis_proxy=54.0,
            fima_repo_usage=46.0,
            fed_swap_line_usage=20.0,
            private_credit_stress=52.0,
            payroll_momentum=34.0,
            unemployment_rate=42.0,
            wage_stickiness=44.0,
            hours_worked_momentum=40.0,
            temp_help_stress=52.0,
            employment_tax_base_proxy=44.0,
            central_bank_intervention_toggle=1.0,
        ),
        regime_scores={'sticky': 24.0, 'convex': 74.0, 'break': 46.0},
    ),
    EpisodeTemplate(
        key='red_sea_shipping_2024',
        label='Red Sea Shipping Shock',
        period='Q1 2024',
        regime_bias='sticky',
        cluster='shipping',
        summary='Shipping and insurance stress stayed high, but funding and Treasury dysfunction did not yet fully synchronize.',
        profile=_profile(
            brent_prompt_spread=78.0,
            wti_prompt_spread=74.0,
            tanker_freight_proxy=82.0,
            tanker_disruption_score=88.0,
            marine_insurance_stress=86.0,
            jpy_usd_basis=34.0,
            eur_usd_basis=28.0,
            sofr_spread=20.0,
            move_index=42.0,
            auction_stress=28.0,
            treasury_liquidity_proxy=34.0,
            treasury_basis_proxy=30.0,
            fima_repo_usage=20.0,
            fed_swap_line_usage=10.0,
            private_credit_stress=36.0,
            payroll_momentum=64.0,
            unemployment_rate=18.0,
            wage_stickiness=52.0,
            hours_worked_momentum=16.0,
            temp_help_stress=22.0,
            employment_tax_base_proxy=58.0,
            geopolitical_escalation_toggle=1.0,
        ),
        regime_scores={'sticky': 72.0, 'convex': 44.0, 'break': 22.0},
    ),
    EpisodeTemplate(
        key='eurozone_dollar_shortage_2011',
        label='Eurozone Dollar Funding Squeeze',
        period='Late 2011',
        regime_bias='convex',
        cluster='funding',
        summary='Cross-currency dollar scarcity, sovereign duration pressure, and swap-line reliance rose together without a pure oil-shock trigger.',
        profile=_profile(
            brent_prompt_spread=46.0,
            wti_prompt_spread=42.0,
            tanker_freight_proxy=22.0,
            tanker_disruption_score=14.0,
            marine_insurance_stress=8.0,
            jpy_usd_basis=72.0,
            eur_usd_basis=82.0,
            sofr_spread=52.0,
            move_index=68.0,
            auction_stress=58.0,
            treasury_liquidity_proxy=62.0,
            treasury_basis_proxy=56.0,
            fima_repo_usage=34.0,
            fed_swap_line_usage=64.0,
            private_credit_stress=44.0,
            payroll_momentum=30.0,
            unemployment_rate=34.0,
            wage_stickiness=26.0,
            hours_worked_momentum=28.0,
            temp_help_stress=30.0,
            employment_tax_base_proxy=32.0,
            central_bank_intervention_toggle=1.0,
        ),
        regime_scores={'sticky': 22.0, 'convex': 82.0, 'break': 54.0},
    ),
    EpisodeTemplate(
        key='repo_spike_2019',
        label='September 2019 Repo Spike',
        period='Sep 2019',
        regime_bias='convex',
        cluster='funding',
        summary='Short-end funding markets broke first, then pulled Treasury basis and liquidity indicators wider before a full sovereign clearing failure.',
        profile=_profile(
            brent_prompt_spread=18.0,
            wti_prompt_spread=16.0,
            tanker_freight_proxy=12.0,
            tanker_disruption_score=8.0,
            marine_insurance_stress=6.0,
            jpy_usd_basis=46.0,
            eur_usd_basis=34.0,
            sofr_spread=84.0,
            move_index=56.0,
            auction_stress=30.0,
            treasury_liquidity_proxy=64.0,
            treasury_basis_proxy=68.0,
            fima_repo_usage=18.0,
            fed_swap_line_usage=8.0,
            private_credit_stress=28.0,
            payroll_momentum=38.0,
            unemployment_rate=16.0,
            wage_stickiness=30.0,
            hours_worked_momentum=24.0,
            temp_help_stress=48.0,
            employment_tax_base_proxy=40.0,
            central_bank_intervention_toggle=1.0,
        ),
        regime_scores={'sticky': 18.0, 'convex': 68.0, 'break': 52.0},
    ),
    EpisodeTemplate(
        key='european_energy_crisis_2022',
        label='European Energy Shock',
        period='Q3 2022',
        regime_bias='sticky',
        cluster='energy',
        summary='Physical energy scarcity and geopolitical escalation stayed dominant while global funding and Treasury plumbing absorbed the shock unevenly.',
        profile=_profile(
            brent_prompt_spread=86.0,
            wti_prompt_spread=80.0,
            tanker_freight_proxy=54.0,
            tanker_disruption_score=42.0,
            marine_insurance_stress=24.0,
            jpy_usd_basis=44.0,
            eur_usd_basis=58.0,
            sofr_spread=30.0,
            move_index=58.0,
            auction_stress=34.0,
            treasury_liquidity_proxy=36.0,
            treasury_basis_proxy=32.0,
            fima_repo_usage=16.0,
            fed_swap_line_usage=6.0,
            private_credit_stress=48.0,
            payroll_momentum=42.0,
            unemployment_rate=22.0,
            wage_stickiness=72.0,
            hours_worked_momentum=20.0,
            temp_help_stress=28.0,
            employment_tax_base_proxy=46.0,
            geopolitical_escalation_toggle=1.0,
        ),
        regime_scores={'sticky': 78.0, 'convex': 62.0, 'break': 26.0},
    ),
]


def extract_snapshot_profile(snapshots: dict[str, dict[str, Any]]) -> dict[str, float]:
    profile: dict[str, float] = {}
    for key in PROFILE_KEYS:
        snapshot = snapshots.get(key)
        if snapshot is None or snapshot.get('normalized_value') is None:
            profile[key] = 50.0
        else:
            profile[key] = float(snapshot.get('normalized_value'))
    return profile


def _cluster_centroids() -> dict[str, dict[str, float]]:
    grouped: dict[str, list[EpisodeTemplate]] = {}
    for template in EPISODE_TEMPLATES:
        grouped.setdefault(template.cluster, []).append(template)
    centroids: dict[str, dict[str, float]] = {}
    for cluster, templates in grouped.items():
        centroids[cluster] = {
            key: round(sum(template.profile.get(key, 0.0) for template in templates) / max(1, len(templates)), 2)
            for key in PROFILE_KEYS
        }
    return centroids


def _profile_similarity(current: dict[str, float], profile: dict[str, float]) -> float:
    diffs = [abs(current.get(key, 0.0) - target) for key, target in profile.items()]
    average_diff = sum(diffs) / max(1, len(diffs))
    return max(0.0, min(100.0, 100.0 - average_diff))


def score_episode_clusters(profile: dict[str, float]) -> list[dict[str, Any]]:
    centroids = _cluster_centroids()
    cluster_scores: list[dict[str, Any]] = []
    for cluster, centroid in centroids.items():
        similarity = round(_profile_similarity(profile, centroid), 2)
        templates = [template for template in EPISODE_TEMPLATES if template.cluster == cluster]
        avg_regime = {
            regime: round(sum(float(template.regime_scores[regime]) for template in templates) / max(1, len(templates)), 2)
            for regime in ('sticky', 'convex', 'break')
        }
        lead_regime = max(avg_regime, key=avg_regime.get)
        cluster_scores.append(
            {
                'key': cluster,
                'label': CLUSTER_LABELS.get(cluster, cluster.replace('_', ' ').title()),
                'similarity': similarity,
                'episode_count': len(templates),
                'lead_regime': lead_regime,
            }
        )
    cluster_scores.sort(key=lambda item: item['similarity'], reverse=True)
    return cluster_scores


def infer_episode_cluster(profile: dict[str, float]) -> dict[str, Any]:
    cluster_scores = score_episode_clusters(profile)
    if not cluster_scores:
        return {
            'key': 'unavailable',
            'label': 'Unavailable',
            'similarity': 0.0,
            'confidence': 0.0,
            'summary': 'No cluster classification available.',
            'supporting_episodes': [],
            'clusters': [],
        }

    top = cluster_scores[0]
    runner_up = cluster_scores[1] if len(cluster_scores) > 1 else {'similarity': 0.0}
    confidence = round(max(0.0, min(1.0, (float(top['similarity']) - float(runner_up['similarity'])) / 15.0)), 2)
    supporting = [template.label for template in EPISODE_TEMPLATES if template.cluster == top['key']][:3]
    summary = (
        f"Current episode family is {top['label']} with similarity {top['similarity']:.1f} and confidence {confidence * 100:.0f}%. "
        f"Closest supporting episodes are {', '.join(supporting)}."
    )
    return {
        'key': top['key'],
        'label': top['label'],
        'similarity': float(top['similarity']),
        'confidence': confidence,
        'summary': summary,
        'supporting_episodes': supporting,
        'clusters': cluster_scores,
    }


def _regime_similarity(regime: dict[str, Any], template: EpisodeTemplate) -> float:
    current_scores = {
        'sticky': float(regime['sticky']['score']),
        'convex': float(regime['convex']['score']),
        'break': float(regime['break']['score']),
    }
    diffs = [abs(current_scores[key] - template.regime_scores[key]) for key in ('sticky', 'convex', 'break')]
    average_diff = sum(diffs) / 3.0
    return max(0.0, min(100.0, 100.0 - average_diff))


def _top_matches(current: dict[str, float], template: EpisodeTemplate) -> tuple[list[str], list[str]]:
    strongest: list[tuple[str, float]] = []
    weakest: list[tuple[str, float]] = []
    for key, target in template.profile.items():
        diff = abs(current.get(key, 0.0) - target)
        strongest.append((key, diff))
        weakest.append((key, diff))
    strongest.sort(key=lambda item: item[1])
    weakest.sort(key=lambda item: item[1], reverse=True)
    return (
        [item[0].replace('_', ' ') for item in strongest[:4]],
        [item[0].replace('_', ' ') for item in weakest[:4]],
    )


def build_backtest_overview(
    snapshots: dict[str, dict[str, Any]],
    regime: dict[str, Any],
    state_space: dict[str, Any],
) -> dict[str, Any]:
    current_profile = extract_snapshot_profile(snapshots)
    cluster_focus = infer_episode_cluster(current_profile)
    episodes: list[dict[str, Any]] = []

    for template in EPISODE_TEMPLATES:
        profile_similarity = _profile_similarity(current_profile, template.profile)
        regime_similarity = _regime_similarity(regime, template)
        combined_similarity = round(profile_similarity * 0.65 + regime_similarity * 0.35, 2)
        closest, furthest = _top_matches(current_profile, template)
        episodes.append(
            {
                'key': template.key,
                'label': template.label,
                'period': template.period,
                'regime_bias': template.regime_bias,
                'cluster': template.cluster,
                'cluster_label': CLUSTER_LABELS.get(template.cluster, template.cluster.replace('_', ' ').title()),
                'similarity': combined_similarity,
                'profile_similarity': round(profile_similarity, 2),
                'regime_similarity': round(regime_similarity, 2),
                'summary': template.summary,
                'closest_matches': closest,
                'furthest_matches': furthest,
                'regime_scores': template.regime_scores,
            }
        )

    episodes.sort(key=lambda item: item['similarity'], reverse=True)
    top_episode = episodes[0] if episodes else None
    summary = (
        f"Closest historical analog is {top_episode['label']} ({top_episode['period']}) at {top_episode['similarity']:.1f} similarity. "
        f"Dominant episode family is {cluster_focus['label']} at {cluster_focus['similarity']:.1f} similarity."
        if top_episode
        else 'No historical analogs available.'
    )

    return {
        'summary': summary,
        'dominant_cluster': cluster_focus['key'],
        'dominant_cluster_label': cluster_focus['label'],
        'cluster_confidence': cluster_focus['confidence'],
        'clusters': cluster_focus['clusters'][:4],
        'episodes': episodes[:6],
    }
