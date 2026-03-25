import { useState, type ReactNode } from 'react';

import guideContent from '../../../docs/macro_stress_dashboard_user_guide.md.txt?raw';
import { AboutAppModal } from '../components/AboutAppModal';
import { AdvancedAnalyticsModal } from '../components/AdvancedAnalyticsModal';
import { AlertList } from '../components/AlertList';
import { CausalChain } from '../components/CausalChain';
import { CrisisMonitor } from '../components/CrisisMonitor';
import { EpisodeComparisonPanel } from '../components/EpisodeComparisonPanel';
import { NarrativePanel } from '../components/NarrativePanel';
import { PanelSection } from '../components/PanelSection';
import { SettingsPanel } from '../components/SettingsPanel';
import { StateSpacePanel } from '../components/StateSpacePanel';
import { SummaryCard } from '../components/SummaryCard';
import { LineChart } from '../charts/LineChart';
import { useDashboardData } from '../hooks/useDashboardData';
import type { IndicatorSnapshot, Panel } from '../types/api';

const REGIME_COLORS = {
  sticky: '#f59e0b',
  convex: '#38bdf8',
  break: '#ef4444',
};

const TAB_LABELS = {
  executive: 'Executive',
  markets: 'Markets',
  domestic: 'Domestic',
  settings: 'Settings',
} as const;

type TabKey = keyof typeof TAB_LABELS;


const REGIME_RANGE_LEGEND = [
  {
    range: '0-44',
    sticky: 'background',
    convex: 'not migrated',
    breakRisk: 'low',
  },
  {
    range: '45-59',
    sticky: 'building',
    convex: 'transition',
    breakRisk: 'building',
  },
  {
    range: '60-74',
    sticky: 'active',
    convex: 'active',
    breakRisk: 'active',
  },
  {
    range: '75-100',
    sticky: 'dominant',
    convex: 'dominant',
    breakRisk: 'dominant',
  },
] as const;

