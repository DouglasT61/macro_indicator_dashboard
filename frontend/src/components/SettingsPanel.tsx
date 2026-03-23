import { useEffect, useMemo, useState } from 'react';

import type { DashboardOverview, ManualInputItem, SettingsResponse } from '../types/api';

interface SettingsPanelProps {
  overview: DashboardOverview;
  settings: SettingsResponse;
  saving: boolean;
  onSaveConfig: (config: Record<string, unknown>) => Promise<void>;
  onToggleAlerts: (enabled: boolean) => Promise<void>;
  onSaveManualInput: (payload: { key: string; value: number; notes: string }) => Promise<void>;
  onSaveEvent: (payload: { title: string; description: string; related_series: string[]; severity: string }) => Promise<void>;
  onImportCsv: (seriesKey: string, file: File) => Promise<void>;
}

const MANUAL_KEYS = [
  'marine_insurance_stress',
  'tanker_disruption_score',
  'private_credit_stress',
  'geopolitical_escalation_toggle',
  'central_bank_intervention_toggle',
  'p_and_i_circular_stress',
  'iaea_nuclear_ambiguity',
  'interceptor_depletion',
  'governance_fragmentation',
];

const MANUAL_HELP: Record<string, string> = {
  marine_insurance_stress: 'Auto-refresh scans Beinsure marine and war-risk articles. You can still override it manually.',
  tanker_disruption_score: 'Auto-refresh uses public shipping sources, currently EIA chokepoint context plus optional AISHub if configured.',
  private_credit_stress: 'Auto-refresh now scores a public proxy basket using BIZD, BKLN, and HYG.',
  geopolitical_escalation_toggle: 'Auto-refresh now scans public news for chokepoint and shipping-escalation headlines and sets this toggle probabilistically.',
  central_bank_intervention_toggle: 'Auto-refresh now scans official Federal Reserve feeds for intervention and liquidity-backstop language.',
  p_and_i_circular_stress: 'Auto-refresh now scans official P&I club circulars and maritime security notices for war-risk cancellation, reinstatement, and listed-area stress.',
  iaea_nuclear_ambiguity: 'Auto-refresh now scans IAEA Iran monitoring pages and statements for verification loss, unresolved safeguards, and high-enrichment ambiguity.',
  interceptor_depletion: 'Auto-refresh now scores public operational updates for sustained interceptor burn-rate pressure and high-tempo strike defense.',
  governance_fragmentation: 'Auto-refresh now scans conflict-event and public statement reporting for contradictory command signals and widening provincial-security fragmentation.',
};

const SOURCE_LABELS: Record<string, string> = {
  marine_insurance_stress: 'Beinsure site scan',
  tanker_disruption_score: 'Public shipping sources',
  private_credit_stress: 'Public private-credit market composite',
  geopolitical_escalation_toggle: 'Public geopolitical news scan',
  central_bank_intervention_toggle: 'Official Federal Reserve feed scan',
  p_and_i_circular_stress: 'Official P&I circular scan',
  iaea_nuclear_ambiguity: 'Official IAEA verification scan',
  interceptor_depletion: 'Operational depletion scan',
  governance_fragmentation: 'Governance fragmentation scan',
};

interface AuditDetails {
  sourceLabel: string;
  checkedAt: string | null;
  itemCount: string | null;
  signal: string | null;
  highlights: string[];
  components: string[];
  extraNotes: string[];
}

function extractField(notes: string, pattern: RegExp): string | null {
  const match = notes.match(pattern);
  return match?.[1]?.trim() ?? null;
}

