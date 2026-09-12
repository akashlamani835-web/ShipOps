import { useEffect, useState } from "react";
import {
  getConnectivityMetrics,
  getConnectivityStatus,
  submitConnectivityTraffic,
  updateConnectivityLink,
  retryConnectivityQueue,
  runConnectivitySimulation,
  getHealth,
  getEvents,
  getEvent,
  acknowledgeEvent,
  resolveEvent,
  getRCAEvent,
  getRCACluster,
  submitTelemetry,
  getTopologyGraph,
  getTopologyImpact,
  type ConnectivityMetricsResponse,
  type ConnectivityStatusResponse,
  type ConnectivityTrafficDecision,
  type ConnectivityRetryResponse,
  type ConnectivitySimulationResponse,
  type RCAEventResponse,
  type RCAEventCandidate,
  type RCAClusterResponse,
  type TelemetryIngestResponse,
  type TrafficClass,
  type ConnectivityState,
  type HealthResponse,
  type OperationalEvent,
  type EventSeverity,
  type EventStatus,
  type TopologyGraphResponse,
  type TopologyImpactResponse,
} from "./services/api";

type IconName =
  | "overview"
  | "topology"
  | "connectivity"
  | "incidents"
  | "rca"
  | "telemetry"
  | "settings"
  | "search"
  | "bell"
  | "chevron"
  | "external"
  | "pulse"
  | "network"
  | "warning"
  | "activity"
  | "shield";

type NavItem = {
  label: string;
  icon: IconName;
  badge?: string;
};

const primaryNavigation: NavItem[] = [
  { label: "Overview", icon: "overview" },
  { label: "Network Topology", icon: "topology" },
  { label: "Connectivity", icon: "connectivity" },
  { label: "Incidents", icon: "incidents" },
  { label: "Root Cause", icon: "rca" },
  { label: "Telemetry", icon: "telemetry" },
];

function Icon({
  name,
  size = 18,
  strokeWidth = 1.8,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
}) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "overview":
      return (
        <svg {...common}>
          <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
          <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
          <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
          <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
        </svg>
      );

    case "topology":
      return (
        <svg {...common}>
          <circle cx="6" cy="6" r="2.5" />
          <circle cx="18" cy="6" r="2.5" />
          <circle cx="12" cy="18" r="2.5" />
          <path d="M8.3 7.2 10.7 16" />
          <path d="m15.7 7.2-2.4 8.8" />
          <path d="M8.5 6h7" />
        </svg>
      );

    case "connectivity":
      return (
        <svg {...common}>
          <path d="M5 12.5a10 10 0 0 1 14 0" />
          <path d="M7.8 15.5a6 6 0 0 1 8.4 0" />
          <path d="M10.7 18.3a2 2 0 0 1 2.6 0" />
          <circle
            cx="12"
            cy="20"
            r=".75"
            fill="currentColor"
            stroke="none"
          />
        </svg>
      );

    case "incidents":
      return (
        <svg {...common}>
          <path d="M12 3.7 21 19H3L12 3.7Z" />
          <path d="M12 9.2v4.5" />
          <circle
            cx="12"
            cy="16.4"
            r=".8"
            fill="currentColor"
            stroke="none"
          />
        </svg>
      );

    case "rca":
      return (
        <svg {...common}>
          <path d="M12 3.5v17" />
          <path d="M12 7.5h6" />
          <path d="M12 16.5h6" />
          <path d="M6 7.5h2" />
          <path d="M6 16.5h2" />
          <circle cx="5" cy="7.5" r="1.5" />
          <circle cx="5" cy="16.5" r="1.5" />
          <circle cx="19" cy="7.5" r="1.5" />
          <circle cx="19" cy="16.5" r="1.5" />
        </svg>
      );

    case "telemetry":
      return (
        <svg {...common}>
          <path d="M4 17.5V13" />
          <path d="M8 17.5V9.5" />
          <path d="M12 17.5V6.5" />
          <path d="M16 17.5v-5" />
          <path d="M20 17.5V8" />
          <path d="M3.5 20.5h17" />
        </svg>
      );

    case "settings":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3.2" />
          <path d="M19.4 15a1.8 1.8 0 0 0 .3 2l.1.1-1.7 1.7-.1-.1a1.8 1.8 0 0 0-2-.3 1.8 1.8 0 0 0-1.1 1.6V20h-2.4v-.2a1.8 1.8 0 0 0-1.1-1.6 1.8 1.8 0 0 0-2 .3l-.1.1-1.7-1.7.1-.1a1.8 1.8 0 0 0 .3-2 1.8 1.8 0 0 0-1.6-1.1H6v-2.4h.2a1.8 1.8 0 0 0 1.6-1.1 1.8 1.8 0 0 0-.3-2l-.1-.1 1.7-1.7.1.1a1.8 1.8 0 0 0 2 .3 1.8 1.8 0 0 0 1.1-1.6V5h2.4v.2a1.8 1.8 0 0 0 1.1 1.6 1.8 1.8 0 0 0 2-.3l.1-.1 1.7 1.7-.1.1a1.8 1.8 0 0 0-.3 2 1.8 1.8 0 0 0 1.6 1.1h.2v2.4h-.2a1.8 1.8 0 0 0-1.4 1.3Z" />
        </svg>
      );

    case "search":
      return (
        <svg {...common}>
          <circle cx="10.8" cy="10.8" r="6.4" />
          <path d="m16 16 4.3 4.3" />
        </svg>
      );

    case "bell":
      return (
        <svg {...common}>
          <path d="M18 9.8a6 6 0 0 0-12 0c0 7-2.5 7-2.5 8.5h17C20.5 16.8 18 16.8 18 9.8Z" />
          <path d="M10 20.2a2.2 2.2 0 0 0 4 0" />
        </svg>
      );

    case "chevron":
      return (
        <svg {...common}>
          <path d="m9 6 6 6-6 6" />
        </svg>
      );

    case "external":
      return (
        <svg {...common}>
          <path d="M14 5h5v5" />
          <path d="m19 5-8.2 8.2" />
          <path d="M18 13.5V18a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 18V7.5A1.5 1.5 0 0 1 6 6h4.5" />
        </svg>
      );

    case "pulse":
      return (
        <svg {...common}>
          <path d="M3 12h4l2.1-5 3.1 10 2.1-5H21" />
        </svg>
      );

    case "network":
      return (
        <svg {...common}>
          <rect x="3.5" y="4" width="6" height="5" rx="1.2" />
          <rect x="14.5" y="4" width="6" height="5" rx="1.2" />
          <rect x="9" y="15" width="6" height="5" rx="1.2" />
          <path d="M9.5 6.5h5" />
          <path d="M12 9v6" />
        </svg>
      );

    case "warning":
      return (
        <svg {...common}>
          <path d="M12 4 21 19H3L12 4Z" />
          <path d="M12 9.5v4.2" />
          <circle
            cx="12"
            cy="16.4"
            r=".7"
            fill="currentColor"
            stroke="none"
          />
        </svg>
      );

    case "activity":
      return (
        <svg {...common}>
          <path d="M3 12h4l2.2-6 3.5 12L15 12h6" />
        </svg>
      );

    case "shield":
      return (
        <svg {...common}>
          <path d="M12 3.5 19 6v5.3c0 4.5-2.9 7.8-7 9.2-4.1-1.4-7-4.7-7-9.2V6l7-2.5Z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      );

    default:
      return null;
  }
}

function StatusDot({
  tone,
  label,
}: {
  tone: "healthy" | "warning" | "critical" | "neutral";
  label: string;
}) {
  return (
    <span className={`status-pill status-pill--${tone}`}>
      <span className="status-dot" />
      {label}
    </span>
  );
}

function MetricCard({
  label,
  value,
  helper,
  tone = "neutral",
  icon,
}: {
  label: string;
  value: string;
  helper: string;
  tone?: "healthy" | "warning" | "critical" | "neutral";
  icon: IconName;
}) {
  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span className={`metric-icon metric-icon--${tone}`}>
          <Icon name={icon} size={17} />
        </span>

        <span className="metric-card__label">{label}</span>
      </div>

      <div className="metric-card__value">{value}</div>

      <div className="metric-card__helper">
        <span className={`helper-dot helper-dot--${tone}`} />
        {helper}
      </div>
    </article>
  );
}

function ConnectivityGauge({
  connectivity,
}: {
  connectivity: ConnectivityStatusResponse | null;
}) {
  const capacity = connectivity?.link.capacity_kbps ?? 0;
  const available = connectivity?.link.available_kbps ?? 0;
  const used = Math.max(capacity - available, 0);
  const utilization = capacity > 0 ? Math.round((used / capacity) * 100) : 0;
  const linkState = connectivity?.link.state ?? "unknown";
  const linkTone =
    linkState === "available"
      ? "healthy"
      : linkState === "degraded"
        ? "warning"
        : "critical";

  return (
    <div className="connectivity-gauge">
      <div className="gauge-ring">
        <div className="gauge-ring__inner">
          <span className="gauge-ring__value">
            {connectivity ? available.toLocaleString() : "—"}
          </span>
          <span className="gauge-ring__unit">
            Kbps available
          </span>
        </div>
      </div>

      <div className="gauge-meta">
        <div>
          <span>Capacity</span>
          <strong>
            {connectivity ? `${capacity.toLocaleString()} Kbps` : "—"}
          </strong>
        </div>

        <div>
          <span>Utilization</span>
          <strong>{connectivity ? `${utilization}%` : "—"}</strong>
        </div>

        <div>
          <span>Link state</span>
          <strong className={`text-${linkTone}`}>
            {connectivity ? linkState.replace("_", " ") : "Checking"}
          </strong>
        </div>
      </div>
    </div>
  );
}

function MiniSparkline() {
  const points = [
    [0, 30],
    [18, 26],
    [34, 31],
    [50, 20],
    [68, 25],
    [84, 17],
    [100, 21],
  ];

  const path = points
    .map(
      ([x, y], index) =>
        `${index === 0 ? "M" : "L"} ${x} ${y}`,
    )
    .join(" ");

  return (
    <svg
      className="mini-sparkline"
      viewBox="0 0 100 40"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
    </svg>
  );
}

