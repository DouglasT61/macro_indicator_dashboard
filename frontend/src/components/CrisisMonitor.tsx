import type { CrisisSignal } from '../types/api';

interface CrisisMonitorProps {
  signals: CrisisSignal[];
  active: boolean;
}

const PANEL_THRESHOLDS = {
  warning: '3 signals in warning/critical',
  critical: '4 or more signals in warning/critical',
};

export function CrisisMonitor({ signals, active }: CrisisMonitorProps) {
  return (
    <section className={`panel-shell crisis-monitor ${active ? 'crisis-monitor--active' : ''}`}>
      <div className="panel-shell__header">
        <div>
          <h2>Intraday / Fast-Moving Stress Panel</h2>
          <p>{active ? 'Systemic stress alert active: three or more fast signals are flashing.' : 'No systemic stress trigger right now.'}</p>
        </div>
        <div className="crisis-monitor__thresholds">
          <span>Warning: {PANEL_THRESHOLDS.warning}</span>
          <span>Critical: {PANEL_THRESHOLDS.critical}</span>
        </div>
      </div>
      <div className="crisis-monitor__grid">
        {signals.map((signal) => (
          <article key={signal.key} className={`crisis-signal crisis-signal--${signal.status}`}>
            <div className="crisis-signal__header">
              <div className="crisis-signal__label">{signal.label}</div>
              <span className={`status-pill status-pill--${signal.status}`}>{signal.status}</span>
            </div>
            <div className="crisis-signal__value">{signal.value.toFixed(2)}</div>
            <p>{signal.explanation}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
