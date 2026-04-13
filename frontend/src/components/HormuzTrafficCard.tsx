import type { HormuzTrafficStats } from '../types/api';

interface HormuzTrafficCardProps {
  stats: HormuzTrafficStats | null;
}

function StatRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="hormuz-card__stat-row">
      <span className="hormuz-card__stat-label">{label}</span>
      <span className="hormuz-card__stat-value">
        {value}
        {sub ? <span className="hormuz-card__stat-sub">{sub}</span> : null}
      </span>
    </div>
  );
}

function fmt(n: number) {
  return n.toFixed(1);
}

export function HormuzTrafficCard({ stats }: HormuzTrafficCardProps) {
  const hasData = stats !== null;
  const isLive = hasData && stats.source.includes('portwatch');
  const isDemo = hasData && stats.source.includes('demo');

  const latestCount = stats?.latest_count ?? null;
  const avg30d = stats?.avg_30d ?? null;
  const avgLongterm = stats?.avg_longterm ?? null;
  const latestDate = (stats?.latest_date && stats.latest_date !== 'demo') ? stats.latest_date : null;

  // Colour the focal number relative to long-term average
  let focalTone: 'normal' | 'warn' | 'stress' = 'normal';
  if (latestCount !== null && avgLongterm !== null && avgLongterm > 0) {
    const pctDrop = (avgLongterm - latestCount) / avgLongterm;
    if (pctDrop >= 0.2) focalTone = 'stress';
    else if (pctDrop >= 0.08) focalTone = 'warn';
  }

  return (
    <article className="thesis-intro__card hormuz-card">
      <div className="hormuz-card__header">
        <h2>Hormuz daily tanker transits</h2>
        <span className={`hormuz-card__badge hormuz-card__badge--${isLive ? 'live' : isDemo ? 'demo' : 'none'}`}>
          {isLive ? 'PortWatch live' : isDemo ? 'demo' : 'no data'}
        </span>
      </div>

      <div className="hormuz-card__context">
        <StatRow
          label="Long-term avg"
          value={avgLongterm !== null ? fmt(avgLongterm) : '—'}
          sub=" tankers / day"
        />
        <StatRow
          label="30-day avg"
          value={avg30d !== null ? fmt(avg30d) : '—'}
          sub=" tankers / day"
        />
        <StatRow
          label={latestDate ? `Latest (${latestDate})` : 'Latest reading'}
          value={latestCount !== null ? fmt(latestCount) : '—'}
          sub=" tankers"
        />
      </div>

      <div className={`hormuz-card__focal hormuz-card__focal--${focalTone}`}>
        <span className="hormuz-card__focal-number">
          {latestCount !== null ? latestCount.toFixed(0) : '—'}
        </span>
        <span className="hormuz-card__focal-label">tankers / day</span>
      </div>

      {isDemo && (
        <p className="hormuz-card__unavailable">
          Demo values shown. Live PortWatch data will replace these on the next successful refresh.
        </p>
      )}
      {!hasData && (
        <p className="hormuz-card__unavailable">
          Live PortWatch data will populate on next refresh when the feed is available.
        </p>
      )}
    </article>
  );
}