interface CollapsibleSectionProps {
  title: string;
  description: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

interface NavItem {
  id: string;
  label: string;
  count?: number;
}

function CollapsibleSection({ title, description, defaultOpen = false, children }: CollapsibleSectionProps) {
  return (
    <details className="panel-accordion" open={defaultOpen}>
      <summary className="panel-accordion__summary">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </summary>
      <div className="panel-accordion__content">{children}</div>
    </details>
  );
}

function countStressedIndicators(indicators: IndicatorSnapshot[]) {
  return indicators.filter((indicator) => indicator.status === 'orange' || indicator.status === 'red').length;
}

function countPanelStress(panels: Panel[]) {
  return panels.reduce((total, panel) => total + countStressedIndicators(panel.indicators), 0);
}

function buildNavItems(activeTab: TabKey, overview: NonNullable<ReturnType<typeof useDashboardData>['overview']>): NavItem[] {
  if (activeTab === 'executive') {
    return [
      { id: 'executive-regime', label: 'Regime View' },
      { id: 'executive-ordering', label: 'Ordering Discipline' },
      { id: 'executive-stagflation', label: 'Stagflation' },
      { id: 'executive-migration', label: 'Physical vs Financial' },
      { id: 'executive-interpretation', label: 'Score History' },
      { id: 'executive-interpretation-rule', label: 'Interpretation Rule' },
      { id: 'executive-headline', label: 'Critical Indicators', count: countStressedIndicators(overview.headline_indicators) },
      { id: 'executive-crisis', label: 'Fast Stress Panel', count: overview.crisis_monitor.filter((signal) => signal.status === 'orange' || signal.status === 'red').length },
      { id: 'executive-chain', label: 'Causal Chain', count: overview.causal_chain.filter((node) => node.status !== 'green').length },
      { id: 'executive-narratives', label: 'Narratives' },
      { id: 'executive-alerts', label: 'Alerts', count: overview.alerts.filter((alert) => alert.severity !== 'info').length },
    ];
  }

  if (activeTab === 'markets') {
    return [
      { id: 'markets-oil', label: 'Oil / Shipping', count: countPanelStress(overview.panels.oil_shipping ?? []) },
      { id: 'markets-funding', label: 'Funding / Plumbing', count: countPanelStress(overview.panels.funding ?? []) },
      { id: 'markets-ust', label: 'UST / Funding', count: countPanelStress(overview.panels.ust_funding ?? []) },
    ];
  }

  if (activeTab === 'domestic') {
    return [
      { id: 'domestic-employment', label: 'Employment / Receipts', count: countPanelStress(overview.panels.employment ?? []) },
      { id: 'domestic-consumer', label: 'Consumer / Fiscal / Credit', count: countPanelStress(overview.panels.consumer_credit ?? []) },
      { id: 'domestic-assets', label: 'Asset Regime', count: countPanelStress(overview.panels.asset_regime ?? []) },
    ];
  }

  return [{ id: 'settings-main', label: 'Settings and Inputs' }];
}

export function DashboardPage() {
  const [aboutOpen, setAboutOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>('executive');
  const {
    overview,
    settings,
    loading,
    saving,
    error,
    refresh,
    saveConfig,
    toggleAlerts,
    saveManualInput,
    saveEvent,
    importCsv,
    exportSummary,
  } = useDashboardData();

  if (loading) {
    return <div className="screen-state">Loading macro stress dashboard...</div>;
  }

  if (error || !overview || !settings) {
    return <div className="screen-state screen-state--error">Unable to load dashboard: {error}</div>;
  }

  const interpretationChart = overview.interpretation_chart ?? { series: [], thresholds: [] };
  const sourceIssues = overview.headline_indicators.filter((indicator) => indicator.source_class !== 'live');
  const sourceIssueLabels = Array.from(
    new Set(
      sourceIssues.map((indicator) => {
        if (indicator.source_class === 'demo') {
          return 'unavailable/demo';
        }
        if (indicator.source_class === 'support') {
          return 'support-derived';
        }
        return indicator.source_class;
      }),
    ),
  );
  const navItems = buildNavItems(activeTab, overview);
  const tabCounts = {
    executive: countStressedIndicators(overview.headline_indicators) + overview.alerts.filter((alert) => alert.severity !== 'info').length,
    markets: countPanelStress([...(overview.panels.oil_shipping ?? []), ...(overview.panels.funding ?? []), ...(overview.panels.ust_funding ?? [])]),
    domestic: countPanelStress([...(overview.panels.employment ?? []), ...(overview.panels.consumer_credit ?? []), ...(overview.panels.asset_regime ?? [])]),
    settings: 0,
  } satisfies Record<TabKey, number>;
  const advancedCount = overview.state_space.forecast.scenarios.filter((scenario) => scenario.break >= 35).length;

  return (
    <main className="app-shell">
      <header className="hero-bar">
        <div>
          <div className="hero-bar__eyebrow-row">
            <button className="hero-bar__about-link" onClick={() => setAboutOpen(true)} type="button">
              About This App
            </button>
            <p className="eyebrow">Local Macro Stress Monitor</p>
          </div>
          <h1>Marine Shock to Treasury Plumbing Dashboard</h1>
          <p className="hero-bar__subtext">
            Tracks the path from shipping disruption and oil scarcity into dollar funding stress, Treasury dysfunction, and repression risk.
          </p>
        </div>
        <div className="hero-bar__actions">
          <button disabled={saving} onClick={() => void refresh()}>
            {saving ? 'Refreshing...' : 'Manual Refresh'}
          </button>
          <button className="button-secondary" onClick={() => void exportSummary()}>
            Export Daily Markdown
          </button>
          <button className="button-secondary" onClick={() => setAdvancedOpen(true)} type="button">
            Advanced Analytics
          </button>
        </div>
      </header>

      <AboutAppModal content={guideContent} onClose={() => setAboutOpen(false)} open={aboutOpen} />
      <AdvancedAnalyticsModal onClose={() => setAdvancedOpen(false)} open={advancedOpen}>
        <div className="tab-stack">
          <CollapsibleSection title="Econometric Layer" description="State-space regime inference, diagnostics, calibration, and forecast." defaultOpen>
            <StateSpacePanel stateSpace={overview.state_space} />
          </CollapsibleSection>
          <CollapsibleSection title="Historical Analogs" description="Episode comparison, clustering, and analog fit.">
            <EpisodeComparisonPanel backtest={overview.backtest} />
          </CollapsibleSection>
        </div>
      </AdvancedAnalyticsModal>

      {sourceIssues.length > 0 ? (
        <section className="data-warning-banner">
          <strong>Source note.</strong>
          <span>
            {sourceIssues.length} headline indicator{sourceIssues.length === 1 ? '' : 's'} currently use {sourceIssueLabels.join(', ')} inputs. The dashboard remains usable, but those cards should be read according to their source badge rather than as direct market prints.
          </span>
        </section>
      ) : null}

      <div className="dashboard-frame">
        <aside className="dashboard-sidebar">
          <section className="dashboard-sidebar__section">
            <p className="dashboard-sidebar__title">Workspace</p>
            <nav className="dashboard-sidebar__tabs" aria-label="Dashboard tabs">
              {(Object.entries(TAB_LABELS) as Array<[TabKey, string]>).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  className={`dashboard-tab ${activeTab === key ? 'dashboard-tab--active' : ''}`}
                  onClick={() => setActiveTab(key)}
                >
                  <span>{label}</span>
                  {tabCounts[key] > 0 ? <span className="dashboard-sidebar__count">{tabCounts[key]}</span> : null}
                </button>
              ))}
            </nav>
          </section>

          <section className="dashboard-sidebar__section">
            <div className="dashboard-sidebar__section-header">
              <p className="dashboard-sidebar__title">On This Page</p>
              <span className="dashboard-sidebar__subtitle">Jump links with warning counts</span>
            </div>
            <nav className="dashboard-sidebar__links" aria-label="Section links">
              {navItems.map((item) => (
                <a key={item.id} className="dashboard-sidebar__link" href={`#${item.id}`}>
                  <span>{item.label}</span>
                  {item.count && item.count > 0 ? <span className="dashboard-sidebar__count">{item.count}</span> : null}
                </a>
              ))}
            </nav>
          </section>

          <section className="dashboard-sidebar__section">
            <button className="dashboard-sidebar__advanced" onClick={() => setAdvancedOpen(true)} type="button">
              <span>Advanced Analytics</span>
              {advancedCount > 0 ? <span className="dashboard-sidebar__count">{advancedCount}</span> : null}
            </button>
            <p className="dashboard-sidebar__hint">Models, calibration, diagnostics, and historical analogs now live outside the main scroll path.</p>
          </section>
        </aside>

        <div className="dashboard-content">
          {activeTab === 'executive' ? (
            <section className="tab-stack">
              <section className="dashboard-anchor regime-summary-block" id="executive-regime">
                <div className="regime-legend">
                  <div className="regime-legend__header">
                    <div>
                      <h2>Regime Score Legend</h2>
                      <p>Each card is a 0-100 absolute score. Read the number against these band thresholds before comparing it to the other regimes.</p>
                    </div>
                  </div>
                  <div className="regime-legend__grid">
                    {REGIME_RANGE_LEGEND.map((row) => (
                      <article key={row.range} className="regime-legend__item">
                        <strong>{row.range}</strong>
                        <span>Sticky: {row.sticky}</span>
                        <span>Convex: {row.convex}</span>
                        <span>Break: {row.breakRisk}</span>
                      </article>
                    ))}
                  </div>
                </div>
                <section className="summary-grid">
                  <SummaryCard card={overview.regime.sticky} tone="sticky" />
                  <SummaryCard card={overview.regime.convex} tone="convex" />
                  <SummaryCard card={overview.regime.break} tone="break" />
                </section>
              </section>


              <section className="dashboard-anchor" id="executive-ordering">
                <CollapsibleSection title="Ordering Discipline" description="Sequence the shock correctly before comparing late-stage financial variables." defaultOpen>
                  <section className="executive-insight-grid">
                      <article className="executive-insight-card">
                        <h3>Framework</h3>
                        <p>{overview.ordering_framework.summary}</p>
                        <div className="executive-insight-card__metric">
                          Lead stage: {overview.ordering_framework.lead_stage} ({overview.ordering_framework.lead_score.toFixed(1)}, {overview.ordering_framework.lead_confidence_label})
                        </div>
                      </article>
                      <article className="executive-insight-card">
                        <h3>Stage Scores</h3>
                        <div className="executive-stage-list">
                          {overview.ordering_framework.items.map((item) => (
                            <div key={item.label} className="executive-stage-row">
                              <div className="executive-stage-row__label-group">
                                <span>{item.label}</span>
                                <span className="executive-stage-row__confidence">{item.confidence_label}</span>
                              </div>
                              <div className="executive-stage-row__bar">
                                <div className={`executive-stage-row__fill executive-stage-row__fill--${item.status}`} style={{ width: `${Math.min(100, item.score)}%` }} />
                              </div>
                              <strong>{item.score.toFixed(1)}</strong>
                            </div>
                        ))}
                      </div>
                    </article>
                  </section>
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-stagflation">
                <CollapsibleSection title="Stagflation Layer" description="Inflation pressure, weaker real activity, and policy constraint considered together.">
                  <section className="executive-insight-grid">
                    <article className="executive-insight-card">
                      <h3>Composite</h3>
                      <div className="executive-insight-card__score">{overview.stagflation_overview.composite_score.toFixed(1)}</div>
                      <p>{overview.stagflation_overview.summary}</p>
                    </article>
                    <article className="executive-insight-card">
                      <h3>Components</h3>
                      <div className="executive-insight-card__metric-grid">
                        <span>Inflation pressure</span><strong>{overview.stagflation_overview.inflation_score.toFixed(1)}</strong>
                        <span>Growth impairment</span><strong>{overview.stagflation_overview.growth_score.toFixed(1)}</strong>
                        <span>Policy constraint</span><strong>{overview.stagflation_overview.policy_constraint_score.toFixed(1)}</strong>
                      </div>
                    </article>
                  </section>
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-migration">
                <CollapsibleSection title="Physical vs Financial Migration" description="Separates the physical oil shock from the financial-system response.">
                  <section className="executive-insight-grid">
                    <article className="executive-insight-card">
                      <h3>Migration Summary</h3>
                      <p>{overview.migration_overview.summary}</p>
                      <div className="executive-insight-card__metric">Financial minus physical: {overview.migration_overview.financial_minus_physical.toFixed(1)}</div>
                    </article>
                    <article className="executive-insight-card">
                      <h3>Node Scores</h3>
                      <div className="executive-insight-card__metric-grid">
                        <span>Physical</span><strong>{overview.migration_overview.physical_score.toFixed(1)}</strong>
                        <span>Domestic</span><strong>{overview.migration_overview.domestic_score.toFixed(1)}</strong>
                        <span>Financial</span><strong>{overview.migration_overview.financial_score.toFixed(1)}</strong>
                      </div>
                    </article>
                  </section>
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-interpretation">
                <CollapsibleSection title="Executive Regime View" description={`Updated ${new Date(overview.generated_at).toLocaleString()} | Data mode: ${overview.data_mode}`} defaultOpen>
                  <LineChart
                    title="Regime Score History"
                    series={[
                      { name: 'Sticky', color: REGIME_COLORS.sticky, values: overview.regime.history.map((row) => ({ timestamp: row.timestamp, value: row.sticky_score })) },
                      { name: 'Convex', color: REGIME_COLORS.convex, values: overview.regime.history.map((row) => ({ timestamp: row.timestamp, value: row.convex_score })) },
                      { name: 'Break', color: REGIME_COLORS.break, values: overview.regime.history.map((row) => ({ timestamp: row.timestamp, value: row.break_score })) },
                    ]}
                  />
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-interpretation-rule">
                <CollapsibleSection title="Practical Interpretation Rule" description="Single-line composite of oil stress, funding stress, and break-risk inputs with interpretation thresholds.">
                  <LineChart
                    title="Practical Interpretation Composite"
                    series={[
                      {
                        name: 'Interpretation Composite',
                        color: '#c084fc',
                        values: interpretationChart.series,
                      },
                    ]}
                    thresholdLines={interpretationChart.thresholds}
                    height={260}
                  />
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-headline">
                <PanelSection
                  title="Critical Panels Above the Fold"
                  description="Brent spread, JPY basis, SOFR spread, MOVE, 10Y/30Y yields, FIMA usage, and the regime cards stay in view first."
                  panels={[
                    {
                      id: 'headline',
                      title: 'Critical Indicators',
                      description: 'Fast view of the highest-value systemic signals.',
                      indicators: overview.headline_indicators,
                    },
                  ]}
                  events={overview.event_annotations}
                />
              </section>

              <section className="dashboard-anchor" id="executive-crisis">
                <CollapsibleSection title="Fast-Moving Stress Panel" description="Simultaneity trigger for the fastest plumbing and oil-stress indicators.">
                  <CrisisMonitor signals={overview.crisis_monitor} active={overview.systemic_stress_alert} />
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-chain">
                <CollapsibleSection title="Causal Chain" description="Base stress and recursive loop pressure across the transmission path.">
                  <CausalChain nodes={overview.causal_chain} />
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-narratives">
                <CollapsibleSection title="Narratives" description="Daily, weekly, and escalation interpretations from the current state.">
                  <NarrativePanel narratives={overview.narratives} />
                </CollapsibleSection>
              </section>

              <section className="dashboard-anchor" id="executive-alerts">
                <CollapsibleSection title="Alerts" description="Current operational alerts across thresholds, combinations, and econometric escalation.">
                  <AlertList alerts={overview.alerts} />
                </CollapsibleSection>
              </section>
            </section>
          ) : null}

          {activeTab === 'markets' ? (
            <section className="tab-stack">
              <section className="dashboard-anchor" id="markets-oil">
                <PanelSection
                  title="Oil / Shipping View"
                  description="Marine insurance, tanker freight, crude dislocation, and physical tightness."
                  panels={overview.panels.oil_shipping ?? []}
                  events={overview.event_annotations}
                  compact
                />
              </section>
              <section className="dashboard-anchor" id="markets-funding">
                <PanelSection
                  title="Dollar Funding / Plumbing View"
                  description="Cross-currency basis, repo stress, Treasury depth, and Fed swap lines."
                  panels={overview.panels.funding ?? []}
                  events={overview.event_annotations}
                  compact
                />
              </section>
              <section className="dashboard-anchor" id="markets-ust">
                <PanelSection
                  title="UST / Funding View"
                  description="Duration clearing, yields, auction performance, and FIMA usage."
                  panels={overview.panels.ust_funding ?? []}
                  events={overview.event_annotations}
                  compact
                />
              </section>
            </section>
          ) : null}

          {activeTab === 'domestic' ? (
            <section className="tab-stack">
              <section className="dashboard-anchor" id="domestic-employment">
                <PanelSection
                  title="Employment / Receipts / Household Credit View"
                  description="BLS labor data translated into withholding-tax, household-credit, and labor-demand stress."
                  panels={overview.panels.employment ?? []}
                  events={overview.event_annotations}
                  compact
                />
              </section>
              <section className="dashboard-anchor" id="domestic-consumer">
                <PanelSection
                  title="Consumer / Fiscal / Credit View"
                  description="Consumer stress, fiscal quality, deficits, and private credit pressure."
                  panels={overview.panels.consumer_credit ?? []}
                  events={overview.event_annotations}
                  compact
                />
              </section>
              <section className="dashboard-anchor" id="domestic-assets">
                <PanelSection
                  title="Asset Regime View"
                  description="Nominals, inflation hedges, credit spreads, oil, and the dollar."
                  panels={overview.panels.asset_regime ?? []}
                  events={overview.event_annotations}
                  compact
                />
              </section>
            </section>
          ) : null}

          {activeTab === 'settings' ? (
            <section className="tab-stack dashboard-anchor" id="settings-main">
              <SettingsPanel
                overview={overview}
                settings={settings}
                saving={saving}
                onSaveConfig={saveConfig}
                onToggleAlerts={toggleAlerts}
                onSaveManualInput={saveManualInput}
                onSaveEvent={saveEvent}
                onImportCsv={importCsv}
              />
            </section>
          ) : null}
        </div>
      </div>
    </main>
  );
}

