from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from app.services.analytics import clamp, normalize_value


def _labelize(value: str) -> str:
    return value.replace('_', ' ')


def _component_score(indicator: str, value: float, rule: dict[str, Any], thresholds: dict[str, dict[str, Any]]) -> float:
    mode = rule.get('mode', 'stress')
    if mode == 'toggle':
        return 100.0 if value >= 1 else 0.0
    return normalize_value(value, thresholds.get(indicator)) or 0.0


def _build_base_node_states(
    merged: dict[str, float],
    thresholds: dict[str, dict[str, Any]],
    causal_groups: dict[str, list[str]],
) -> dict[str, dict[str, Any]]:
    node_states: dict[str, dict[str, Any]] = {}
    for node, indicators in causal_groups.items():
        inputs: list[dict[str, Any]] = []
        normalized_values: list[float] = []
        for indicator in indicators:
            value = float(merged.get(indicator, 0.0))
            normalized = normalize_value(value, thresholds.get(indicator))
            if normalized is None:
                continue
            normalized_values.append(normalized)
            inputs.append(
                {
                    'indicator': indicator,
                    'value': round(value, 2),
                    'normalized': round(normalized, 2),
                }
            )
        base_score = round(sum(normalized_values) / len(normalized_values), 2) if normalized_values else 0.0
        node_states[node] = {
            'base_score': base_score,
            'inputs': sorted(inputs, key=lambda item: item['normalized'], reverse=True)[:3],
        }
    return node_states


