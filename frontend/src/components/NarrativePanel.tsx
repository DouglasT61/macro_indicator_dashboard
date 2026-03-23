import type { NarrativeBlock } from '../types/api';

interface NarrativePanelProps {
  narratives: NarrativeBlock;
}

export function NarrativePanel({ narratives }: NarrativePanelProps) {
  return (
    <section className="panel-shell narrative-grid">
      <article className="narrative-card">
        <h2>Daily Summary</h2>
        <p>{narratives.daily}</p>
      </article>
      <article className="narrative-card">
        <h2>Weekly Drift</h2>
        <p>{narratives.weekly}</p>
      </article>
      <article className="narrative-card">
        <h2>Stress Escalation</h2>
        <p>{narratives.escalation}</p>
      </article>
    </section>
  );
}