function splitList(raw: string | null): string[] {
  if (!raw) {
    return [];
  }
  return raw
    .split('|')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function parseAuditNotes(item: ManualInputItem): AuditDetails {
  const notes = item.notes ?? '';
  const sourceLabel = extractField(notes, /source=([^;]+)/) ?? SOURCE_LABELS[item.key] ?? 'Auto-refresh source';
  const checkedAt = extractField(notes, /checked=([^;,]+)/);
  const articleCount = extractField(notes, /articles=(\d+)/);
  const itemCount = articleCount ?? extractField(notes, /items=(\d+)/);
  const signal = extractField(notes, /signal=([0-9.]+)/);
  const highlights = splitList(extractField(notes, /highlights=(.*)$/) ?? extractField(notes, /top=(.*)$/));
  const components = splitList(extractField(notes, /components=(.*)$/));

  const extraNotes = notes
    .split(';')
    .map((entry) => entry.trim())
    .filter(
      (entry) =>
        entry.length > 0 &&
        !entry.startsWith('Auto-scored from') &&
        !entry.startsWith('source=') &&
        !entry.startsWith('checked=') &&
        !entry.startsWith('articles=') &&
        !entry.startsWith('items=') &&
        !entry.startsWith('signal=') &&
        !entry.startsWith('highlights=') &&
        !entry.startsWith('components='),
    );

  return {
    sourceLabel,
    checkedAt,
    itemCount,
    signal,
    highlights,
    components,
    extraNotes,
  };
}

function getAuditStatus(details: AuditDetails): string {
  const itemCount = details.itemCount ? Number(details.itemCount) : null;
  const signal = details.signal ? Number(details.signal) : null;

  if (itemCount === 0 && signal === 0) {
    return 'Scan succeeded. No matching items found on this refresh.';
  }
  if ((itemCount ?? 0) > 0 || (signal ?? 0) > 0) {
    return 'Scan succeeded. Matching items contributed to the current value.';
  }
  return 'Auto-refresh source details parsed from the latest successful scan.';
}

export function SettingsPanel({
  overview,
  settings,
  saving,
  onSaveConfig,
  onToggleAlerts,
  onSaveManualInput,
  onSaveEvent,
  onImportCsv,
}: SettingsPanelProps) {
  const [configText, setConfigText] = useState(() => JSON.stringify(settings.config, null, 2));
  const [manualKey, setManualKey] = useState(MANUAL_KEYS[0]);
  const [manualValue, setManualValue] = useState('60');
  const [manualNotes, setManualNotes] = useState('');
  const [eventTitle, setEventTitle] = useState('');
  const [eventDescription, setEventDescription] = useState('');
  const [eventSeries, setEventSeries] = useState('brent_prompt_spread,jpy_usd_basis');
  const [eventSeverity, setEventSeverity] = useState('warning');
  const [csvSeries, setCsvSeries] = useState('brent_prompt_spread');
  const [csvFile, setCsvFile] = useState<File | null>(null);

  useEffect(() => {
    setConfigText(JSON.stringify(settings.config, null, 2));
  }, [settings.config]);

  const availableSeries = useMemo(
    () => Object.keys((settings.config.thresholds as Record<string, unknown>) ?? {}),
    [settings.config],
  );

  const latestSelectedManual = useMemo(
    () => overview.manual_inputs.find((item) => item.key === manualKey),
    [manualKey, overview.manual_inputs],
  );

  useEffect(() => {
    if (latestSelectedManual) {
      setManualValue(latestSelectedManual.value.toFixed(2));
      setManualNotes(latestSelectedManual.notes ?? '');
      return;
    }
    setManualValue('60');
    setManualNotes('');
  }, [latestSelectedManual]);

  const auditDetails = useMemo(
    () => (latestSelectedManual ? parseAuditNotes(latestSelectedManual) : null),
    [latestSelectedManual],
  );

  const handleConfigSave = async () => {
    const parsed = JSON.parse(configText) as Record<string, unknown>;
    await onSaveConfig(parsed);
  };

  const showAudit = MANUAL_KEYS.includes(manualKey);

  return (
    <section className="panel-shell settings-panel">
      <div className="panel-shell__header">
        <h2>Admin / Settings</h2>
        <p>Thresholds, weights, alert toggle, CSV import, manual overlays, and event annotations.</p>
      </div>
      <div className="settings-grid">
        <article className="settings-card">
          <h3>Threshold and Regime Config</h3>
          <textarea value={configText} onChange={(event) => setConfigText(event.target.value)} rows={18} />
          <button disabled={saving} onClick={() => void handleConfigSave()}>
            Save Config JSON
          </button>
        </article>
        <article className="settings-card">
          <h3>Alert Engine</h3>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={settings.alerts_enabled}
              onChange={(event) => void onToggleAlerts(event.target.checked)}
            />
            Alerts enabled
          </label>
          <h3>Manual Inputs</h3>
          <select value={manualKey} onChange={(event) => setManualKey(event.target.value)}>
            {MANUAL_KEYS.map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
          <p className="settings-help">{MANUAL_HELP[manualKey]}</p>
          {showAudit && latestSelectedManual && auditDetails ? (
            <div className="settings-audit">
              <strong>Auto-Refresh Source</strong>
              <p className="settings-help">{getAuditStatus(auditDetails)}</p>
              <div className="settings-audit__row"><span>Current value</span><span>{latestSelectedManual.value.toFixed(2)}</span></div>
              <div className="settings-audit__row"><span>Updated</span><span>{new Date(latestSelectedManual.timestamp).toLocaleString()}</span></div>
              <div className="settings-audit__row"><span>Source</span><span>{auditDetails.sourceLabel}</span></div>
              {auditDetails.itemCount ? <div className="settings-audit__row"><span>Matched items</span><span>{auditDetails.itemCount}</span></div> : null}
              {auditDetails.signal ? <div className="settings-audit__row"><span>Signal</span><span>{auditDetails.signal}</span></div> : null}
              {auditDetails.checkedAt ? <div className="settings-audit__row"><span>Scan time</span><span>{new Date(auditDetails.checkedAt).toLocaleString()}</span></div> : null}
              {auditDetails.highlights.length ? (
                <div className="settings-audit__block">
                  <span>Highlights</span>
                  <ul className="settings-audit__list">
                    {auditDetails.highlights.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {auditDetails.components.length ? (
                <div className="settings-audit__block">
                  <span>Components</span>
                  <ul className="settings-audit__list">
                    {auditDetails.components.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {auditDetails.extraNotes.length ? (
                <div className="settings-audit__block">
                  <span>Notes</span>
                  <ul className="settings-audit__list">
                    {auditDetails.extraNotes.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
          <input value={manualValue} onChange={(event) => setManualValue(event.target.value)} placeholder="value" />
          <input value={manualNotes} onChange={(event) => setManualNotes(event.target.value)} placeholder="notes / source used" />
          <button
            disabled={saving}
            onClick={() =>
              void onSaveManualInput({ key: manualKey, value: Number(manualValue), notes: manualNotes })
            }
          >
            Save Manual Input
          </button>
        </article>
        <article className="settings-card">
          <h3>Import Custom CSV</h3>
          <select value={csvSeries} onChange={(event) => setCsvSeries(event.target.value)}>
            {availableSeries.map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
          <input type="file" accept=".csv" onChange={(event) => setCsvFile(event.target.files?.[0] ?? null)} />
          <button disabled={saving || !csvFile} onClick={() => csvFile && void onImportCsv(csvSeries, csvFile)}>
            Import CSV
          </button>
          <p className="settings-help">CSV format: timestamp,value with ISO timestamps. Use this for any dataset where you have a better or faster source.</p>
          <h3>Event Annotation / Policy Overlay</h3>
          <input value={eventTitle} onChange={(event) => setEventTitle(event.target.value)} placeholder="Event title" />
          <textarea
            value={eventDescription}
            onChange={(event) => setEventDescription(event.target.value)}
            rows={4}
            placeholder="Why the event matters or what policy probability changed"
          />
          <input
            value={eventSeries}
            onChange={(event) => setEventSeries(event.target.value)}
            placeholder="series keys, comma separated"
          />
          <select value={eventSeverity} onChange={(event) => setEventSeverity(event.target.value)}>
            <option value="info">info</option>
            <option value="warning">warning</option>
            <option value="critical">critical</option>
          </select>
          <button
            disabled={saving}
            onClick={() =>
              void onSaveEvent({
                title: eventTitle,
                description: eventDescription,
                related_series: eventSeries.split(',').map((item) => item.trim()).filter(Boolean),
                severity: eventSeverity,
              })
            }
          >
            Save Event
          </button>
        </article>
      </div>
      <div className="source-status-grid">
        {Object.entries(overview.source_status).map(([key, value]) => (
          <article key={key} className="source-card">
            <h4>{key}</h4>
            <p>{value}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

