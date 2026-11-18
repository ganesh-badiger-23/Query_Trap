/**
 * API Service for Sentinel DB / Query Trap backend endpoints.
 * Adapts strictly to fixed Flask API contracts.
 */

import {
  EventsResponse,
  QueryPayload,
  QueryResponse,
  HandoffPayload,
  DecoyRecordsResponse,
  HealthResponse,
} from '../types';

export const SOC_DEFAULT_TOKEN = 'soc_token_live_2026';

// Base URL resolver supporting local multi-service ports and Vite proxy
export const getBaseUrl = (service: 'sentinel' | 'storefront' | 'honeypot'): string => {
  if (typeof window !== 'undefined') {
    const port = window.location.port;
    // When running inside Vite dev server (port 3000), use direct ports or proxy
    if (port === '3000') {
      const portMap = { sentinel: '5100', storefront: '5200', honeypot: '5300' };
      return `http://127.0.0.1:${portMap[service]}`;
    }
  }
  return '';
};

/**
 * Submit untrusted search query or payload to Sentinel Gateway inspection.
 */
export async function inspectQuery(
  payload: QueryPayload,
  baseUrl: string = getBaseUrl('sentinel'),
  token: string = SOC_DEFAULT_TOKEN
): Promise<QueryResponse> {
  const url = `${baseUrl}/api/query${token ? `?token=${encodeURIComponent(token)}` : ''}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Inspection failed with status ${res.status}`);
  }

  return res.json();
}

/**
 * Fetch durable telemetry event history from SQLite production.db (SOC Guarded).
 */
export async function fetchTelemetryEvents(
  baseUrl: string = getBaseUrl('sentinel'),
  token: string = SOC_DEFAULT_TOKEN
): Promise<EventsResponse> {
  const url = `${baseUrl}/api/events${token ? `?token=${encodeURIComponent(token)}` : ''}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('401 Unauthorized: Valid SOC credentials or security token required.');
    }
    throw new Error(`Failed to load telemetry events (${res.status})`);
  }

  return res.json();
}

/**
 * Consume a single-use honeypot redirection handoff token.
 */
export async function fetchHandoffData(
  token: string,
  baseUrl: string = getBaseUrl('honeypot')
): Promise<HandoffPayload> {
  const res = await fetch(`${baseUrl}/api/handoff/${encodeURIComponent(token)}`);
  if (!res.ok) {
    throw new Error('This handoff token has expired or was already consumed.');
  }
  return res.json();
}

/**
 * Fetch records from the Honeypot SQLite replica or synthetic honeytoken generators.
 */
export async function fetchDecoyRecords(
  table: string,
  isSynthetic: boolean = false,
  baseUrl: string = getBaseUrl('honeypot')
): Promise<DecoyRecordsResponse> {
  const params = new URLSearchParams({
    table,
    ...(isSynthetic ? { source: 'synthetic' } : {}),
  });
  const res = await fetch(`${baseUrl}/api/decoy/records?${params.toString()}`);
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error('429 Too Many Requests: Rate limit exceeded (50 req/min).');
    }
    throw new Error(`Failed to fetch decoy records: ${res.status}`);
  }
  return res.json();
}

/**
 * Check service health status.
 */
export async function checkServiceHealth(
  service: 'sentinel' | 'storefront' | 'honeypot'
): Promise<HealthResponse> {
  const res = await fetch(`${getBaseUrl(service)}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
