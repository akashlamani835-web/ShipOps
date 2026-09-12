export type HealthStatus = "healthy" | "degraded";

export type ConnectivityState = "available" | "degraded" | "unavailable";

export type ConnectivityStatusResponse = {
  link: {
    name: string;
    state: ConnectivityState;
    capacity_kbps: number;
    available_kbps: number;
  };
  queued_traffic: Array<{
    traffic_id: string;
    traffic_class: string;
    size_kb: number;
    required_kbps: number;
    deadline: number | null;
  }>;
  usage: {
    requests: number;
    transmitted_kbps: number;
    throttled_kbps: number;
    queued_requests: number;
    queued_kbps: number;
  };
};

export type ConnectivityMetricsResponse = {
  traffic: {
    total_requests: number;
    transmitted_requests: number;
    throttled_requests: number;
    queued_requests: number;
  };
  bandwidth_kbps: {
    transmitted: number;
    throttled: number;
    queued: number;
  };
  connectivity_states: {
    available_observations: number;
    degraded_observations: number;
    unavailable_observations: number;
  };
};

export type TrafficClass = "critical" | "high" | "normal" | "low" | "bulk";
export type ConnectivityAction = "transmit" | "throttle" | "queue" | "reject";

export type ConnectivityTrafficDecision = {
  traffic_id: string;
  traffic_class: TrafficClass;
  action: ConnectivityAction;
  allocated_kbps: number;
  reason: string;
};

export type ConnectivityLinkResponse = {
  name: string;
  state: ConnectivityState;
  capacity_kbps: number;
  available_kbps: number;
};

export type ConnectivityRetryResponse = {
  decisions: ConnectivityTrafficDecision[];
  queued_traffic_count: number;
};

export type ConnectivitySimulationResponse = {
  initial_state: ConnectivityState;
  degraded_state: ConnectivityState;
  outage_state: ConnectivityState;
  recovered_state: ConnectivityState;
  critical_action_during_degradation: string;
  bulk_action_during_degradation: string;
  outage_queued_requests: number;
  recovered_transmitted_requests: number;
  final_queued_requests: number;
  transmitted_kbps: number;
  queued_kbps: number;
};

export type HealthResponse = {
  status: HealthStatus;
  service: string;
  environment: string;
  dependencies: {
    postgres: "healthy" | "unhealthy";
    redis: "healthy" | "unhealthy";
  };
};

export type EventSeverity = "info" | "low" | "medium" | "high" | "critical";
export type EventStatus = "open" | "acknowledged" | "resolved";

export type OperationalEvent = {
  id: string;
  asset_id: string;
  rule_id: string;
  event_type: string;
  severity: EventSeverity;
  status: EventStatus;
  occurred_at: string;
  resolved_at: string | null;
  summary: string;
  details: Record<string, unknown>;
  evidence: Array<Record<string, unknown>>;
};

export type EventListResponse = {
  items: OperationalEvent[];
  count: number;
};

export type TopologyGraphResponse = {
  nodes: Array<{
    id: string;
    asset_id: string;
    identifier: string;
    name: string;
  }>;
  edges: Array<{
    source_node_id: string;
    destination_node_id: string;
    operational_up: boolean;
  }>;
};

export type TopologyImpactResponse = {
  root_asset: string;
  affected_assets: string[];
  affected_count: number;
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;

    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // Keep the generic HTTP error when the response is not JSON.
    }

    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export function getHealth() {
  return request<HealthResponse>("/health");
}

export function getConnectivityStatus() {
  return request<ConnectivityStatusResponse>("/connectivity/status");
}

export function getConnectivityMetrics() {
  return request<ConnectivityMetricsResponse>("/connectivity/metrics");
}

export function getEvents(limit = 10) {
  return request<EventListResponse>(`/api/v1/events?limit=${limit}`);
}

export function submitConnectivityTraffic(payload: {
  traffic_id: string;
  traffic_class: TrafficClass;
  size_kb: number;
  required_kbps: number;
  deadline?: number | null;
}) {
  return request<ConnectivityTrafficDecision>("/connectivity/traffic", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateConnectivityLink(
  state: ConnectivityState,
  availableKbps: number,
) {
  const params = new URLSearchParams({
    state,
    available_kbps: String(availableKbps),
  });

  return request<ConnectivityLinkResponse>(
    `/connectivity/link?${params.toString()}`,
    {
      method: "POST",
    },
  );
}

export function retryConnectivityQueue() {
  return request<ConnectivityRetryResponse>("/connectivity/retry", {
    method: "POST",
  });
}

export function runConnectivitySimulation() {
  return request<ConnectivitySimulationResponse>("/connectivity/simulate", {
    method: "POST",
  });
}

export function getTopologyGraph() {
  return request<TopologyGraphResponse>("/api/v1/topology/graph");
}

export function getTopologyImpact(identifier: string) {
  return request<TopologyImpactResponse>(
    `/api/v1/topology/assets/${encodeURIComponent(identifier)}/impact`,
  );
}

export type RCAEventCandidate = {
  asset_id: string;
  identifier: string;
  asset_type: string;
  distance: number;
  score: number;
  telemetry_support: number;
  shared_event_support: number;
  reasons: string[];
};

export type RCAEventResponse = {
  event_id: string;
  affected_asset_id: string;
  affected_asset_identifier: string;
  root_cause_asset_id: string | null;
  root_cause_identifier: string | null;
  confidence: number;
  severity: string;
  explanation: string;
  candidates: RCAEventCandidate[];
};

export type RCAClusterResponse = {
  event_ids: string[];
  affected_asset_ids: string[];
  affected_asset_identifiers: string[];
  root_cause_asset_id: string | null;
  root_cause_identifier: string | null;
  confidence: number;
  severity: string;
  explanation: string;
  candidates: RCAEventCandidate[];
};

export type TelemetryIngestResponse = {
  id?: string;
  asset_id?: string;
  asset_identifier?: string;
  metric?: string;
  value?: number;
  unit?: string;
  observed_at?: string;
  received_at?: string;
  source?: string;
  source_sequence?: number;
  quality?: string;
  idempotency_key?: string | null;
  accepted?: boolean;
  event_created?: boolean;
  detail?: string;
  [key: string]: unknown;
};

export function submitTelemetry(payload: {
  asset_identifier: string;
  metric: string;
  value: number;
  unit: string;
  observed_at: string;
  received_at?: string;
  source: string;
  source_sequence: number;
  quality: string;
  idempotency_key?: string;
  extra_data?: Record<string, unknown>;
}) {
  return request<TelemetryIngestResponse>("/api/v1/telemetry", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getEvent(eventId: string) {
  return request<OperationalEvent>(
    `/api/v1/events/${encodeURIComponent(eventId)}`,
  );
}

export function acknowledgeEvent(eventId: string) {
  return request<OperationalEvent>(
    `/api/v1/events/${encodeURIComponent(eventId)}/acknowledge`,
    {
      method: "POST",
    },
  );
}

export function resolveEvent(eventId: string) {
  return request<OperationalEvent>(
    `/api/v1/events/${encodeURIComponent(eventId)}/resolve`,
    {
      method: "POST",
    },
  );
}

export function getRCAEvent(eventId: string) {
  return request<RCAEventResponse>(
    `/api/v1/rca/events/${encodeURIComponent(eventId)}`,
  );
}

export function getRCACluster(eventIds: string[]) {
  return request<RCAClusterResponse>("/api/v1/rca/clusters", {
    method: "POST",
    body: JSON.stringify({
      event_ids: eventIds,
    }),
  });
}
