import type { CausalNode } from '../types/api';

interface CausalChainProps {
  nodes: CausalNode[];
}

export function CausalChain({ nodes }: CausalChainProps) {
  return (
    <section className="panel-shell">
      <div className="panel-shell__header">
        <h2>Causal Chain</h2>
        <p>The thesis is encoded directly into node-level stress states, recursive propagation, and regime scoring.</p>
      </div>
      <div className="causal-chain">
        {nodes.map((node) => (
          <article key={node.key} className={`causal-node causal-node--${node.status}`}>
            <div className="causal-node__score">{node.score.toFixed(0)}</div>
            <h3>{node.label}</h3>
            {node.base_score !== null && node.incoming_pressure !== null ? (
              <div className="causal-node__meta">
                <span>Base {node.base_score.toFixed(0)}</span>
                <span>Loop {node.incoming_pressure.toFixed(0)}</span>
              </div>
            ) : null}
            <p>{node.explanation}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
