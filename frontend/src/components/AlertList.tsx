import type { AlertItem } from '../types/api';

interface AlertListProps {
  alerts: AlertItem[];
}

function severityClass(severity: AlertItem['severity']): string {
  if (severity === 'critical') {
    return 'red';
  }
  if (severity === 'warning') {
    return 'orange';
  }
  return 'yellow';
}

export function AlertList({ alerts }: AlertListProps) {
  return (
    <section className="panel-shell">
      <div className="panel-shell__header">
        <h2>Alert Engine</h2>
        <p>Threshold breaches and combination alerts along the macro stress chain.</p>
      </div>
      <div className="alert-list">
        {alerts.map((alert) => (
          <article key={`${alert.timestamp}-${alert.title}`} className={`alert-item alert-item--${alert.severity}`}>
            <div className="alert-item__header">
              <span className={`status-pill status-pill--${severityClass(alert.severity)}`}>
                {alert.severity}
              </span>
              <h3>{alert.title}</h3>
            </div>
            <p>{alert.body}</p>
            <small>Next stage: {alert.next_stage_consequence}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
