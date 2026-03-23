import { useCallback, useEffect, useState } from 'react';

import type { DashboardOverview, SettingsResponse } from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? '/api/v1' : 'http://127.0.0.1:8005/api/v1');

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function useDashboardData() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [overviewData, settingsData] = await Promise.all([
        fetchJson<DashboardOverview>(`${API_BASE}/dashboard/overview`),
        fetchJson<SettingsResponse>(`${API_BASE}/settings/config`),
      ]);
      setOverview(overviewData);
      setSettings(settingsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = useCallback(async () => {
    setSaving(true);
    try {
      await fetchJson(`${API_BASE}/dashboard/refresh`, { method: 'POST' });
      await load();
    } finally {
      setSaving(false);
    }
  }, [load]);

  const saveConfig = useCallback(
    async (config: Record<string, unknown>) => {
      setSaving(true);
      try {
        const response = await fetchJson<SettingsResponse>(`${API_BASE}/settings/config`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
        });
        setSettings(response);
        await load();
      } finally {
        setSaving(false);
      }
    },
    [load],
  );

  const toggleAlerts = useCallback(async (enabled: boolean) => {
    setSaving(true);
    try {
      const response = await fetchJson<SettingsResponse>(`${API_BASE}/settings/alerts-toggle?enabled=${enabled ? 'true' : 'false'}`, {
        method: 'POST',
      });
      setSettings(response);
    } finally {
      setSaving(false);
    }
  }, []);

  const saveManualInput = useCallback(
    async (payload: { key: string; value: number; notes: string }) => {
      setSaving(true);
      try {
        await fetchJson(`${API_BASE}/settings/manual-inputs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        await load();
      } finally {
        setSaving(false);
      }
    },
    [load],
  );

  const saveEvent = useCallback(
    async (payload: { title: string; description: string; related_series: string[]; severity: string }) => {
      setSaving(true);
      try {
        await fetchJson(`${API_BASE}/settings/events`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        await load();
      } finally {
        setSaving(false);
      }
    },
    [load],
  );

  const importCsv = useCallback(
    async (seriesKey: string, file: File) => {
      setSaving(true);
      try {
        const form = new FormData();
        form.append('file', file);
        const response = await fetch(`${API_BASE}/settings/import/${seriesKey}`, {
          method: 'POST',
          body: form,
        });
        if (!response.ok) {
          throw new Error(`Failed to import CSV for ${seriesKey}`);
        }
        await load();
      } finally {
        setSaving(false);
      }
    },
    [load],
  );

  const exportSummary = useCallback(async () => {
    const response = await fetch(`${API_BASE}/dashboard/export/daily-summary`);
    if (!response.ok) {
      throw new Error('Failed to export daily summary.');
    }
    const text = await response.text();
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'macro-dashboard-daily-summary.md';
    link.click();
    URL.revokeObjectURL(url);
  }, []);

  return {
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
  };
}

