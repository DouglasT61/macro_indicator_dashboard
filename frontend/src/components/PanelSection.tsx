import { CompactIndicatorRow } from './CompactIndicatorRow';
import { IndicatorTile } from './IndicatorTile';
import type { EventAnnotationItem, Panel } from '../types/api';

interface PanelSectionProps {
  title: string;
  description: string;
  panels: Panel[];
  events: EventAnnotationItem[];
  compact?: boolean;
}

function describeBreadth(indicators: Panel['indicators']) {
  const usable = indicators.filter((indicator) => indicator.source_class !== 'demo');
  const sample = usable.length > 0 ? usable : indicators;
  const stressed = sample.filter((indicator) => indicator.status === 'orange' || indicator.status === 'red').length;
  const accelerating = sample.filter((indicator) => (indicator.rate_of_change ?? 0) > 0 || (indicator.acceleration ?? 0) > 0).length;
  const total = sample.length || 1;

  if (usable.length !== indicators.length) {
    return 'Data quality constrained: one or more indicators are unavailable and excluded from breadth assessment.';
  }
  if (stressed >= Math.ceil(total / 2) && accelerating >= Math.ceil(total / 3)) {
    return 'Broadening: multiple indicators are already stressed and momentum is still rising.';
  }
  if (stressed <= 1 && accelerating <= 1) {
    return 'Narrowing or contained: stress is limited in breadth and momentum is not spreading.';
  }
  return 'Mixed breadth: some indicators are stressed, but the move is not broad across the full panel.';
}

function summarizePanel(indicators: Panel['indicators']) {
  const usable = indicators.filter((indicator) => indicator.source_class !== 'demo');
  const sample = usable.length > 0 ? usable : indicators;
  const stressed = sample.filter((indicator) => indicator.status === 'orange' || indicator.status === 'red').length;
  const critical = sample.filter((indicator) => indicator.status === 'red').length;
  const top = sample.find((indicator) => indicator.status === 'red') ?? sample.find((indicator) => indicator.status === 'orange') ?? sample[0];
  return {
    stressed,
    critical,
    total: sample.length,
    top: top?.name ?? 'No indicators',
  };
}

export function PanelSection({ title, description, panels, events, compact = false }: PanelSectionProps) {
  return (
    <section className="panel-shell">
      <div className="panel-shell__header">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="panel-stack">
        {panels.map((panel, index) => {
          const summary = summarizePanel(panel.indicators);
          return (
            <details key={panel.id} className="panel-accordion" open={index === 0}>
              <summary className="panel-accordion__summary">
                <div>
                  <h3>{panel.title}</h3>
                  <p>{panel.description}</p>
                </div>
                <div className="panel-accordion__stats">
                  <span>{summary.stressed}/{summary.total} stressed</span>
                  <span>{summary.critical} critical</span>
                  <span>Top: {summary.top}</span>
                </div>
              </summary>
              <div className="panel-subsection">
                <div className="panel-subsection__header">
                  <div>
                    <h3>{panel.title}</h3>
                    <p>{panel.description}</p>
                  </div>
                  <p className="panel-subsection__breadth">{describeBreadth(panel.indicators)}</p>
                </div>
                {compact ? (
                  <div className="compact-indicator-list">
                    {panel.indicators.map((indicator) => (
                      <CompactIndicatorRow key={indicator.key} indicator={indicator} events={events} />
                    ))}
                  </div>
                ) : (
                  <div className="indicator-grid">
                    {panel.indicators.map((indicator) => (
                      <IndicatorTile key={indicator.key} indicator={indicator} events={events} />
                    ))}
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
