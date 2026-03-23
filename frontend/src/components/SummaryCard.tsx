import type { RegimeCard } from '../types/api';

interface SummaryCardProps {
  card: RegimeCard;
  tone: 'sticky' | 'convex' | 'break';
}

export function SummaryCard({ card, tone }: SummaryCardProps) {
  return (
    <article className={`summary-card summary-card--${tone}`}>
      <div className="summary-card__label">{card.name}</div>
      <div className="summary-card__score">{card.score.toFixed(1)}</div>
      <div className="summary-card__delta-row">
        <span>7d {card.change_7d >= 0 ? '+' : ''}{card.change_7d.toFixed(1)}</span>
        <span>30d {card.change_30d >= 0 ? '+' : ''}{card.change_30d.toFixed(1)}</span>
      </div>
      <div className="summary-card__loop">Recursive boost +{card.propagation_boost.toFixed(1)}</div>
      <ul className="summary-card__drivers">
        {card.top_drivers.map((driver) => (
          <li key={driver}>{driver}</li>
        ))}
      </ul>
    </article>
  );
}
