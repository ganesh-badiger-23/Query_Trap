/**
 * Strict TypeScript Data Models for Sentinel DB & Query Trap.
 * Mirrors the exact immutable JSON response schemas returned by the Flask APIs.
 */

export type RiskBand = 'safe' | 'suspicious' | 'critical';
export type RouteTarget = 'production' | 'honeypot';
export type EventBucket = 'safe' | 'suspicious' | 'honeypot';

export interface TelemetryEvent {
  id: string;
  timestamp: string;
  ip: string;
  query: string;
  threats: string[];
  risk: number;
  risk_band?: RiskBand | string;
  route: RouteTarget;
  bucket: EventBucket;
  query_class?: string;
  query_type?: string;
  action_taken?: string;
  db_target?: string;
  site_context?: string;
  table?: string;
}

export interface TelemetryCounts {
  safe: number;
  suspicious: number;
  honeypot: number;
}

export interface EventsResponse {
  events: TelemetryEvent[];
  counts: TelemetryCounts;
}

export interface QueryPayload {
  query: string;
  site_context?: string;
  search_term?: string;
}

export interface QueryResponse {
  risk: number;
  risk_band: RiskBand;
  route: RouteTarget;
  bucket: EventBucket;
  table: string;
  site_context: string;
  threats: string[];
  rows: Record<string, unknown>[];
  is_synthetic: boolean;
  handoff: string | null;
  message: string;
}

export interface HandoffPayload {
  query: string;
  risk: number;
  risk_band: string;
  route: string;
  bucket: string;
  table: string;
  site_context: string;
  threats: string[];
  rows: Record<string, unknown>[];
  is_synthetic: boolean;
  source_type: string;
  trigger_channel?: string;
}

export interface DecoyRecordsResponse {
  table: string;
  rows: Record<string, unknown>[];
  is_synthetic: boolean;
  count?: number;
  description?: string;
}

export interface HealthResponse {
  status: string;
  mode: string;
  is_unified: boolean;
  service_port: number;
  events: number;
}

export interface Product {
  id: number;
  item: string;
  category: string;
  price: number;
  description?: string;
  badge?: string;
  tag?: string;
}