function TopologyPreview() {
  return (
    <div className="topology-preview">
      <div className="topology-line topology-line--vertical" />

      <div className="topology-node topology-node--router">
        <span className="node-status node-status--healthy" />

        <span className="topology-node__icon">
          <Icon name="network" size={16} />
        </span>

        <div>
          <strong>R1</strong>
          <span>Core router</span>
        </div>
      </div>

      <div className="topology-node topology-node--switch">
        <span className="node-status node-status--healthy" />

        <span className="topology-node__icon">
          <Icon name="network" size={16} />
        </span>

        <div>
          <strong>SW-07</strong>
          <span>Distribution</span>
        </div>
      </div>

      <div className="topology-children">
        <div className="topology-branch">
          <span className="branch-line" />

          <div className="topology-node topology-node--small">
            <span className="node-status node-status--healthy" />

            <div>
              <strong>AP1</strong>
              <span>6 endpoints</span>
            </div>
          </div>
        </div>

        <div className="topology-branch">
          <span className="branch-line" />

          <div className="topology-node topology-node--small topology-node--warning">
            <span className="node-status node-status--warning" />

            <div>
              <strong>AP2</strong>
              <span>degraded</span>
            </div>
          </div>
        </div>

        <div className="topology-branch">
          <span className="branch-line" />

          <div className="topology-node topology-node--small">
            <span className="node-status node-status--healthy" />

            <div>
              <strong>POS cluster</strong>
              <span>4 endpoints</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function IncidentRow({
  severity,
  title,
  detail,
  time,
}: {
  severity: "critical" | "high" | "medium";
  title: string;
  detail: string;
  time: string;
}) {
  return (
    <div className="incident-row">
      <div
        className={`incident-severity incident-severity--${severity}`}
      >
        <Icon name="warning" size={15} />
      </div>

      <div className="incident-row__main">
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>

      <time>{time}</time>
    </div>
  );
}

function formatEventTime(value: string): string {
  const eventTime = new Date(value);

  if (Number.isNaN(eventTime.getTime())) {
    return "Unknown";
  }

  const diffMs = Math.max(Date.now() - eventTime.getTime(), 0);
  const diffMinutes = Math.floor(diffMs / 60000);

  if (diffMinutes < 1) {
    return "now";
  }

  if (diffMinutes < 60) {
    return `${diffMinutes}m`;
  }

  const diffHours = Math.floor(diffMinutes / 60);

  if (diffHours < 24) {
    return `${diffHours}h`;
  }

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d`;
}

function incidentVisualSeverity(
  severity: OperationalEvent["severity"],
): "critical" | "high" | "medium" {
  if (severity === "critical") {
    return "critical";
  }

  if (severity === "high") {
    return "high";
  }

  return "medium";
}



function ConnectivityPage({
  connectivity,
  metrics,
  error,
  metricsError,
  trafficDecision,
  actionLoading,
  actionError,
  retryResult,
  simulation,
  onRefresh,
  onSubmitTraffic,
  onUpdateLink,
  onRetryQueue,
  onSimulate,
}: {
  connectivity: ConnectivityStatusResponse | null;
  metrics: ConnectivityMetricsResponse | null;
  error: string | null;
  metricsError: string | null;
  trafficDecision: ConnectivityTrafficDecision | null;
  actionLoading: string | null;
  actionError: string | null;
  retryResult: ConnectivityRetryResponse | null;
  simulation: ConnectivitySimulationResponse | null;
  onRefresh: () => void;
  onSubmitTraffic: (payload: {
    traffic_id: string;
    traffic_class: TrafficClass;
    size_kb: number;
    required_kbps: number;
    deadline?: number | null;
  }) => Promise<void>;
  onUpdateLink: (state: ConnectivityState, available_kbps: number) => Promise<void>;
  onRetryQueue: () => Promise<void>;
  onSimulate: () => Promise<void>;
}) {
  const [trafficClass, setTrafficClass] = useState<TrafficClass>("normal");
  const [sizeKb, setSizeKb] = useState("256");
  const [requiredKbps, setRequiredKbps] = useState("128");
  const [trafficId, setTrafficId] = useState(() => `WEB-${Date.now()}`);

  const capacity = connectivity?.link.capacity_kbps ?? 0;
  const available = connectivity?.link.available_kbps ?? 0;
  const used = Math.max(capacity - available, 0);
  const utilization = capacity > 0 ? Math.round((used / capacity) * 100) : 0;
  const state = connectivity?.link.state ?? "unavailable";

  const stateTone =
    state === "available" ? "healthy" : state === "degraded" ? "warning" : "critical";

  const trafficClasses: TrafficClass[] = [
    "critical",
    "high",
    "normal",
    "low",
    "bulk",
  ];

  const submit = async () => {
    await onSubmitTraffic({
      traffic_id: trafficId.trim() || `WEB-${Date.now()}`,
      traffic_class: trafficClass,
      size_kb: Number(sizeKb),
      required_kbps: Number(requiredKbps),
      deadline: null,
    });
    setTrafficId(`WEB-${Date.now()}`);
  };

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">ADAPTIVE CONNECTIVITY</div>
          <h1>Connectivity operations</h1>
          <p>
            Exercise the deterministic bandwidth policy, scheduler, local queue,
            accounting, and resilience simulation behind the vessel edge link.
          </p>
        </div>
        <div className="page-heading__status">
          <StatusDot
            tone={error ? "critical" : stateTone}
            label={error ? "Connectivity unavailable" : state.replace("_", " ")}
          />
          <button
            className="panel-link"
            type="button"
            onClick={onRefresh}
            disabled={actionLoading === "refresh"}
            style={{ background: "none", border: 0, cursor: "pointer" }}
          >
            Refresh
          </button>
        </div>
      </section>

      <section className="metric-grid" aria-label="Connectivity summary">
        <MetricCard
          label="Available bandwidth"
          value={connectivity ? `${available.toLocaleString()} Kbps` : "—"}
          helper={connectivity ? `${capacity.toLocaleString()} Kbps link capacity` : "Loading link"}
          tone={stateTone}
          icon="connectivity"
        />
        <MetricCard
          label="Link utilization"
          value={connectivity ? `${utilization}%` : "—"}
          helper={connectivity ? `${used.toLocaleString()} Kbps currently in use` : "Loading utilization"}
          tone={utilization > 80 ? "warning" : "healthy"}
          icon="pulse"
        />
        <MetricCard
          label="Queued requests"
          value={connectivity ? connectivity.usage.queued_requests.toLocaleString() : "—"}
          helper={connectivity ? `${connectivity.usage.queued_kbps.toLocaleString()} Kbps queued` : "Loading queue"}
          tone={connectivity?.usage.queued_requests ? "warning" : "neutral"}
          icon="activity"
        />
        <MetricCard
          label="Traffic decisions"
          value={metrics ? metrics.traffic.total_requests.toLocaleString() : "—"}
          helper={metrics ? `${metrics.traffic.transmitted_requests} transmit · ${metrics.traffic.throttled_requests} throttle` : "Loading metrics"}
          tone="neutral"
          icon="network"
        />
      </section>

      {actionError ? (
        <article className="panel" style={{ marginTop: 18 }}>
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">CONTROL RESULT</div>
              <h2>Operation failed</h2>
            </div>
          </div>
          <p style={{ margin: 0, color: "#ff8899" }}>{actionError}</p>
        </article>
      ) : null}

      <section className="primary-grid" style={{ alignItems: "stretch" }}>
        <article className="panel panel--wide">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">LINK CONTROL</div>
              <h2>Simulated external link</h2>
            </div>
            <StatusDot tone={stateTone} label={connectivity?.link.name ?? "satellite-link"} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr", gap: 18 }}>
            <div
              style={{
                padding: 20,
                border: "1px solid rgba(148,163,184,.12)",
                borderRadius: 14,
                background: "rgba(6,16,26,.55)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                <span style={{ color: "#91a0af", fontSize: 12 }}>Capacity envelope</span>
                <strong style={{ color: "#dce8f2" }}>{capacity.toLocaleString()} Kbps</strong>
              </div>
              <div style={{ height: 10, borderRadius: 999, background: "rgba(148,163,184,.1)", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.min(100, utilization)}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, rgba(57,194,255,.55), rgba(57,194,255,.95))",
                  }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12, color: "#91a0af" }}>
                <span>{available.toLocaleString()} Kbps available</span>
                <span>{utilization}% utilized</span>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {(["available", "degraded", "unavailable"] as ConnectivityState[]).map((nextState) => (
                <button
                  key={nextState}
                  type="button"
                  onClick={() => void onUpdateLink(nextState, nextState === "available" ? 750 : nextState === "degraded" ? 240 : 0)}
                  disabled={actionLoading === "link"}
                  style={{
                    textAlign: "left",
                    borderRadius: 12,
                    padding: "12px 14px",
                    border: `1px solid ${nextState === state ? "rgba(64,195,255,.48)" : "rgba(148,163,184,.12)"}`,
                    background: nextState === state ? "rgba(39,148,206,.12)" : "rgba(6,16,26,.45)",
                    color: "#d9e5ef",
                    cursor: "pointer",
                  }}
                >
                  <strong style={{ display: "block", textTransform: "capitalize" }}>{nextState}</strong>
                  <span style={{ fontSize: 12, color: "#8c9bab" }}>
                    {nextState === "available" ? "Full policy throughput" : nextState === "degraded" ? "Priority throttling and bulk deferral" : "Local queue until recovery"}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">POLICY ENGINE</div>
              <h2>Priority ladder</h2>
            </div>
            <span className="panel-link">Deterministic</span>
          </div>

          <div style={{ display: "grid", gap: 9 }}>
            {trafficClasses.map((trafficClass, index) => (
              <div
                key={trafficClass}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "10px 12px",
                  borderRadius: 10,
                  background: index === 0 ? "rgba(255,89,110,.09)" : "rgba(255,255,255,.025)",
                  border: "1px solid rgba(148,163,184,.08)",
                }}
              >
                <span style={{ width: 24, fontSize: 11, color: "#7f91a3" }}>0{index + 1}</span>
                <strong style={{ textTransform: "uppercase", letterSpacing: ".08em", fontSize: 12 }}>{trafficClass}</strong>
                <span style={{ marginLeft: "auto", fontSize: 11, color: "#8494a4" }}>
                  {index === 0 ? "protected" : index === 4 ? "deferred under degradation" : "priority"}
                </span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="primary-grid" style={{ alignItems: "stretch", marginTop: 18 }}>
        <article className="panel panel--wide">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">TRAFFIC TEST</div>
              <h2>Submit a policy decision</h2>
            </div>
            <span className="panel-link">Policy → scheduler → accounting</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.2fr .8fr", gap: 18 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 12 }}>
              {[
                ["Traffic ID", trafficId, setTrafficId, "text"],
                ["Payload (KB)", sizeKb, setSizeKb, "number"],
                ["Required Kbps", requiredKbps, setRequiredKbps, "number"],
              ].map(([label, value, setter, type]) => (
                <label key={label as string} style={{ display: "grid", gap: 7 }}>
                  <span style={{ fontSize: 11, color: "#8fa0b0", textTransform: "uppercase", letterSpacing: ".08em" }}>{label as string}</span>
                  <input
                    type={type as string}
                    value={value as string}
                    onChange={(event) => (setter as (value: string) => void)(event.target.value)}
                    style={{
                      width: "100%",
                      boxSizing: "border-box",
                      borderRadius: 10,
                      border: "1px solid rgba(148,163,184,.14)",
                      background: "rgba(2,9,16,.6)",
                      color: "#dbe7f0",
                      padding: "11px 12px",
                      outline: "none",
                    }}
                  />
                </label>
              ))}
              <label style={{ display: "grid", gap: 7 }}>
                <span style={{ fontSize: 11, color: "#8fa0b0", textTransform: "uppercase", letterSpacing: ".08em" }}>Traffic class</span>
                <select
                  value={trafficClass}
                  onChange={(event) => setTrafficClass(event.target.value as TrafficClass)}
                  style={{
                    borderRadius: 10,
                    border: "1px solid rgba(148,163,184,.14)",
                    background: "rgba(2,9,16,.6)",
                    color: "#dbe7f0",
                    padding: "11px 12px",
                  }}
                >
                  {trafficClasses.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
            </div>

            <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", gap: 12 }}>
              <div style={{ padding: 14, borderRadius: 12, background: "rgba(255,255,255,.025)", border: "1px solid rgba(148,163,184,.08)" }}>
                <span style={{ display: "block", fontSize: 11, color: "#8395a5", textTransform: "uppercase", letterSpacing: ".08em" }}>Decision</span>
                <strong style={{ display: "block", marginTop: 8, fontSize: 20, textTransform: "uppercase" }}>
                  {trafficDecision?.action ?? "—"}
                </strong>
                <span style={{ display: "block", marginTop: 6, fontSize: 12, color: "#98a8b7", lineHeight: 1.5 }}>
                  {trafficDecision?.reason ?? "Submit traffic to evaluate it against the current link state."}
                </span>
                <div style={{ marginTop: 10, fontSize: 12, color: "#c9d5df" }}>
                  Allocated: {trafficDecision ? `${trafficDecision.allocated_kbps.toLocaleString()} Kbps` : "—"}
                </div>
              </div>
              <button
                type="button"
                onClick={() => void submit()}
                disabled={actionLoading === "traffic"}
                style={{
                  border: 0,
                  borderRadius: 11,
                  padding: "12px 15px",
                  background: "linear-gradient(135deg, rgba(36,147,207,.95), rgba(59,195,255,.9))",
                  color: "#041018",
                  fontWeight: 800,
                  cursor: "pointer",
                }}
              >
                {actionLoading === "traffic" ? "Evaluating…" : "Evaluate traffic"}
              </button>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">LOCAL QUEUE</div>
              <h2>Queued traffic</h2>
            </div>
            <button
              className="panel-link"
              type="button"
              onClick={() => void onRetryQueue()}
              disabled={actionLoading === "retry" || !connectivity?.queued_traffic.length}
              style={{ background: "none", border: 0, cursor: "pointer" }}
            >
              Retry queue
            </button>
          </div>

          {connectivity?.queued_traffic.length ? (
            <div style={{ display: "grid", gap: 9 }}>
              {connectivity.queued_traffic.map((request) => (
                <div key={request.traffic_id} style={{ padding: 11, borderRadius: 10, border: "1px solid rgba(148,163,184,.08)", background: "rgba(255,255,255,.025)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <strong>{request.traffic_id}</strong>
                    <span style={{ fontSize: 11, textTransform: "uppercase", color: "#9eb0bf" }}>{request.traffic_class}</span>
                  </div>
                  <div style={{ marginTop: 5, fontSize: 12, color: "#8799a9" }}>
                    {request.size_kb.toLocaleString()} KB · needs {request.required_kbps.toLocaleString()} Kbps
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: "28px 10px", textAlign: "center", color: "#8293a4" }}>
              Queue empty — no traffic is waiting for connectivity.
            </div>
          )}

          {retryResult ? (
            <div style={{ marginTop: 12, fontSize: 12, color: "#91a6b5" }}>
              Retry processed {retryResult.decisions.length} decision{retryResult.decisions.length === 1 ? "" : "s"}; {retryResult.queued_traffic_count} remain queued.
            </div>
          ) : null}
        </article>
      </section>

      <section className="secondary-grid" style={{ marginTop: 18 }}>
        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">ACCOUNTING</div>
              <h2>Bandwidth ledger</h2>
            </div>
            <span className="panel-link">Live counters</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
            {[
              ["Transmitted", metrics?.bandwidth_kbps.transmitted ?? 0, "Kbps"],
              ["Throttled", metrics?.bandwidth_kbps.throttled ?? 0, "Kbps"],
              ["Queued", metrics?.bandwidth_kbps.queued ?? 0, "Kbps"],
            ].map(([label, value, unit]) => (
              <div key={label as string} style={{ padding: 14, borderRadius: 12, background: "rgba(255,255,255,.025)", border: "1px solid rgba(148,163,184,.08)" }}>
                <span style={{ fontSize: 11, color: "#8597a7" }}>{label as string}</span>
                <strong style={{ display: "block", marginTop: 6, fontSize: 21 }}>{Number(value).toLocaleString()} <small style={{ fontSize: 11, color: "#8294a5" }}>{unit as string}</small></strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">RESILIENCE LAB</div>
              <h2>Degrade → outage → recovery</h2>
            </div>
            <button
              className="panel-link"
              type="button"
              onClick={() => void onSimulate()}
              disabled={actionLoading === "simulate"}
              style={{ background: "none", border: 0, cursor: "pointer" }}
            >
              {actionLoading === "simulate" ? "Running…" : "Run simulation"}
            </button>
          </div>
          {simulation ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 8 }}>
              {[
                ["Initial", simulation.initial_state],
                ["Degraded", simulation.degraded_state],
                ["Outage", simulation.outage_state],
                ["Recovered", simulation.recovered_state],
              ].map(([label, value]) => (
                <div key={label} style={{ padding: 10, borderRadius: 9, background: "rgba(255,255,255,.025)", border: "1px solid rgba(148,163,184,.08)" }}>
                  <span style={{ display: "block", fontSize: 10, color: "#8294a4", textTransform: "uppercase" }}>{label}</span>
                  <strong style={{ display: "block", marginTop: 5, fontSize: 12, textTransform: "capitalize" }}>{value}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0, color: "#8496a6", lineHeight: 1.6 }}>
              Execute the isolated resilience scenario to verify that critical traffic is protected, bulk traffic is deferred, outage traffic is queued, and recovery releases work.
            </p>
          )}
          {simulation ? (
            <div style={{ marginTop: 12, fontSize: 12, color: "#94a5b4", lineHeight: 1.6 }}>
              Critical: {simulation.critical_action_during_degradation} · Bulk: {simulation.bulk_action_during_degradation} · Outage queued: {simulation.outage_queued_requests} · Final queued: {simulation.final_queued_requests} · Recovered transmitted: {simulation.recovered_transmitted_requests}
            </div>
          ) : null}
        </article>
      </section>

      {metricsError ? (
        <p style={{ marginTop: 14, color: "#ff9aaa", fontSize: 12 }}>Metrics: {metricsError}</p>
      ) : null}
    </>
  );
}

function TopologyPage({
  graph,
  selectedAsset,
  impact,
  loading,
  impactLoading,
  error,
  impactError,
  onSelectAsset,
  onRefresh,
}: {
  graph: TopologyGraphResponse | null;
  selectedAsset: string | null;
  impact: TopologyImpactResponse | null;
  loading: boolean;
  impactLoading: boolean;
  error: string | null;
  impactError: string | null;
  onSelectAsset: (identifier: string) => void;
  onRefresh: () => void;
}) {
  const groupedAssets = new Map<
    string,
    { identifier: string; interfaces: TopologyGraphResponse["nodes"] }
  >();

  graph?.nodes.forEach((node) => {
    const existing = groupedAssets.get(node.asset_id);
    if (existing) {
      existing.interfaces.push(node);
    } else {
      groupedAssets.set(node.asset_id, {
        identifier: node.identifier,
        interfaces: [node],
      });
    }
  });

  const assets = Array.from(groupedAssets.values());
  const width = 900;
  const height = 430;
  const centerX = width / 2;
  const centerY = height / 2 + 4;
  const ringX = 310;
  const ringY = 150;

  const positions = new Map<string, { x: number; y: number }>();
  assets.forEach((asset, index) => {
    if (index === 0) {
      positions.set(asset.identifier, { x: centerX, y: centerY });
      return;
    }
    const remaining = assets.length - 1;
    const angle = ((index - 1) / Math.max(remaining, 1)) * Math.PI * 2 - Math.PI / 2;
    positions.set(asset.identifier, {
      x: centerX + Math.cos(angle) * ringX,
      y: centerY + Math.sin(angle) * ringY,
    });
  });

  const selectedSet = new Set(impact?.affected_assets ?? []);
  const rootIdentifier = selectedAsset ?? assets[0]?.identifier ?? null;

  const resolveNodeAsset = (nodeId: string) => {
    const node = graph?.nodes.find((candidate) => candidate.id === nodeId);
    return node?.identifier ?? null;
  };

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">NETWORK INTELLIGENCE</div>
          <h1>Network topology</h1>
          <p>
            Physical connectivity and asset impact analysis from the vessel edge topology.
          </p>
        </div>

        <div className="page-heading__status">
          <StatusDot
            tone={error ? "critical" : loading ? "neutral" : "healthy"}
            label={error ? "Topology unavailable" : loading ? "Loading topology" : "Topology live"}
          />
          <button
            className="panel-link"
            type="button"
            onClick={onRefresh}
            disabled={loading}
            style={{ background: "none", border: 0, cursor: loading ? "default" : "pointer" }}
          >
            Refresh
          </button>
        </div>
      </section>

      <section className="metric-grid" aria-label="Topology summary">
        <MetricCard
          label="Assets"
          value={graph ? assets.length.toLocaleString() : "—"}
          helper="Database-backed infrastructure assets"
          tone="neutral"
          icon="network"
        />
        <MetricCard
          label="Interfaces"
          value={graph ? graph.nodes.length.toLocaleString() : "—"}
          helper="Network interfaces in topology"
          tone="neutral"
          icon="activity"
        />
        <MetricCard
          label="Operational links"
          value={graph ? graph.edges.length.toLocaleString() : "—"}
          helper="Active physical links"
          tone="healthy"
          icon="connectivity"
        />
        <MetricCard
          label="Selected impact"
          value={impact ? impact.affected_count.toLocaleString() : "—"}
          helper={rootIdentifier ? `Potentially affected from ${rootIdentifier}` : "Select an asset"}
          tone={impact && impact.affected_count > 0 ? "warning" : "neutral"}
          icon="warning"
        />
      </section>

      {error ? (
        <article className="panel" style={{ marginTop: 18 }}>
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">TOPOLOGY API</div>
              <h2>Unable to load network graph</h2>
            </div>
          </div>
          <p style={{ margin: 0, color: "var(--text-muted, #8c98a6)" }}>{error}</p>
        </article>
      ) : null}

      <section className="primary-grid" style={{ alignItems: "stretch" }}>
        <article className="panel panel--wide">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">PHYSICAL TOPOLOGY</div>
              <h2>Vessel network graph</h2>
            </div>
            <span className="panel-link">
              {graph ? `${graph.edges.length} active links` : "—"}
            </span>
          </div>

          <div
            style={{
              position: "relative",
              minHeight: 430,
              border: "1px solid rgba(148, 163, 184, 0.12)",
              borderRadius: 14,
              overflow: "hidden",
              background:
                "radial-gradient(circle at 50% 50%, rgba(61, 177, 255, 0.06), transparent 42%), rgba(5, 14, 23, 0.72)",
            }}
          >
            {loading ? (
              <div
                style={{
                  display: "grid",
                  placeItems: "center",
                  minHeight: 430,
                  color: "var(--text-muted, #8c98a6)",
                }}
              >
                Loading network topology…
              </div>
            ) : graph && graph.nodes.length === 0 ? (
              <div
                style={{
                  display: "grid",
                  placeItems: "center",
                  minHeight: 430,
                  color: "var(--text-muted, #8c98a6)",
                }}
              >
                No topology interfaces are currently registered.
              </div>
            ) : (
              <svg
                viewBox={`0 0 ${width} ${height}`}
                style={{ width: "100%", height: "100%", minHeight: 430, display: "block" }}
                role="img"
                aria-label="ShipOps network topology graph"
              >
                <defs>
                  <filter id="nodeGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {graph?.edges.map((edge, index) => {
                  const source = resolveNodeAsset(edge.source_node_id);
                  const target = resolveNodeAsset(edge.destination_node_id);
                  const sourcePosition = source ? positions.get(source) : undefined;
                  const targetPosition = target ? positions.get(target) : undefined;
                  if (!sourcePosition || !targetPosition) return null;
                  const active =
                    source === rootIdentifier ||
                    target === rootIdentifier ||
                    selectedSet.has(source ?? "") ||
                    selectedSet.has(target ?? "");
                  return (
                    <line
                      key={`${edge.source_node_id}-${edge.destination_node_id}-${index}`}
                      x1={sourcePosition.x}
                      y1={sourcePosition.y}
                      x2={targetPosition.x}
                      y2={targetPosition.y}
                      stroke={
                        active
                          ? "rgba(77, 205, 255, 0.75)"
                          : "rgba(120, 145, 165, 0.22)"
                      }
                      strokeWidth={active ? 2.6 : 1.4}
                    />
                  );
                })}

                {assets.map((asset) => {
                  const position = positions.get(asset.identifier);
                  if (!position) return null;
                  const isRoot = asset.identifier === rootIdentifier;
                  const isAffected = selectedSet.has(asset.identifier);
                  const isSelected = asset.identifier === selectedAsset;
                  const radius = isRoot ? 34 : 28;
                  return (
                    <g
                      key={asset.identifier}
                      transform={`translate(${position.x} ${position.y})`}
                      onClick={() => onSelectAsset(asset.identifier)}
                      style={{ cursor: "pointer" }}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectAsset(asset.identifier);
                        }
                      }}
                      aria-label={`Analyze ${asset.identifier}`}
                    >
                      <circle
                        r={radius + (isSelected ? 7 : 2)}
                        fill={
                          isRoot
                            ? "rgba(65, 203, 255, 0.14)"
                            : "rgba(10, 28, 42, 0.94)"
                        }
                        stroke={
                          isAffected
                            ? "rgba(255, 179, 71, 0.9)"
                            : isSelected
                              ? "rgba(65, 203, 255, 0.95)"
                              : "rgba(108, 139, 160, 0.42)"
                        }
                        strokeWidth={isAffected || isSelected ? 2.4 : 1.2}
                        filter={isSelected ? "url(#nodeGlow)" : undefined}
                      />
                      <circle
                        r={6}
                        cy={-radius + 8}
                        fill={isAffected ? "#ffb347" : "#4ce0a1"}
                        stroke="#0a1823"
                        strokeWidth={2}
                      />
                      <text
                        y={4}
                        textAnchor="middle"
                        fill="#e7f0f7"
                        fontSize="15"
                        fontWeight="700"
                      >
                        {asset.identifier}
                      </text>
                      <text
                        y={22}
                        textAnchor="middle"
                        fill="#7f92a3"
                        fontSize="10"
                      >
                        {asset.interfaces.length} interface
                        {asset.interfaces.length === 1 ? "" : "s"}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">ASSET IMPACT</div>
              <h2>{rootIdentifier ? `${rootIdentifier} analysis` : "Select an asset"}</h2>
            </div>
            {impactLoading ? <span className="panel-link">Analyzing…</span> : null}
          </div>

          {impactError ? (
            <p style={{ margin: 0, color: "#ff8585" }}>{impactError}</p>
          ) : impact ? (
            <div>
              <div className="rca-card" style={{ marginBottom: 16 }}>
                <div className="rca-card__icon">
                  <Icon name="activity" size={19} />
                </div>
                <div className="rca-card__content">
                  <span className="rca-card__label">Physical reachability</span>
                  <strong>{impact.affected_count} affected assets</strong>
                  <p>
                    Assets connected through currently operational physical links from {impact.root_asset}.
                  </p>
                </div>
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                {impact.affected_assets.length === 0 ? (
                  <div
                    style={{
                      padding: "14px 0",
                      color: "var(--text-muted, #8c98a6)",
                    }}
                  >
                    No downstream or adjacent assets are reachable from this asset.
                  </div>
                ) : (
                  impact.affected_assets.map((identifier) => (
                    <button
                      key={identifier}
                      type="button"
                      onClick={() => onSelectAsset(identifier)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        width: "100%",
                        padding: "11px 12px",
                        border: "1px solid rgba(148, 163, 184, 0.12)",
                        borderRadius: 10,
                        background: "rgba(15, 30, 43, 0.6)",
                        color: "#dce8f0",
                        cursor: "pointer",
                        textAlign: "left",
                      }}
                    >
                      <span>{identifier}</span>
                      <Icon name="chevron" size={14} />
                    </button>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gap: 10,
                color: "var(--text-muted, #8c98a6)",
              }}
            >
              <p style={{ margin: 0 }}>
                Select an asset in the graph or choose one below to calculate its physical impact.
              </p>
              <div
                style={{
                  display: "grid",
                  gap: 8,
                  maxHeight: 250,
                  overflow: "auto",
                }}
              >
                {assets.map((asset) => (
                  <button
                    key={asset.identifier}
                    type="button"
                    onClick={() => onSelectAsset(asset.identifier)}
                    style={{
                      padding: "10px 12px",
                      border: "1px solid rgba(148, 163, 184, 0.12)",
                      borderRadius: 10,
                      background: "rgba(15, 30, 43, 0.6)",
                      color: "#dce8f0",
                      textAlign: "left",
                      cursor: "pointer",
                    }}
                  >
                    {asset.identifier}
                  </button>
                ))}
              </div>
            </div>
          )}
        </article>
      </section>

      <section className="secondary-grid">
        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">INTERFACES</div>
              <h2>Asset inventory</h2>
            </div>
            <span className="panel-link">{assets.length} assets</span>
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            {assets.map((asset) => (
              <button
                key={asset.identifier}
                type="button"
                onClick={() => onSelectAsset(asset.identifier)}
                style={{
                  display: "grid",
                  gap: 4,
                  padding: "12px 0",
                  border: 0,
                  borderBottom: "1px solid rgba(148, 163, 184, 0.08)",
                  background: "none",
                  textAlign: "left",
                  color: "inherit",
                  cursor: "pointer",
                }}
              >
                <strong style={{ color: "#e7f0f7" }}>{asset.identifier}</strong>
                <span
                  style={{
                    color: "var(--text-muted, #8c98a6)",
                    fontSize: 12,
                  }}
                >
                  {asset.interfaces.map((item) => item.name).join(" · ")}
                </span>
              </button>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">LEGEND</div>
              <h2>Topology interpretation</h2>
            </div>
          </div>
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "#4ce0a1",
                  boxShadow: "0 0 12px rgba(76, 224, 161, 0.45)",
                }}
              />
              <span style={{ color: "#b7c5d1" }}>Operational asset</span>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "#ffb347",
                  boxShadow: "0 0 12px rgba(255, 179, 71, 0.4)",
                }}
              />
              <span style={{ color: "#b7c5d1" }}>Affected by selected asset</span>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span
                style={{
                  width: 30,
                  height: 2,
                  background: "rgba(120, 145, 165, 0.38)",
                }}
              />
              <span style={{ color: "#b7c5d1" }}>Operational physical link</span>
            </div>
            <p
              style={{
                margin: 0,
                color: "var(--text-muted, #8c98a6)",
                fontSize: 12,
                lineHeight: 1.6,
              }}
            >
              Impact analysis follows the same bidirectional physical-link traversal used by the ShipOps topology service.
            </p>
          </div>
        </article>
      </section>
    </>
  );
}


function IncidentPage({
  events,
  selectedEvent,
  rca,
  loading,
  detailLoading,
  actionLoading,
  error,
  actionError,
  onRefresh,
  onSelect,
  onAcknowledge,
  onResolve,
  onRunRca,
  topology,
}: {
  events: OperationalEvent[] | null;
  selectedEvent: OperationalEvent | null;
  topology: TopologyGraphResponse | null;
  rca: RCAEventResponse | null;
  loading: boolean;
  detailLoading: boolean;
  actionLoading: string | null;
  error: string | null;
  actionError: string | null;
  onRefresh: () => void;
  onSelect: (eventId: string) => void;
  onAcknowledge: (eventId: string) => Promise<void>;
  onResolve: (eventId: string) => Promise<void>;
  onRunRca: (eventId: string) => Promise<void>;
}) {
  const [statusFilter, setStatusFilter] = useState<"all" | EventStatus>("all");
  const [severityFilter, setSeverityFilter] = useState<"all" | EventSeverity>("all");

  const filteredEvents = (events ?? []).filter((event) => {
    const statusMatch = statusFilter === "all" || event.status === statusFilter;
    const severityMatch = severityFilter === "all" || event.severity === severityFilter;
    return statusMatch && severityMatch;
  });

  const criticalCount = (events ?? []).filter((event) => event.severity === "critical").length;
  const openCount = (events ?? []).filter((event) => event.status === "open").length;
  const acknowledgedCount = (events ?? []).filter((event) => event.status === "acknowledged").length;
  const resolvedCount = (events ?? []).filter((event) => event.status === "resolved").length;

  const statusTone = (status: EventStatus): "healthy" | "warning" | "critical" | "neutral" => {
    if (status === "resolved") return "healthy";
    if (status === "acknowledged") return "warning";
    return "critical";
  };

  const severityLabel = (severity: EventSeverity) => severity.toUpperCase();

  const assetIdentifierById = new Map(
    (topology?.nodes ?? []).map((node) => [node.asset_id, node.identifier]),
  );

  const getEventAssetIdentifier = (event: OperationalEvent) =>
    assetIdentifierById.get(event.asset_id) ?? event.asset_id;

  const renderEvidence = (item: Record<string, unknown>, index: number) => (
    <div
      key={`${index}-${Object.keys(item).join("-")}`}
      style={{
        padding: "12px 14px",
        border: "1px solid rgba(148,163,184,.1)",
        borderRadius: 10,
        background: "rgba(6,16,26,.48)",
      }}
    >
      <div style={{ color: "#8ea1b2", fontSize: 11, marginBottom: 7 }}>
        Evidence {String(index + 1).padStart(2, "0")}
      </div>
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          color: "#d9e6f0",
          fontSize: 11,
          lineHeight: 1.55,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
        }}
      >
        {JSON.stringify(item, null, 2)}
      </pre>
    </div>
  );

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">INCIDENT OPERATIONS</div>
          <h1>Operational incidents</h1>
          <p>
            Investigate rule-driven events, inspect telemetry evidence, manage incident
            state, and launch deterministic root-cause analysis.
          </p>
        </div>
        <div className="page-heading__status">
          <StatusDot
            tone={error ? "critical" : criticalCount > 0 ? "critical" : "healthy"}
            label={error ? "Incident API error" : `${events?.length ?? 0} events loaded`}
          />
          <button
            className="panel-link"
            type="button"
            onClick={onRefresh}
            disabled={loading}
            style={{ background: "none", border: 0, cursor: "pointer" }}
          >
            Refresh
          </button>
        </div>
      </section>

      <section className="metric-grid" aria-label="Incident summary">
        <MetricCard
          label="Open incidents"
          value={openCount.toLocaleString()}
          helper="Awaiting operator action"
          tone={openCount > 0 ? "critical" : "healthy"}
          icon="warning"
        />
        <MetricCard
          label="Acknowledged"
          value={acknowledgedCount.toLocaleString()}
          helper="Taken into operator ownership"
          tone={acknowledgedCount > 0 ? "warning" : "neutral"}
          icon="shield"
        />
        <MetricCard
          label="Critical events"
          value={criticalCount.toLocaleString()}
          helper="Highest operational severity"
          tone={criticalCount > 0 ? "critical" : "neutral"}
          icon="pulse"
        />
        <MetricCard
          label="Resolved"
          value={resolvedCount.toLocaleString()}
          helper="Closed operational records"
          tone="healthy"
          icon="activity"
        />
      </section>

      {actionError ? (
        <article className="panel" style={{ marginTop: 18 }}>
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">CONTROL RESULT</div>
              <h2>Incident operation failed</h2>
            </div>
          </div>
          <p style={{ margin: 0, color: "#ff8899" }}>{actionError}</p>
        </article>
      ) : null}

      <section style={{ display: "grid", gridTemplateColumns: "1.15fr .85fr", gap: 18, marginTop: 18 }}>
        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">EVENT QUEUE</div>
              <h2>Operational events</h2>
            </div>
            <span className="panel-link">{filteredEvents.length} shown</span>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            {(["all", "open", "acknowledged", "resolved"] as const).map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => setStatusFilter(filter)}
                style={{
                  border: `1px solid ${statusFilter === filter ? "rgba(57,194,255,.5)" : "rgba(148,163,184,.12)"}`,
                  background: statusFilter === filter ? "rgba(39,148,206,.12)" : "rgba(255,255,255,.025)",
                  color: "#d9e5ef",
                  borderRadius: 999,
                  padding: "7px 11px",
                  textTransform: "capitalize",
                  fontSize: 11,
                  cursor: "pointer",
                }}
              >
                {filter}
              </button>
            ))}
            <select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value as "all" | EventSeverity)}
              style={{
                marginLeft: "auto",
                border: "1px solid rgba(148,163,184,.12)",
                background: "rgba(255,255,255,.025)",
                color: "#d9e5ef",
                borderRadius: 999,
                padding: "7px 11px",
                fontSize: 11,
              }}
            >
              <option value="all">All severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>

          {loading ? (
            <div style={{ padding: 28, color: "#8fa2b2" }}>Loading operational events…</div>
          ) : filteredEvents.length === 0 ? (
            <div
              style={{
                padding: 34,
                borderRadius: 12,
                border: "1px dashed rgba(148,163,184,.16)",
                color: "#8fa2b2",
                textAlign: "center",
              }}
            >
              No events match the current filters.
            </div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {filteredEvents
                .slice()
                .sort((left, right) => new Date(right.occurred_at).getTime() - new Date(left.occurred_at).getTime())
                .map((event) => {
                  const selected = selectedEvent?.id === event.id;
                  return (
                    <button
                      key={event.id}
                      type="button"
                      onClick={() => onSelect(event.id)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        border: `1px solid ${selected ? "rgba(57,194,255,.45)" : "rgba(148,163,184,.1)"}`,
                        background: selected ? "rgba(39,148,206,.1)" : "rgba(255,255,255,.02)",
                        color: "inherit",
                        borderRadius: 12,
                        padding: "13px 14px",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span className={`incident-severity incident-severity--${incidentVisualSeverity(event.severity)}`}>
                          <Icon name="warning" size={14} />
                        </span>
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <strong style={{ color: "#e4edf5", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {event.summary}
                          </strong>
                          <span style={{ display: "block", color: "#8193a3", fontSize: 11, marginTop: 4 }}>
                            {getEventAssetIdentifier(event)} · {event.event_type} · {formatEventTime(event.occurred_at)}
                          </span>
                        </div>
                        <StatusDot tone={statusTone(event.status)} label={event.status} />
                      </div>
                    </button>
                  );
                })}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">EVENT DETAIL</div>
              <h2>{selectedEvent ? "Selected incident" : "Select an event"}</h2>
            </div>
            {selectedEvent ? <StatusDot tone={statusTone(selectedEvent.status)} label={selectedEvent.status} /> : null}
          </div>

          {!selectedEvent ? (
            <div style={{ padding: 32, color: "#8fa2b2" }}>
              Select an operational event to inspect its lifecycle, evidence, and available actions.
            </div>
          ) : (
            <div style={{ display: "grid", gap: 14 }}>
              {detailLoading ? (
                <div style={{ color: "#8fa2b2" }}>Loading authoritative event record…</div>
              ) : null}
              <div>
                <div style={{ fontSize: 11, color: "#7890a2", marginBottom: 6 }}>SUMMARY</div>
                <strong style={{ fontSize: 18, color: "#e7f0f7" }}>{selectedEvent.summary.replace(selectedEvent.asset_id, getEventAssetIdentifier(selectedEvent))}</strong>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  ["Asset", getEventAssetIdentifier(selectedEvent)],
                  ["Rule", selectedEvent.rule_id],
                  ["Event type", selectedEvent.event_type],
                  ["Occurred", new Date(selectedEvent.occurred_at).toLocaleString()],
                  ["Severity", severityLabel(selectedEvent.severity)],
                  ["Resolved", selectedEvent.resolved_at ? new Date(selectedEvent.resolved_at).toLocaleString() : "—"],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    style={{
                      padding: 11,
                      borderRadius: 10,
                      border: "1px solid rgba(148,163,184,.08)",
                      background: "rgba(255,255,255,.02)",
                    }}
                  >
                    <span style={{ display: "block", color: "#788d9e", fontSize: 10, marginBottom: 4 }}>{label}</span>
                    <strong style={{ color: "#dce7ef", fontSize: 12, wordBreak: "break-word" }}>{value}</strong>
                  </div>
                ))}
              </div>

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {selectedEvent.status === "open" ? (
                  <button
                    type="button"
                    className="panel-link"
                    onClick={() => void onAcknowledge(selectedEvent.id)}
                    disabled={actionLoading === "acknowledge"}
                    style={{ background: "rgba(250,180,60,.1)", border: "1px solid rgba(250,180,60,.25)", padding: "9px 12px", borderRadius: 9, cursor: "pointer" }}
                  >
                    Acknowledge
                  </button>
                ) : null}
                {selectedEvent.status !== "resolved" ? (
                  <button
                    type="button"
                    className="panel-link"
                    onClick={() => void onResolve(selectedEvent.id)}
                    disabled={actionLoading === "resolve"}
                    style={{ background: "rgba(64,205,154,.1)", border: "1px solid rgba(64,205,154,.25)", padding: "9px 12px", borderRadius: 9, cursor: "pointer" }}
                  >
                    Resolve
                  </button>
                ) : null}
                <button
                  type="button"
                  className="panel-link"
                  onClick={() => void onRunRca(selectedEvent.id)}
                  disabled={actionLoading === "rca"}
                  style={{ marginLeft: "auto", background: "rgba(57,194,255,.1)", border: "1px solid rgba(57,194,255,.24)", padding: "9px 12px", borderRadius: 9, cursor: "pointer" }}
                >
                  {actionLoading === "rca" ? "Analyzing…" : "Run deterministic RCA"}
                </button>
              </div>

              <div>
                <div style={{ fontSize: 11, color: "#7890a2", marginBottom: 8 }}>EVENT DETAILS</div>
                <pre
                  style={{
                    margin: 0,
                    padding: 13,
                    borderRadius: 10,
                    border: "1px solid rgba(148,163,184,.1)",
                    background: "rgba(6,16,26,.48)",
                    color: "#cddbe5",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    fontSize: 11,
                    lineHeight: 1.55,
                  }}
                >
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </article>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr", gap: 18, marginTop: 18 }}>
        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">EVIDENCE CHAIN</div>
              <h2>Telemetry evidence</h2>
            </div>
            <span className="panel-link">{selectedEvent?.evidence.length ?? 0} records</span>
          </div>
          {selectedEvent?.evidence.length ? (
            <div style={{ display: "grid", gap: 9 }}>
              {selectedEvent.evidence.map(renderEvidence)}
            </div>
          ) : (
            <div style={{ color: "#8fa2b2" }}>
              Select an event with persisted evidence to inspect the signals attached to the operational decision.
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">ROOT CAUSE</div>
              <h2>{rca ? "Deterministic analysis" : "Analysis ready"}</h2>
            </div>
            {rca ? <span className="confidence-badge">{Math.round(rca.confidence * 100)}% confidence</span> : null}
          </div>

          {rca ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div
                style={{
                  padding: 13,
                  borderRadius: 11,
                  background: "rgba(57,194,255,.06)",
                  border: "1px solid rgba(57,194,255,.15)",
                }}
              >
                <span style={{ display: "block", color: "#7890a2", fontSize: 10, marginBottom: 5 }}>PROBABLE ROOT CAUSE</span>
                <strong style={{ color: "#e7f0f7", fontSize: 16 }}>{rca.root_cause_identifier ?? "No single root cause identified"}</strong>
                <p style={{ margin: "7px 0 0", color: "#9caebc", fontSize: 12, lineHeight: 1.5 }}>{rca.explanation}</p>
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                {rca.candidates.slice(0, 4).map((candidate) => (
                  <div
                    key={candidate.identifier}
                    style={{
                      padding: "10px 12px",
                      border: "1px solid rgba(148,163,184,.1)",
                      borderRadius: 10,
                      background: "rgba(255,255,255,.02)",
                    }}
                  >
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <strong style={{ color: "#dce8f2", flex: 1 }}>{candidate.identifier}</strong>
                      <span style={{ color: "#72d7b1", fontSize: 11 }}>{Math.round(candidate.score * 100)} score</span>
                    </div>
                    <div style={{ color: "#7f91a3", fontSize: 10, marginTop: 4 }}>
                      {candidate.asset_type} · {candidate.distance} hop{candidate.distance === 1 ? "" : "s"} · {candidate.telemetry_support} telemetry · {candidate.shared_event_support} shared events
                    </div>
                    {candidate.reasons.length ? (
                      <div style={{ color: "#a8b8c4", fontSize: 10, marginTop: 6 }}>
                        {candidate.reasons.join(" · ")}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: "#8fa2b2", lineHeight: 1.6 }}>
              Select an event and run the deterministic RCA engine. ShipOps will use topology distance, telemetry support, shared-event support, and the backend's scoring model to rank candidate root-cause assets.
            </div>
          )}
        </article>
      </section>
    </>
  );
}


function RootCausePage({
  events,
  loading,
  selectedEventIds,
  onToggleEvent,
  onAnalyzeEvent,
  onAnalyzeCluster,
  result,
  clusterResult,
  actionLoading,
  error,
  topology,
}: {
  events: OperationalEvent[] | null;
  loading: boolean;
  selectedEventIds: string[];
  onToggleEvent: (eventId: string) => void;
  onAnalyzeEvent: (eventId: string) => Promise<void>;
  onAnalyzeCluster: () => Promise<void>;
  result: RCAEventResponse | null;
  clusterResult: RCAClusterResponse | null;
  actionLoading: string | null;
  error: string | null;
  topology: TopologyGraphResponse | null;
}) {
  const analysis = clusterResult ?? result;
  const isCluster = Boolean(clusterResult);
  const selectedCount = selectedEventIds.length;

  const assetIdentifierById = new Map(
    (topology?.nodes ?? []).map((node) => [node.asset_id, node.identifier]),
  );

  const getEventAssetIdentifier = (event: OperationalEvent) =>
    assetIdentifierById.get(event.asset_id) ?? event.asset_id;

  const candidateBarWidth = (score: number, candidates: RCAEventCandidate[]) => {
    const maxScore = Math.max(...candidates.map((candidate) => candidate.score), 1);
    return Math.max(8, Math.round((score / maxScore) * 100));
  };

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">ROOT CAUSE INTELLIGENCE</div>
          <h1>Root cause analysis</h1>
          <p>
            Explainable topology-aware diagnosis using asset role, physical proximity,
            network connectivity, corroborating telemetry, and shared event impact.
          </p>
        </div>

        <div className="page-heading__status">
          <StatusDot
            tone={analysis ? "healthy" : error ? "critical" : "neutral"}
            label={
              analysis
                ? isCluster
                  ? "Cluster analysis complete"
                  : "Analysis complete"
                : error
                  ? "Analysis error"
                  : "Analysis ready"
            }
          />
        </div>
      </section>

      <section className="metric-grid" aria-label="Root cause summary">
        <MetricCard
          label="Events selected"
          value={selectedCount.toLocaleString()}
          helper="Choose one for event RCA or multiple for cluster RCA"
          tone={selectedCount > 0 ? "neutral" : "warning"}
          icon="warning"
        />
        <MetricCard
          label="Affected assets"
          value={
            analysis
              ? isCluster
                ? clusterResult?.affected_asset_identifiers.length.toLocaleString() ?? "0"
                : result
                  ? "1"
                  : "0"
              : "—"
          }
          helper={analysis ? "Assets represented in this analysis" : "Awaiting analysis"}
          tone="neutral"
          icon="network"
        />
        <MetricCard
          label="Root cause confidence"
          value={analysis ? `${Math.round((analysis.confidence ?? 0) * 100)}%` : "—"}
          helper={analysis ? "Separation between top candidates" : "Awaiting analysis"}
          tone={
            analysis
              ? analysis.confidence >= 0.8
                ? "healthy"
                : analysis.confidence >= 0.65
                  ? "warning"
                  : "neutral"
              : "neutral"
          }
          icon="shield"
        />
        <MetricCard
          label="Candidates"
          value={analysis ? analysis.candidates.length.toLocaleString() : "—"}
          helper="Ranked topology candidates"
          tone="neutral"
          icon="activity"
        />
      </section>

      {error ? (
        <article className="panel" style={{ marginTop: 18 }}>
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">RCA ENGINE</div>
              <h2>Analysis failed</h2>
            </div>
          </div>
          <p style={{ margin: 0, color: "#ff8899" }}>{error}</p>
        </article>
      ) : null}

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "0.82fr 1.18fr",
          gap: 18,
          marginTop: 18,
          alignItems: "stretch",
        }}
      >
        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">EVENT CORRELATION</div>
              <h2>Choose operational events</h2>
            </div>
            <span className="panel-link">
              {events?.length ?? 0} available
            </span>
          </div>

          {loading ? (
            <div style={{ color: "#8fa2b2" }}>Loading operational events…</div>
          ) : events?.length ? (
            <div style={{ display: "grid", gap: 9 }}>
              {events.map((event) => {
                const selected = selectedEventIds.includes(event.id);

                return (
                  <button
                    key={event.id}
                    type="button"
                    onClick={() => onToggleEvent(event.id)}
                    style={{
                      display: "grid",
                      gap: 7,
                      width: "100%",
                      padding: 12,
                      textAlign: "left",
                      borderRadius: 11,
                      border: selected
                        ? "1px solid rgba(72, 202, 255, .5)"
                        : "1px solid rgba(148,163,184,.1)",
                      background: selected
                        ? "rgba(57,194,255,.09)"
                        : "rgba(255,255,255,.02)",
                      color: "#e4edf5",
                      cursor: "pointer",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 9,
                      }}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background:
                            event.severity === "critical"
                              ? "#f17d82"
                              : event.severity === "high"
                                ? "#eab96a"
                                : "#56c7f7",
                          boxShadow: selected
                            ? "0 0 0 4px rgba(86,199,247,.08)"
                            : "none",
                        }}
                      />
                      <strong style={{ flex: 1, minWidth: 0 }}>
                        {event.summary.replace(event.asset_id, getEventAssetIdentifier(event))}
                      </strong>
                      <span
                        style={{
                          fontSize: 9,
                          textTransform: "uppercase",
                          color: "#8498a8",
                        }}
                      >
                        {event.status}
                      </span>
                    </div>

                    <div style={{ color: "#7f91a1", fontSize: 10 }}>
                      {getEventAssetIdentifier(event)} · {event.event_type} · {event.severity} · {formatEventTime(event.occurred_at)}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div style={{ color: "#8fa2b2", lineHeight: 1.6 }}>
              No operational events are available for root-cause analysis.
            </div>
          )}

          <div
            style={{
              display: "grid",
              gap: 9,
              marginTop: 14,
              paddingTop: 14,
              borderTop: "1px solid rgba(148,163,184,.1)",
            }}
          >
            <button
              type="button"
              onClick={() => {
                const id = selectedEventIds[0];
                if (id) {
                  void onAnalyzeEvent(id);
                }
              }}
              disabled={selectedCount !== 1 || actionLoading !== null}
              style={{
                width: "100%",
                border: 0,
                borderRadius: 10,
                padding: "12px 14px",
                background:
                  selectedCount === 1
                    ? "linear-gradient(135deg, rgba(36,147,207,.95), rgba(59,195,255,.9))"
                    : "rgba(255,255,255,.06)",
                color: selectedCount === 1 ? "#041018" : "#647786",
                fontWeight: 800,
                cursor: selectedCount === 1 ? "pointer" : "not-allowed",
              }}
            >
              {actionLoading === "single"
                ? "Analyzing event…"
                : "Analyze selected event"}
            </button>

            <button
              type="button"
              onClick={() => void onAnalyzeCluster()}
              disabled={selectedCount < 2 || actionLoading !== null}
              style={{
                width: "100%",
                borderRadius: 10,
                padding: "11px 14px",
                border: "1px solid rgba(86,199,247,.18)",
                background:
                  selectedCount >= 2
                    ? "rgba(57,194,255,.08)"
                    : "rgba(255,255,255,.02)",
                color: selectedCount >= 2 ? "#bfeaff" : "#647786",
                fontWeight: 750,
                cursor: selectedCount >= 2 ? "pointer" : "not-allowed",
              }}
            >
              {actionLoading === "cluster"
                ? "Analyzing cluster…"
                : `Analyze event cluster (${selectedCount})`}
            </button>
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">
                {isCluster ? "CLUSTER RCA" : "SINGLE EVENT RCA"}
              </div>
              <h2>
                {analysis
                  ? analysis.root_cause_identifier
                    ? `Probable root cause · ${analysis.root_cause_identifier}`
                    : "No single root cause identified"
                  : "Explainable diagnosis"}
              </h2>
            </div>
            {analysis ? (
              <span className="confidence-badge">
                {Math.round(analysis.confidence * 100)}% confidence
              </span>
            ) : null}
          </div>

          {analysis ? (
            <div style={{ display: "grid", gap: 14 }}>
              <div
                style={{
                  padding: 14,
                  borderRadius: 12,
                  background: "rgba(57,194,255,.06)",
                  border: "1px solid rgba(57,194,255,.15)",
                }}
              >
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <span
                    style={{
                      padding: "5px 8px",
                      borderRadius: 6,
                      background: "rgba(241,125,130,.09)",
                      color: "#ffb0b5",
                      fontSize: 9,
                      fontWeight: 800,
                    }}
                  >
                    {analysis.severity.toUpperCase()}
                  </span>

                  {isCluster ? (
                    <span
                      style={{
                        padding: "5px 8px",
                        borderRadius: 6,
                        background: "rgba(86,199,247,.08)",
                        color: "#9fdfff",
                        fontSize: 9,
                      }}
                    >
                      {(clusterResult?.affected_asset_identifiers ?? []).join(" · ")}
                    </span>
                  ) : (
                    <span
                      style={{
                        padding: "5px 8px",
                        borderRadius: 6,
                        background: "rgba(255,255,255,.04)",
                        color: "#a9bac7",
                        fontSize: 9,
                      }}
                    >
                      {result?.affected_asset_identifier ?? "Affected asset"}
                    </span>
                  )}
                </div>

                <p
                  style={{
                    margin: "11px 0 0",
                    color: "#c9d8e3",
                    fontSize: 12,
                    lineHeight: 1.65,
                  }}
                >
                  {analysis.explanation}
                </p>
              </div>

              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 9,
                  }}
                >
                  <span
                    style={{
                      color: "#6f8595",
                      fontSize: 9,
                      textTransform: "uppercase",
                      letterSpacing: ".12em",
                    }}
                  >
                    Candidate ranking
                  </span>
                  <span style={{ color: "#607583", fontSize: 9 }}>
                    Higher score = stronger candidate
                  </span>
                </div>

                <div style={{ display: "grid", gap: 9 }}>
                  {analysis.candidates.map((candidate, index) => (
                    <div
                      key={`${candidate.identifier}-${index}`}
                      style={{
                        padding: "11px 12px",
                        borderRadius: 10,
                        border:
                          index === 0
                            ? "1px solid rgba(73,212,157,.2)"
                            : "1px solid rgba(148,163,184,.09)",
                        background:
                          index === 0
                            ? "rgba(73,212,157,.045)"
                            : "rgba(255,255,255,.02)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 9,
                        }}
                      >
                        <span
                          style={{
                            width: 24,
                            color: "#637989",
                            fontSize: 9,
                            fontFamily:
                              "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                          }}
                        >
                          #{String(index + 1).padStart(2, "0")}
                        </span>

                        <strong style={{ flex: 1, color: "#dfeaf2" }}>
                          {candidate.identifier}
                        </strong>

                        <span
                          style={{
                            color: index === 0 ? "#88e7c1" : "#a3b4c1",
                            fontSize: 10,
                            fontWeight: 800,
                          }}
                        >
                          {candidate.score.toFixed(1)}
                        </span>
                      </div>

                      <div
                        style={{
                          height: 5,
                          margin: "8px 0 8px 33px",
                          borderRadius: 999,
                          background: "rgba(148,163,184,.08)",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${candidateBarWidth(
                              candidate.score,
                              analysis.candidates,
                            )}%`,
                            height: "100%",
                            borderRadius: 999,
                            background:
                              index === 0
                                ? "linear-gradient(90deg, rgba(73,212,157,.55), rgba(73,212,157,.95))"
                                : "rgba(86,199,247,.55)",
                          }}
                        />
                      </div>

                      <div
                        style={{
                          marginLeft: 33,
                          color: "#8093a2",
                          fontSize: 9,
                        }}
                      >
                        {candidate.asset_type} · {candidate.distance} hop
                        {candidate.distance === 1 ? "" : "s"} ·{" "}
                        {candidate.telemetry_support} telemetry ·{" "}
                        {candidate.shared_event_support} shared event
                        {candidate.shared_event_support === 1 ? "" : "s"}
                      </div>

                      {candidate.reasons.length ? (
                        <div
                          style={{
                            margin: "7px 0 0 33px",
                            color: "#a7b6c1",
                            fontSize: 9,
                            lineHeight: 1.5,
                          }}
                        >
                          {candidate.reasons.join(" · ")}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                placeItems: "center",
                minHeight: 320,
                padding: 22,
                color: "#8295a4",
                textAlign: "center",
                lineHeight: 1.65,
              }}
            >
              Select an event to inspect its candidate root causes, or select
              multiple events to identify a common upstream cause.
            </div>
          )}
        </article>
      </section>

      <section className="secondary-grid" style={{ marginTop: 18 }}>
        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">SCORING MODEL</div>
              <h2>Why a candidate wins</h2>
            </div>
          </div>

          <div style={{ display: "grid", gap: 8 }}>
            {[
              ["Asset role", "Network infrastructure receives a stronger prior than endpoints."],
              ["Topology proximity", "Closer physically connected assets rank higher."],
              ["Connectivity", "Assets with more active physical links receive additional weight."],
              ["Telemetry", "Corroborating candidate telemetry strengthens a hypothesis."],
              ["Shared impact", "Cluster RCA rewards candidates common to multiple affected assets."],
              ["Asset state", "Offline or degraded candidates receive additional weight."],
            ].map(([label, explanation]) => (
              <div
                key={label}
                style={{
                  display: "grid",
                  gridTemplateColumns: "120px 1fr",
                  gap: 12,
                  padding: "9px 0",
                  borderBottom: "1px solid rgba(148,163,184,.08)",
                }}
              >
                <strong style={{ color: "#dce7ef", fontSize: 10 }}>
                  {label}
                </strong>
                <span style={{ color: "#7f929f", fontSize: 10, lineHeight: 1.5 }}>
                  {explanation}
                </span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">OPERATING PRINCIPLE</div>
              <h2>Transparent by design</h2>
            </div>
          </div>

          <p style={{ margin: 0, color: "#94a7b5", fontSize: 11, lineHeight: 1.7 }}>
            ShipOps does not need an opaque model to produce a useful first diagnosis.
            The RCA engine exposes the candidate score, supporting factors, topology
            distance, telemetry support, and shared-event evidence so an operator can
            challenge or validate the conclusion.
          </p>
        </article>
      </section>
    </>
  );
}

function TelemetryPage({
  events,
  topology,
  loading,
  actionLoading,
  actionError,
  lastSubmission,
  sessionSamples,
  onRefresh,
  onSubmit,
  onOpenIncident,
  onRunThresholdTest,
}: {
  events: OperationalEvent[] | null;
  topology: TopologyGraphResponse | null;
  loading: boolean;
  actionLoading: string | null;
  actionError: string | null;
  lastSubmission: TelemetryIngestResponse | null;
  sessionSamples: number;
  onRefresh: () => void;
  onSubmit: (payload: {
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
  }) => Promise<void>;
  onOpenIncident: (eventId: string) => void;
  onRunThresholdTest: () => Promise<void>;
}) {
  const assetOptions = Array.from(
    new Set((topology?.nodes ?? []).map((node) => node.identifier)),
  );
  const [assetIdentifier, setAssetIdentifier] = useState(assetOptions[0] ?? "SW-07");
  const [metric, setMetric] = useState("packet_loss");
  const [value, setValue] = useState("38");
  const [unit, setUnit] = useState("percent");
  const [source, setSource] = useState("telemetry-console");
  const [quality, setQuality] = useState("good");
  const [sourceSequence, setSourceSequence] = useState(() => Date.now());
  const [extraData, setExtraData] = useState('{"interface":"eth0"}');


  const latestEvents = (events ?? [])
    .slice()
    .sort(
      (left, right) =>
        new Date(right.occurred_at).getTime() - new Date(left.occurred_at).getTime(),
    )
    .slice(0, 6);

  const assetIdentifierById = new Map(
    (topology?.nodes ?? []).map((node) => [node.asset_id, node.identifier]),
  );

  const getEventAssetIdentifier = (event: OperationalEvent) =>
    assetIdentifierById.get(event.asset_id) ?? event.asset_id;

  const getEventSummary = (event: OperationalEvent) =>
    event.summary.replace(event.asset_id, getEventAssetIdentifier(event));

  const submit = async () => {
    let parsedExtra: Record<string, unknown> | undefined;
    if (extraData.trim()) {
      try {
        const candidate = JSON.parse(extraData);
        if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
          throw new Error("Extra data must be a JSON object.");
        }
        parsedExtra = candidate as Record<string, unknown>;
      } catch {
        return;
      }
    }

    await onSubmit({
      asset_identifier: assetIdentifier.trim(),
      metric: metric.trim(),
      value: Number(value),
      unit: unit.trim(),
      observed_at: new Date().toISOString(),
      received_at: new Date().toISOString(),
      source: source.trim(),
      source_sequence: Number(sourceSequence),
      quality: quality.trim(),
      idempotency_key: `WEB-${assetIdentifier}-${metric}-${Date.now()}`,
      extra_data: parsedExtra,
    });
    setSourceSequence((current) => current + 1);
  };

  const statusTone = actionError ? "critical" : lastSubmission ? "healthy" : "neutral";

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">OBSERVABILITY PIPELINE</div>
          <h1>Telemetry ingestion</h1>
          <p>
            Submit real telemetry into the edge ingestion path, inspect recent event outcomes,
            and exercise the rule-driven incident pipeline without bypassing the backend.
          </p>
        </div>
        <div className="page-heading__status">
          <StatusDot
            tone={statusTone}
            label={loading ? "Refreshing" : actionError ? "Ingestion error" : lastSubmission ? "Ingestion live" : "Ready"}
          />
          <button
            className="panel-link"
            type="button"
            onClick={onRefresh}
            disabled={loading}
            style={{ background: "none", border: 0, cursor: "pointer" }}
          >
            Refresh events
          </button>
        </div>
      </section>

      <section className="metric-grid" aria-label="Telemetry summary">
        <MetricCard
          label="Samples this session"
          value={sessionSamples.toLocaleString()}
          helper="Accepted from this console"
          tone="neutral"
          icon="activity"
        />
        <MetricCard
          label="Active incidents"
          value={(events ?? []).filter((event) => event.status !== "resolved").length.toLocaleString()}
          helper="Persisted operational events"
          tone={(events ?? []).some((event) => event.status !== "resolved") ? "warning" : "healthy"}
          icon="warning"
        />
        <MetricCard
          label="Latest metric"
          value={lastSubmission?.metric ?? "—"}
          helper={lastSubmission?.asset_identifier ? `Asset ${lastSubmission.asset_identifier}` : "Awaiting sample"}
          tone="neutral"
          icon="pulse"
        />
        <MetricCard
          label="Pipeline state"
          value={lastSubmission ? "Accepted" : "Ready"}
          helper="Ingest → persist → rule evaluation"
          tone={lastSubmission ? "healthy" : "neutral"}
          icon="shield"
        />
      </section>

      {actionError ? (
        <article className="panel" style={{ marginTop: 18 }}>
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">INGESTION RESULT</div>
              <h2>Telemetry submission failed</h2>
            </div>
          </div>
          <p style={{ margin: 0, color: "#ff8899", lineHeight: 1.6 }}>{actionError}</p>
        </article>
      ) : null}

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "1.05fr .95fr",
          gap: 18,
          marginTop: 18,
          alignItems: "stretch",
        }}
      >
        <article className="panel panel--wide">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">TELEMETRY INGESTION</div>
              <h2>Submit a telemetry sample</h2>
            </div>
            <span className="panel-link">POST /api/v1/telemetry</span>
          </div>

          <div style={{ display: "grid", gap: 13 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Asset</span>
                <select
                  value={assetIdentifier}
                  onChange={(event) => setAssetIdentifier(event.target.value)}
                  style={{ width: "100%", boxSizing: "border-box" }}
                >
                  {assetOptions.length ? (
                    assetOptions.map((asset) => <option key={asset}>{asset}</option>)
                  ) : (
                    <option>SW-07</option>
                  )}
                </select>
              </label>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Metric</span>
                <input value={metric} onChange={(event) => setMetric(event.target.value)} />
              </label>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Value</span>
                <input type="number" value={value} onChange={(event) => setValue(event.target.value)} />
              </label>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Unit</span>
                <input value={unit} onChange={(event) => setUnit(event.target.value)} />
              </label>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Source</span>
                <input value={source} onChange={(event) => setSource(event.target.value)} />
              </label>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Quality</span>
                <select value={quality} onChange={(event) => setQuality(event.target.value)}>
                  <option>good</option>
                  <option>suspect</option>
                  <option>bad</option>
                </select>
              </label>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Source sequence</span>
                <input type="number" value={sourceSequence} onChange={(event) => setSourceSequence(Number(event.target.value))} />
              </label>
              <label style={{ display: "grid", gap: 7 }}>
                <span className="field-label">Extra data</span>
                <input value={extraData} onChange={(event) => setExtraData(event.target.value)} />
              </label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 10 }}>
              <div
                style={{
                  padding: 13,
                  borderRadius: 11,
                  background: "rgba(57,194,255,.05)",
                  border: "1px solid rgba(57,194,255,.12)",
                }}
              >
                <span style={{ display: "block", color: "#7f95a7", fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em" }}>
                  Pipeline
                </span>
                <strong style={{ display: "block", marginTop: 6, color: "#dce8f2", fontSize: 13 }}>
                  Accept sample → persist observation → evaluate event rules → attach evidence
                </strong>
              </div>
              <button
                type="button"
                onClick={() => void submit()}
                disabled={actionLoading === "telemetry"}
                style={{
                  border: 0,
                  borderRadius: 11,
                  padding: "12px 18px",
                  background: "linear-gradient(135deg, rgba(36,147,207,.95), rgba(59,195,255,.9))",
                  color: "#041018",
                  fontWeight: 800,
                  cursor: "pointer",
                  minWidth: 170,
                }}
              >
                {actionLoading === "telemetry" ? "Ingesting…" : "Ingest telemetry"}
              </button>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">CONTROLLED TEST</div>
              <h2>Trigger a sustained threshold</h2>
            </div>
            <span className="panel-link">packet_loss &gt; 30%</span>
          </div>
          <p style={{ margin: "0 0 14px", color: "#93a6b6", lineHeight: 1.65, fontSize: 12 }}>
            Send three historical packet-loss observations against SW-07 so the persisted rule can demonstrate sustained-condition evaluation and event creation.
          </p>
          <button
            type="button"
            onClick={() => void onRunThresholdTest()}
            disabled={actionLoading === "threshold-test"}
            style={{
              width: "100%",
              borderRadius: 11,
              padding: "12px 15px",
              border: "1px solid rgba(255,179,71,.25)",
              background: "rgba(255,179,71,.08)",
              color: "#ffd18a",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            {actionLoading === "threshold-test" ? "Running threshold test…" : "Run 3-point packet-loss test"}
          </button>
          {lastSubmission ? (
            <div style={{ marginTop: 14, color: "#8ea2b1", fontSize: 11, lineHeight: 1.6 }}>
              Last accepted sample: <strong style={{ color: "#dbe7ef" }}>{lastSubmission.metric ?? "metric"}</strong>
              {lastSubmission.asset_identifier ? ` on ${lastSubmission.asset_identifier}` : ""}.
            </div>
          ) : null}
        </article>
      </section>

      <section className="secondary-grid" style={{ marginTop: 18 }}>
        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">RECENT EVENTS</div>
              <h2>Telemetry-driven incidents</h2>
            </div>
            <span className="panel-link">{latestEvents.length} shown</span>
          </div>
          {latestEvents.length ? (
            <div style={{ display: "grid", gap: 9 }}>
              {latestEvents.map((event) => (
                <button
                  type="button"
                  key={event.id}
                  onClick={() => onOpenIncident(event.id)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    padding: "11px 12px",
                    borderRadius: 10,
                    border: "1px solid rgba(148,163,184,.1)",
                    background: "rgba(255,255,255,.02)",
                    color: "inherit",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <strong style={{ flex: 1, minWidth: 0, color: "#dce8f2" }}>
                      {getEventSummary(event)}
                    </strong>
                    <StatusDot
                      tone={event.status === "resolved" ? "healthy" : event.severity === "critical" ? "critical" : "warning"}
                      label={event.status}
                    />
                  </div>
                  <div style={{ marginTop: 5, color: "#7f91a3", fontSize: 10 }}>
                    {getEventAssetIdentifier(event)} · {event.event_type} · {event.severity} · {event.evidence.length} evidence records
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ color: "#8799a9", lineHeight: 1.6 }}>
              No persisted operational events are currently available.
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">OBSERVABILITY MODEL</div>
              <h2>What this page proves</h2>
            </div>
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            {[
              ["Ingestion", "Validated telemetry enters the same backend pipeline used by vessel-side sources."],
              ["Persistence", "Samples become durable observations rather than UI-only values."],
              ["Rules", "Sustained threshold conditions are evaluated against historical observations."],
              ["Evidence", "Triggered events retain the threshold-breach observations that led to the decision."],
              ["Investigation", "Incidents feed directly into the RCA and topology workflows."],
            ].map(([title, description]) => (
              <div key={title} style={{ display: "grid", gridTemplateColumns: "92px 1fr", gap: 10, paddingBottom: 9, borderBottom: "1px solid rgba(148,163,184,.08)" }}>
                <strong style={{ color: "#d8e4ec", fontSize: 11 }}>{title}</strong>
                <span style={{ color: "#7f91a3", fontSize: 11, lineHeight: 1.55 }}>{description}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </>
  );
}

function App() {
  const [activeItem, setActiveItem] = useState("Overview");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [connectivity, setConnectivity] =
    useState<ConnectivityStatusResponse | null>(null);
  const [connectivityError, setConnectivityError] =
    useState<string | null>(null);
  const [connectivityMetrics, setConnectivityMetrics] =
    useState<ConnectivityMetricsResponse | null>(null);
  const [connectivityMetricsError, setConnectivityMetricsError] =
    useState<string | null>(null);
  const [events, setEvents] = useState<OperationalEvent[] | null>(null);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<OperationalEvent | null>(null);
  const [incidentDetailLoading, setIncidentDetailLoading] = useState(false);
  const [incidentActionLoading, setIncidentActionLoading] = useState<string | null>(null);
  const [incidentActionError, setIncidentActionError] = useState<string | null>(null);
  const [incidentRca, setIncidentRca] = useState<RCAEventResponse | null>(null);
  const [incidentRcaError, setIncidentRcaError] = useState<string | null>(null);
  const [rootCauseResult, setRootCauseResult] = useState<RCAEventResponse | null>(null);
  const [rootCauseClusterResult, setRootCauseClusterResult] = useState<RCAClusterResponse | null>(null);
  const [rootCauseSelectedEventIds, setRootCauseSelectedEventIds] = useState<string[]>([]);
  const [topology, setTopology] = useState<TopologyGraphResponse | null>(null);
  const [topologyLoading, setTopologyLoading] = useState(false);
  const [topologyError, setTopologyError] = useState<string | null>(null);
  const [selectedTopologyAsset, setSelectedTopologyAsset] = useState<string | null>(null);
  const [topologyImpact, setTopologyImpact] = useState<TopologyImpactResponse | null>(null);
  const [topologyImpactLoading, setTopologyImpactLoading] = useState(false);
  const [topologyImpactError, setTopologyImpactError] = useState<string | null>(null);
  const [trafficDecision, setTrafficDecision] = useState<ConnectivityTrafficDecision | null>(null);
  const [connectivityActionLoading, setConnectivityActionLoading] = useState<string | null>(null);
  const [connectivityActionError, setConnectivityActionError] = useState<string | null>(null);
  const [retryResult, setRetryResult] = useState<ConnectivityRetryResponse | null>(null);
  const [simulation, setSimulation] = useState<ConnectivitySimulationResponse | null>(null);
  const [telemetryActionLoading, setTelemetryActionLoading] = useState<string | null>(null);
  const [telemetryActionError, setTelemetryActionError] = useState<string | null>(null);
  const [telemetryLastSubmission, setTelemetryLastSubmission] = useState<TelemetryIngestResponse | null>(null);
  const [telemetrySessionSamples, setTelemetrySessionSamples] = useState(0);

  useEffect(() => {
    let cancelled = false;

    getHealth()
      .then((response) => {
        if (!cancelled) {
          setHealth(response);
          setHealthError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setHealthError(
            error instanceof Error
              ? error.message
              : "Unable to reach the ShipOps API.",
          );
        }
      });

    getConnectivityStatus()
      .then((response) => {
        if (!cancelled) {
          setConnectivity(response);
          setConnectivityError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setConnectivityError(
            error instanceof Error
              ? error.message
              : "Unable to load connectivity status.",
          );
        }
      });

    getConnectivityMetrics()
      .then((response) => {
        if (!cancelled) {
          setConnectivityMetrics(response);
          setConnectivityMetricsError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setConnectivityMetricsError(
            error instanceof Error
              ? error.message
              : "Unable to load connectivity metrics.",
          );
        }
      });

    getEvents(10)
      .then((response) => {
        if (!cancelled) {
          setEvents(response.items);
          setEventsError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setEventsError(
            error instanceof Error
              ? error.message
              : "Unable to load operational events.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const healthTone: "healthy" | "warning" | "critical" | "neutral" =
    health?.status === "healthy"
      ? "healthy"
      : health?.status === "degraded"
        ? "warning"
        : healthError
          ? "critical"
          : "neutral";

  const healthLabel = health
    ? health.status === "healthy"
      ? "All core systems operational"
      : "Core systems degraded"
    : healthError
      ? "API connection unavailable"
      : "Checking core systems";

  const healthValue = health
    ? health.status === "healthy"
      ? "Healthy"
      : "Degraded"
    : healthError
      ? "Offline"
      : "Checking";

  const healthHelper = health
    ? `${health.service} · ${health.environment}`
    : healthError
      ? healthError
      : "Connecting to ShipOps API";

  const connectivityAvailable = connectivity?.link.available_kbps ?? 0;
  const connectivityCapacity = connectivity?.link.capacity_kbps ?? 0;
  const connectivityUsed = Math.max(
    connectivityCapacity - connectivityAvailable,
    0,
  );
  const queuedKb = connectivity?.usage.queued_kbps ?? 0;
  const formattedQueuedTraffic =
    connectivity !== null
      ? queuedKb >= 1024
        ? `${(queuedKb / 1024).toFixed(1)} MB`
        : `${queuedKb.toLocaleString()} KB`
      : "—";
  const connectivityTone =
    connectivity?.link.state === "available"
      ? "healthy"
      : connectivity?.link.state === "degraded"
        ? "warning"
        : connectivity
          ? "critical"
          : "neutral";
  const connectivityLabel = connectivity
    ? connectivity.link.state === "available"
      ? "Available"
      : connectivity.link.state.replace("_", " ")
    : connectivityError
      ? "Unavailable"
      : "Checking";
  const connectivityHelper = connectivity
    ? connectivityMetrics
      ? `${connectivityMetrics.traffic.total_requests} requests · ${connectivityMetrics.traffic.queued_requests} queued`
      : `${Math.round(
          connectivityCapacity > 0
            ? (connectivityAvailable / connectivityCapacity) * 100
            : 0,
        )}% of satellite capacity`
    : connectivityError
      ? connectivityError
      : "Loading connectivity status";

  const transmittedKbps = connectivityMetrics?.bandwidth_kbps.transmitted ?? 0;
  const throttledKbps = connectivityMetrics?.bandwidth_kbps.throttled ?? 0;
  const queuedKbps = connectivityMetrics?.bandwidth_kbps.queued ?? 0;
  const metricsStatus = connectivityMetrics
    ? "Live accounting"
    : connectivityMetricsError
      ? "Metrics unavailable"
      : "Loading metrics";

  const activeEvents = (events ?? []).filter(
    (event) => event.status !== "resolved",
  );

  const displayedEvents = activeEvents
    .slice()
    .sort(
      (left, right) =>
        new Date(right.occurred_at).getTime() -
        new Date(left.occurred_at).getTime(),
    )
    .slice(0, 3);

  const assetIdentifierById = new Map(
    (topology?.nodes ?? []).map((node) => [node.asset_id, node.identifier]),
  );

  const getEventAssetIdentifier = (event: OperationalEvent) =>
    assetIdentifierById.get(event.asset_id) ?? event.asset_id;

  const criticalEventCount = activeEvents.filter(
    (event) => event.severity === "critical",
  ).length;
  const highEventCount = activeEvents.filter(
    (event) => event.severity === "high",
  ).length;

  const incidentHelper =
    events !== null
      ? activeEvents.length === 0
        ? "No active incidents"
        : `${criticalEventCount} critical · ${highEventCount} high`
      : eventsError
        ? "Unable to load incidents"
        : "Loading incidents";

  const loadTopology = () => {
    setTopologyLoading(true);
    setTopologyError(null);
    getTopologyGraph()
      .then((response) => {
        setTopology(response);
        setTopologyLoading(false);
        setTopologyError(null);
        setTopologyImpact(null);
        setTopologyImpactError(null);
        if (response.nodes.length > 0) {
          setSelectedTopologyAsset(
            (current) => current ?? response.nodes[0].identifier,
          );
        }
      })
      .catch((error: unknown) => {
        setTopologyLoading(false);
        setTopologyError(
          error instanceof Error
            ? error.message
            : "Unable to load network topology.",
        );
      });
  };

  const isTopologyPage = activeItem === "Network Topology";
  const isConnectivityPage = activeItem === "Connectivity";
  const isIncidentPage = activeItem === "Incidents";
  const isRootCausePage = activeItem === "Root Cause";
  const isTelemetryPage = activeItem === "Telemetry";

  const selectTopologyAsset = (identifier: string) => {
    setSelectedTopologyAsset(identifier);
    setTopologyImpact(null);
    setTopologyImpactLoading(true);
    setTopologyImpactError(null);
  };

  useEffect(() => {
    if (!isTopologyPage || !selectedTopologyAsset) {
      return;
    }

    let cancelled = false;

    getTopologyImpact(selectedTopologyAsset)
      .then((response) => {
        if (!cancelled) {
          setTopologyImpact(response);
          setTopologyImpactLoading(false);
          setTopologyImpactError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setTopologyImpactLoading(false);
          setTopologyImpact(null);
          setTopologyImpactError(
            error instanceof Error
              ? error.message
              : "Unable to calculate topology impact.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isTopologyPage, selectedTopologyAsset]);


  const loadConnectivity = () => {
    setConnectivityActionLoading("refresh");
    setConnectivityActionError(null);
    Promise.all([getConnectivityStatus(), getConnectivityMetrics()])
      .then(([status, metrics]) => {
        setConnectivity(status);
        setConnectivityMetrics(metrics);
        setConnectivityError(null);
        setConnectivityMetricsError(null);
        setConnectivityActionLoading(null);
      })
      .catch((error: unknown) => {
        setConnectivityActionLoading(null);
        setConnectivityActionError(
          error instanceof Error ? error.message : "Unable to refresh connectivity.",
        );
      });
  };

  const handleTrafficSubmit = async (payload: {
    traffic_id: string;
    traffic_class: TrafficClass;
    size_kb: number;
    required_kbps: number;
    deadline?: number | null;
  }) => {
    setConnectivityActionLoading("traffic");
    setConnectivityActionError(null);
    try {
      const decision = await submitConnectivityTraffic(payload);
      setTrafficDecision(decision);
      const status = await getConnectivityStatus();
      const metrics = await getConnectivityMetrics();
      setConnectivity(status);
      setConnectivityMetrics(metrics);
    } catch (error: unknown) {
      setConnectivityActionError(
        error instanceof Error ? error.message : "Unable to evaluate connectivity traffic.",
      );
    } finally {
      setConnectivityActionLoading(null);
    }
  };

  const handleLinkUpdate = async (state: ConnectivityState, availableKbps: number) => {
    setConnectivityActionLoading("link");
    setConnectivityActionError(null);
    try {
      await updateConnectivityLink(state, availableKbps);
      const [status, metrics] = await Promise.all([
        getConnectivityStatus(),
        getConnectivityMetrics(),
      ]);
      setConnectivity(status);
      setConnectivityMetrics(metrics);
      setConnectivityError(null);
    } catch (error: unknown) {
      setConnectivityActionError(
        error instanceof Error ? error.message : "Unable to update connectivity link.",
      );
    } finally {
      setConnectivityActionLoading(null);
    }
  };

  const handleRetryQueue = async () => {
    setConnectivityActionLoading("retry");
    setConnectivityActionError(null);
    try {
      const result = await retryConnectivityQueue();
      setRetryResult(result);
      const [status, metrics] = await Promise.all([
        getConnectivityStatus(),
        getConnectivityMetrics(),
      ]);
      setConnectivity(status);
      setConnectivityMetrics(metrics);
    } catch (error: unknown) {
      setConnectivityActionError(
        error instanceof Error ? error.message : "Unable to retry connectivity queue.",
      );
    } finally {
      setConnectivityActionLoading(null);
    }
  };

  const handleSimulation = async () => {
    setConnectivityActionLoading("simulate");
    setConnectivityActionError(null);
    try {
      const result = await runConnectivitySimulation();
      setSimulation(result);
    } catch (error: unknown) {
      setConnectivityActionError(
        error instanceof Error ? error.message : "Unable to run connectivity simulation.",
      );
    } finally {
      setConnectivityActionLoading(null);
    }
  };


  const loadEvents = async () => {
    setIncidentActionLoading("refresh");
    setIncidentActionError(null);
    try {
      const response = await getEvents(100);
      setEvents(response.items);
      setEventsError(null);
      if (selectedEvent) {
        const refreshed = response.items.find((event) => event.id === selectedEvent.id);
        if (refreshed) {
          setSelectedEvent(refreshed);
        }
      }
    } catch (error: unknown) {
      setEventsError(error instanceof Error ? error.message : "Unable to load operational events.");
      setIncidentActionError(error instanceof Error ? error.message : "Unable to load operational events.");
    } finally {
      setIncidentActionLoading(null);
    }
  };

  const handleIncidentSelect = async (eventId: string) => {
    setIncidentDetailLoading(true);
    setIncidentActionError(null);
    setIncidentRca(null);
    setIncidentRcaError(null);
    try {
      const event = await getEvent(eventId);
      setSelectedEvent(event);
    } catch (error: unknown) {
      setIncidentActionError(error instanceof Error ? error.message : "Unable to load the selected event.");
    } finally {
      setIncidentDetailLoading(false);
    }
  };

  const handleIncidentAcknowledge = async (eventId: string) => {
    setIncidentActionLoading("acknowledge");
    setIncidentActionError(null);
    try {
      const event = await acknowledgeEvent(eventId);
      setSelectedEvent(event);
      const response = await getEvents(100);
      setEvents(response.items);
    } catch (error: unknown) {
      setIncidentActionError(error instanceof Error ? error.message : "Unable to acknowledge event.");
    } finally {
      setIncidentActionLoading(null);
    }
  };

  const handleIncidentResolve = async (eventId: string) => {
    setIncidentActionLoading("resolve");
    setIncidentActionError(null);
    try {
      const event = await resolveEvent(eventId);
      setSelectedEvent(event);
      const response = await getEvents(100);
      setEvents(response.items);
    } catch (error: unknown) {
      setIncidentActionError(error instanceof Error ? error.message : "Unable to resolve event.");
    } finally {
      setIncidentActionLoading(null);
    }
  };

  const handleIncidentRca = async (eventId: string) => {
    setIncidentActionLoading("rca");
    setIncidentActionError(null);
    setIncidentRcaError(null);
    try {
      const result = await getRCAEvent(eventId);
      setIncidentRca(result);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Unable to run deterministic RCA.";
      setIncidentRcaError(message);
      setIncidentActionError(message);
    } finally {
      setIncidentActionLoading(null);
    }
  };

  const toggleRootCauseEvent = (eventId: string) => {
    setRootCauseSelectedEventIds((current) =>
      current.includes(eventId)
        ? current.filter((id) => id !== eventId)
        : [...current, eventId],
    );
    setRootCauseResult(null);
    setRootCauseClusterResult(null);
  };

  const handleRootCauseEvent = async (eventId: string) => {
    setIncidentActionLoading("single");
    setIncidentActionError(null);

    try {
      const result = await getRCAEvent(eventId);
      setRootCauseResult(result);
      setRootCauseClusterResult(null);
    } catch (error: unknown) {
      setIncidentActionError(
        error instanceof Error
          ? error.message
          : "Unable to run deterministic RCA.",
      );
    } finally {
      setIncidentActionLoading(null);
    }
  };

  const handleRootCauseCluster = async () => {
    setIncidentActionLoading("cluster");
    setIncidentActionError(null);

    try {
      const result = await getRCACluster(rootCauseSelectedEventIds);
      setRootCauseClusterResult(result);
      setRootCauseResult(null);
    } catch (error: unknown) {
      setIncidentActionError(
        error instanceof Error
          ? error.message
          : "Unable to run cluster RCA.",
      );
    } finally {
      setIncidentActionLoading(null);
    }
  };

  const handleTelemetrySubmit = async (payload: {
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
  }) => {
    setTelemetryActionLoading("telemetry");
    setTelemetryActionError(null);
    try {
      const result = await submitTelemetry(payload);
      setTelemetryLastSubmission(result);
      setTelemetrySessionSamples((current) => current + 1);
      await loadEvents();
    } catch (error: unknown) {
      setTelemetryActionError(
        error instanceof Error ? error.message : "Unable to ingest telemetry sample.",
      );
    } finally {
      setTelemetryActionLoading(null);
    }
  };

  const handleTelemetryThresholdTest = async () => {
    setTelemetryActionLoading("threshold-test");
    setTelemetryActionError(null);
    try {
      const now = Date.now();
      const points = [
        { offset: 180000, value: 38 },
        { offset: 90000, value: 41 },
        { offset: 0, value: 37 },
      ];

      for (const [index, point] of points.entries()) {
        const result = await submitTelemetry({
          asset_identifier: "SW-07",
          metric: "packet_loss",
          value: point.value,
          unit: "percent",
          observed_at: new Date(now - point.offset).toISOString(),
          received_at: new Date().toISOString(),
          source: "telemetry-console",
          source_sequence: now + index,
          quality: "good",
          idempotency_key: `THRESHOLD-${now}-${index}`,
          extra_data: { test: "sustained-threshold", threshold: 30 },
        });
        setTelemetryLastSubmission(result);
        setTelemetrySessionSamples((current) => current + 1);
      }

      await loadEvents();
    } catch (error: unknown) {
      setTelemetryActionError(
        error instanceof Error ? error.message : "Unable to run telemetry threshold test.",
      );
    } finally {
      setTelemetryActionLoading(null);
    }
  };

  const handleTelemetryOpenIncident = (eventId: string) => {
    setActiveItem("Incidents");
    void handleIncidentSelect(eventId);
    void loadEvents();
  };

  const handleNavigation = (label: string) => {
    setActiveItem(label);

    if (label === "Network Topology") {
      loadTopology();
    }

    if (label === "Connectivity") {
      loadConnectivity();
    }

    if (label === "Incidents") {
      void loadEvents();
    }
    if (label === "Root Cause") {
      void loadEvents();
      loadTopology();
    }

    if (label === "Telemetry") {
      void loadEvents();
      loadTopology();
      setTelemetryActionError(null);
    }
  };

  return (
    <div className="shipops-app">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <div className="brand-mark">
            <span className="brand-mark__ring" />
            <span className="brand-mark__core" />
          </div>

          <div className="brand-copy">
            <span className="brand-copy__name">
              ShipOps
            </span>
            <span className="brand-copy__sub">
              Edge Operations
            </span>
          </div>
        </div>

        <div className="sidebar__section-label">
          Operations
        </div>

        <nav
          className="sidebar__nav"
          aria-label="Primary"
        >
          {primaryNavigation.map((item) => {
            const isActive =
              activeItem === item.label;

            return (
              <button
                key={item.label}
                className={`nav-item ${
                  isActive
                    ? "nav-item--active"
                    : ""
                }`}
                onClick={() =>
                  handleNavigation(item.label)
                }
                type="button"
              >
                <span className="nav-item__icon">
                  <Icon
                    name={item.icon}
                    size={17}
                  />
                </span>

                <span>{item.label}</span>

                {item.badge ? (
                  <span className="nav-item__badge">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="sidebar__spacer" />

        <div className="sidebar__section-label">
          System
        </div>

        <button
          className={`nav-item ${
            activeItem === "Settings"
              ? "nav-item--active"
              : ""
          }`}
          onClick={() =>
            setActiveItem("Settings")
          }
          type="button"
        >
          <span className="nav-item__icon">
            <Icon
              name="settings"
              size={17}
            />
          </span>

          <span>Settings</span>
        </button>

        <div className="sidebar__footer">
          <div className="fleet-status">
            <span className="status-pulse status-pulse--healthy" />

            <div>
              <strong>MV Aurora</strong>
              <span>Vessel online</span>
            </div>

            <Icon
              name="chevron"
              size={15}
            />
          </div>

          <div className="sidebar__version">
            SHIPOPS · 0.1.0
          </div>
        </div>
      </aside>

      <main className="main-shell">
        <header className="topbar">
          <div className="topbar__breadcrumb">
            <span>Operations</span>

            <Icon
              name="chevron"
              size={13}
            />

            <strong>{activeItem}</strong>
          </div>

          <div className="topbar__actions">
            <button
              className="icon-button"
              type="button"
              aria-label="Search"
            >
              <Icon
                name="search"
                size={18}
              />
            </button>

            <button
              className="notification-button"
              type="button"
              aria-label="Notifications"
            >
              <Icon
                name="bell"
                size={18}
              />
              <span />
            </button>

            <div className="operator">
              <div className="operator__avatar">
                OP
              </div>

              <div className="operator__copy">
                <strong>Operations</strong>
                <span>Deck systems</span>
              </div>

              <Icon
                name="chevron"
                size={14}
              />
            </div>
          </div>
        </header>

        <div className="main-content">
          {isIncidentPage ? (
            <IncidentPage
              events={events}
              selectedEvent={selectedEvent}
              rca={incidentRca}
              loading={incidentActionLoading === "refresh"}
              detailLoading={incidentDetailLoading}
              actionLoading={incidentActionLoading}
              error={eventsError}
              actionError={incidentActionError ?? incidentRcaError}
              onRefresh={() => void loadEvents()}
              onSelect={(eventId) => void handleIncidentSelect(eventId)}
              onAcknowledge={handleIncidentAcknowledge}
              onResolve={handleIncidentResolve}
              onRunRca={handleIncidentRca}
              topology={topology}
            />
          ) : isTopologyPage ? (
            <TopologyPage
              graph={topology}
              selectedAsset={selectedTopologyAsset}
              impact={topologyImpact}
              loading={topologyLoading}
              impactLoading={topologyImpactLoading}
              error={topologyError}
              impactError={topologyImpactError}
              onSelectAsset={selectTopologyAsset}
              onRefresh={loadTopology}
            />
          ) : isConnectivityPage ? (
            <ConnectivityPage
              connectivity={connectivity}
              metrics={connectivityMetrics}
              error={connectivityError}
              metricsError={connectivityMetricsError}
              trafficDecision={trafficDecision}
              actionLoading={connectivityActionLoading}
              actionError={connectivityActionError}
              retryResult={retryResult}
              simulation={simulation}
              onRefresh={loadConnectivity}
              onSubmitTraffic={handleTrafficSubmit}
              onUpdateLink={handleLinkUpdate}
              onRetryQueue={handleRetryQueue}
              onSimulate={handleSimulation}
            />
          ) : isRootCausePage ? (
            <RootCausePage
              events={events}
              loading={incidentActionLoading === "refresh"}
              selectedEventIds={rootCauseSelectedEventIds}
              onToggleEvent={toggleRootCauseEvent}
              onAnalyzeEvent={handleRootCauseEvent}
              onAnalyzeCluster={handleRootCauseCluster}
              result={rootCauseResult}
              clusterResult={rootCauseClusterResult}
              actionLoading={incidentActionLoading}
              error={incidentActionError}
              topology={topology}
            />
          ) : isTelemetryPage ? (
            <TelemetryPage
              events={events}
              topology={topology}
              loading={telemetryActionLoading === "refresh"}
              actionLoading={telemetryActionLoading}
              actionError={telemetryActionError}
              lastSubmission={telemetryLastSubmission}
              sessionSamples={telemetrySessionSamples}
              onRefresh={() => void loadEvents()}
              onSubmit={handleTelemetrySubmit}
              onOpenIncident={handleTelemetryOpenIncident}
              onRunThresholdTest={handleTelemetryThresholdTest}
            />
          ) : (
            <>
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                VESSEL OPERATIONS
              </div>

              <h1>Operations overview</h1>

              <p>
                Current IT infrastructure health
                across the vessel edge environment.
              </p>
            </div>

            <div className="page-heading__status">
              <StatusDot
                tone={healthTone}
                label={healthLabel}
              />

              <span className="last-updated">
                {health ? "Live from ShipOps API" : "Connecting to ShipOps API"}
              </span>
            </div>
          </section>

          <section
            className="metric-grid"
            aria-label="Operational summary"
          >
            <MetricCard
              label="System health"
              value={healthValue}
              helper={healthHelper}
              tone={healthTone}
              icon="pulse"
            />

            <MetricCard
              label="Connectivity"
              value={
                connectivity
                  ? `${connectivityAvailable.toLocaleString()} Kbps`
                  : "—"
              }
              helper={connectivityHelper}
              tone={connectivityTone}
              icon="connectivity"
            />

            <MetricCard
              label="Active incidents"
              value={events !== null ? activeEvents.length.toLocaleString() : "—"}
              helper={incidentHelper}
              tone={
                events !== null && activeEvents.length === 0
                  ? "healthy"
                  : eventsError
                    ? "critical"
                    : "warning"
              }
              icon="warning"
            />

            <MetricCard
              label="Queued traffic"
              value={formattedQueuedTraffic}
              helper={
                connectivity
                  ? `${connectivity.queued_traffic.length} queued requests`
                  : "Loading connectivity status"
              }
              tone={connectivity?.usage.queued_requests ? "warning" : "neutral"}
              icon="activity"
            />
          </section>

          <section className="primary-grid">
            <article className="panel panel--wide">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">
                    CONNECTIVITY
                  </div>

                  <h2>Satellite link</h2>
                </div>

                <StatusDot
                  tone={connectivityTone}
                  label={connectivityLabel}
                />
              </div>

              <div className="connectivity-layout">
                <ConnectivityGauge connectivity={connectivity} />

                <div className="bandwidth-chart">
                  <div className="chart-heading">
                    <div>
                      <span>
                        Bandwidth utilization
                      </span>
                      <strong>
                        {connectivityMetrics
                          ? `${transmittedKbps.toLocaleString()} Kbps transmitted`
                          : connectivity
                            ? `${connectivityUsed.toLocaleString()} Kbps in use`
                            : "—"}
                      </strong>
                    </div>

                    <span className="chart-period">
                      {metricsStatus}
                    </span>
                  </div>

                  <div className="chart-area">
                    <div className="chart-grid-line chart-grid-line--1" />
                    <div className="chart-grid-line chart-grid-line--2" />
                    <div className="chart-grid-line chart-grid-line--3" />
                    <div className="chart-grid-line chart-grid-line--4" />

                    <div className="chart-label chart-label--top">
                      1.0 Mbps
                    </div>

                    <div className="chart-label chart-label--middle">
                      500 Kbps
                    </div>

                    <div className="chart-label chart-label--bottom">
                      0
                    </div>

                    <svg
                      className="bandwidth-svg"
                      viewBox="0 0 560 190"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                    >
                      <defs>
                        <linearGradient
                          id="areaFill"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="rgba(64, 185, 255, 0.24)"
                          />

                          <stop
                            offset="100%"
                            stopColor="rgba(64, 185, 255, 0)"
                          />
                        </linearGradient>
                      </defs>

                      <path
                        d="M0 138 C38 144 55 126 85 131 C119 137 132 106 162 113 C191 119 204 93 236 101 C271 109 286 79 318 88 C355 98 368 65 399 74 C430 84 448 53 480 62 C512 71 531 48 560 53 L560 190 L0 190 Z"
                        fill="url(#areaFill)"
                      />

                      <path
                        d="M0 138 C38 144 55 126 85 131 C119 137 132 106 162 113 C191 119 204 93 236 101 C271 109 286 79 318 88 C355 98 368 65 399 74 C430 84 448 53 480 62 C512 71 531 48 560 53"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                      />

                      <circle
                        cx="560"
                        cy="53"
                        r="4.5"
                        fill="currentColor"
                      />
                    </svg>
                  </div>

                  <div className="chart-footer">
                    <span>Tx {transmittedKbps.toLocaleString()} Kbps</span>
                    <span>Throttle {throttledKbps.toLocaleString()} Kbps</span>
                    <span>Queued {queuedKbps.toLocaleString()} Kbps</span>
                  </div>
                </div>
              </div>
            </article>

            <article className="panel">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">
                    INCIDENTS
                  </div>

                  <h2>Requires attention</h2>
                </div>

                <button
                  className="panel-link"
                  type="button"
                  onClick={() => handleNavigation("Incidents")}
                  style={{ background: "none", border: 0, cursor: "pointer" }}
                >
                  View all
                </button>
              </div>

              <div className="incident-list">
                {events === null ? (
                  <IncidentRow
                    severity="medium"
                    title="Loading incidents"
                    detail="Fetching operational events from ShipOps API"
                    time="—"
                  />
                ) : activeEvents.length === 0 ? (
                  <IncidentRow
                    severity="medium"
                    title="No active incidents"
                    detail="No open or acknowledged operational events"
                    time="now"
                  />
                ) : (
                  displayedEvents.map((event) => (
                    <IncidentRow
                      key={event.id}
                      severity={incidentVisualSeverity(event.severity)}
                      title={event.summary}
                      detail={`${getEventAssetIdentifier(event)} · ${event.event_type}`}
                      time={formatEventTime(event.occurred_at)}
                    />
                  ))
                )}
              </div>
            </article>
          </section>

          <section className="secondary-grid">
            <article className="panel">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">
                    TOPOLOGY
                  </div>

                  <h2>Network state</h2>
                </div>

                <button
                  className="panel-link"
                  type="button"
                  onClick={() => handleNavigation("Network Topology")}
                  style={{ background: "none", border: 0, cursor: "pointer" }}
                >
                  Open topology
                  <Icon
                    name="external"
                    size={13}
                  />
                </button>
              </div>

              <TopologyPreview />
            </article>

            <article className="panel">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">
                    ROOT CAUSE
                  </div>

                  <h2>Latest analysis</h2>
                </div>

                <span className="confidence-badge">
                  87% confidence
                </span>
              </div>

              <div className="rca-card">
                <div className="rca-card__icon">
                  <Icon
                    name="shield"
                    size={19}
                  />
                </div>

                <div className="rca-card__content">
                  <span className="rca-card__label">
                    Probable common cause
                  </span>

                  <strong>
                    AP2 upstream connectivity
                  </strong>

                  <p>
                    Topology proximity, shared impact,
                    and correlated telemetry indicate AP2
                    as the most probable source.
                  </p>

                  <div className="rca-card__meta">
                    <span>2 affected assets</span>
                    <span>4 telemetry signals</span>
                    <span>Topology match</span>
                  </div>
                </div>
              </div>

              <div className="telemetry-strip">
                <div>
                  <span>Packet loss</span>
                  <strong>3.4%</strong>
                </div>

                <MiniSparkline />

                <div className="telemetry-strip__trend">
                  <span>↑ 1.2%</span>
                  <small>vs. 15 min ago</small>
                </div>
              </div>
            </article>
          </section>

          <section className="system-strip">
            <div className="system-strip__item">
              <span className="system-strip__icon">
                <Icon
                  name="shield"
                  size={16}
                />
              </span>

              <div>
                <strong>
                  Edge services protected
                </strong>
                <span>
                  Authenticated API · {health ? health.status : "checking"}
                </span>
              </div>
            </div>

            <div className="system-strip__divider" />

            <div className="system-strip__item">
              <span className="system-strip__icon">
                <Icon
                  name="activity"
                  size={16}
                />
              </span>

              <div>
                <strong>
                  Telemetry ingestion
                </strong>
                <span>
                  Real-time · nominal
                </span>
              </div>
            </div>

            <div className="system-strip__divider" />

            <div className="system-strip__item">
              <span className="system-strip__icon">
                <Icon
                  name="network"
                  size={16}
                />
              </span>

              <div>
                <strong>
                  18 infrastructure assets
                </strong>
                <span>
                  17 healthy · 1 degraded
                </span>
              </div>
            </div>
          </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