def _evaluate_propagation(
    merged: dict[str, float],
    thresholds: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    causal_groups = config.get('causal_groups', {})
    propagation_config = config.get('propagation') or {}
    if not causal_groups or not propagation_config:
        return {'node_states': {}, 'regime_effects': {}, 'iteration_history': []}

    base_states = _build_base_node_states(merged, thresholds, causal_groups)
    if not base_states:
        return {'node_states': {}, 'regime_effects': {}, 'iteration_history': []}

    activation_floor = float(propagation_config.get('activation_floor', 45.0))
    memory = float(propagation_config.get('memory', 0.35))
    feedback_gain = float(propagation_config.get('feedback_gain', 0.24))
    synergy_gain = float(propagation_config.get('synergy_gain', 0.22))
    iterations = int(propagation_config.get('iterations', 4))

    edges_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in propagation_config.get('edges', []):
        edges_by_target[edge['to']].append(edge)

    current_scores = {node: state['base_score'] for node, state in base_states.items()}
    latest_upstream: dict[str, list[dict[str, Any]]] = {node: [] for node in base_states}
    latest_incoming: dict[str, float] = {node: 0.0 for node in base_states}
    iteration_history: list[dict[str, Any]] = []

    for iteration in range(iterations):
        next_scores: dict[str, float] = {}
        next_upstream: dict[str, list[dict[str, Any]]] = {}
        next_incoming: dict[str, float] = {}
        for node, state in base_states.items():
            base_score = float(state['base_score'])
            upstream: list[dict[str, Any]] = []
            for edge in edges_by_target.get(node, []):
                source = edge['from']
                source_score = current_scores.get(source, base_states.get(source, {}).get('base_score', 0.0))
                pressure = max(0.0, source_score - activation_floor) * float(edge['weight'])
                if pressure <= 0:
                    continue
                upstream.append(
                    {
                        'source': source,
                        'pressure': round(pressure, 2),
                        'source_score': round(source_score, 2),
                    }
                )
            incoming_pressure = sum(item['pressure'] for item in upstream)
            direct_component = base_score * (1.0 - memory)
            memory_component = current_scores.get(node, base_score) * memory
            feedback_component = incoming_pressure * feedback_gain
            synergy_component = max(0.0, base_score - activation_floor) * incoming_pressure / 100.0 * synergy_gain
            propagated_score = clamp(direct_component + memory_component + feedback_component + synergy_component)
            next_scores[node] = round(propagated_score, 2)
            next_incoming[node] = round(incoming_pressure, 2)
            next_upstream[node] = sorted(upstream, key=lambda item: item['pressure'], reverse=True)[:3]
        current_scores = next_scores
        latest_incoming = next_incoming
        latest_upstream = next_upstream
        iteration_history.append({'iteration': iteration + 1, 'states': current_scores.copy()})

    node_states: dict[str, dict[str, Any]] = {}
    for node, state in base_states.items():
        base_score = float(state['base_score'])
        propagated_score = float(current_scores.get(node, base_score))
        amplification = round(max(0.0, propagated_score - base_score), 2)
        node_states[node] = {
            'base_score': round(base_score, 2),
            'propagated_score': round(propagated_score, 2),
            'amplification': amplification,
            'incoming_pressure': round(float(latest_incoming.get(node, 0.0)), 2),
            'inputs': state['inputs'],
            'top_upstream': latest_upstream.get(node, []),
        }

    regime_effects: dict[str, dict[str, Any]] = {}
    for regime_name, sensitivities in (propagation_config.get('regime_sensitivity') or {}).items():
        total = 0.0
        drivers: list[dict[str, Any]] = []
        for node, weight in sensitivities.items():
            state = node_states.get(node)
            if state is None:
                continue
            amplification = float(state['amplification'])
            contribution = amplification * float(weight)
            total += contribution
            top_upstream = ', '.join(_labelize(item['source']) for item in state['top_upstream'][:2])
            if not top_upstream:
                top_upstream = 'direct node pressure'
            drivers.append(
                {
                    'indicator': node,
                    'value': round(float(state['propagated_score']), 2),
                    'score': round(amplification, 2),
                    'contribution': round(contribution, 2),
                    'description': f'Recursive propagation is reinforcing {_labelize(node)} via {top_upstream}.',
                }
            )
        regime_effects[regime_name] = {
            'total': round(total, 2),
            'drivers': sorted(drivers, key=lambda item: item['contribution'], reverse=True),
        }

    return {
        'node_states': node_states,
        'regime_effects': regime_effects,
        'iteration_history': iteration_history,
    }


def evaluate_regimes(
    value_lookup: dict[str, float], manual_inputs: dict[str, float], config: dict[str, Any]
) -> dict[str, Any]:
    thresholds = config['thresholds']
    merged = {**value_lookup, **manual_inputs}
    propagation = _evaluate_propagation(merged, thresholds, config)
    scores: dict[str, float] = {}
    drivers_by_regime: dict[str, list[dict[str, Any]]] = {}

    for regime_name, rules in config['regimes'].items():
        total = 0.0
        drivers: list[dict[str, Any]] = []
        for rule in rules:
            indicator = rule['indicator']
            value = float(merged.get(indicator, 0.0))
            component = _component_score(indicator, value, rule, thresholds)
            contribution = component * float(rule['weight'])
            total += contribution
            drivers.append(
                {
                    'indicator': indicator,
                    'value': round(value, 2),
                    'score': round(component, 2),
                    'contribution': round(contribution, 2),
                    'description': rule['description'],
                }
            )

        regime_propagation = propagation.get('regime_effects', {}).get(regime_name, {'total': 0.0, 'drivers': []})
        total += float(regime_propagation.get('total', 0.0))
        drivers.extend(regime_propagation.get('drivers', []))
        scores[regime_name] = round(total, 2)
        drivers_by_regime[regime_name] = sorted(drivers, key=lambda item: item['contribution'], reverse=True)

    current_regime = max(scores, key=scores.get)
    return {
        'scores': scores,
        'current_regime': current_regime,
        'drivers': drivers_by_regime,
        'summary': {
            regime: [f"{driver['indicator']}: {driver['description']}" for driver in drivers[:4]]
            for regime, drivers in drivers_by_regime.items()
        },
        'propagation': propagation,
    }


def build_regime_history(
    timelines: dict[str, Sequence[tuple[Any, float]]], manual_inputs: dict[str, float], config: dict[str, Any]
) -> list[dict[str, Any]]:
    if not timelines:
        return []

    anchor_key = next(iter(timelines))
    history: list[dict[str, Any]] = []
    for index, (timestamp, _) in enumerate(timelines[anchor_key]):
        values = {key: float(points[index][1]) for key, points in timelines.items() if len(points) > index}
        evaluation = evaluate_regimes(values, manual_inputs, config)
        history.append(
            {
                'timestamp': timestamp,
                'sticky_score': evaluation['scores']['sticky'],
                'convex_score': evaluation['scores']['convex'],
                'break_score': evaluation['scores']['break'],
                'explanation': evaluation,
            }
        )
    return history
