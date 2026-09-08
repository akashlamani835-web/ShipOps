# ShipOps Product Requirements

**Version:** 0.1  
**Status:** Draft

---

# 1. Problem Statement

Modern vessels depend on distributed IT infrastructure consisting of
network devices, servers, wireless systems, POS terminals, endpoints,
and internal services.

External connectivity may be constrained by bandwidth, latency,
availability, and cost.

A centralized IT management model can become less effective when the
connection between a vessel and external infrastructure is degraded.

ShipOps addresses this by providing an edge-first IT operations
platform capable of operating locally while intelligently managing
limited connectivity.

---

# 2. Product Goals

ShipOps should:

- Provide visibility into vessel IT infrastructure.
- Represent infrastructure dependencies.
- Collect infrastructure telemetry.
- Detect infrastructure failures.
- Correlate related failures.
- Identify probable root causes.
- Manage IT incidents.
- Monitor external connectivity.
- Prioritize important traffic.
- Reduce unnecessary bandwidth consumption.
- Continue essential operations during connectivity loss.
- Synchronize local data after connectivity recovery.
- Provide secure operational access.
- Provide evidence-backed AI-assisted troubleshooting.

---

# 3. Functional Requirements

## FR-001 — Vessel Model

The system shall represent:

- Vessel
- Deck
- Zone
- Network segment
- Infrastructure asset

---

## FR-002 — Asset Management

The system shall support assets including:

- Routers
- Switches
- Access points
- Servers
- POS terminals
- Workstations
- Printers
- Network services

Each asset should have:

- Unique identifier
- Type
- Location
- Status
- Metadata
- Ownership information
- Creation/update timestamps

---

## FR-003 — Network Topology

The system shall represent dependencies between infrastructure
components.

Example:

Router → Switch → Access Point → POS terminals

Topology information shall be queryable by the backend.

---

## FR-004 — Telemetry

The system shall support infrastructure measurements including:

- CPU utilization
- Memory utilization
- Network throughput
- Latency
- Packet loss
- Availability
- Interface errors
- Service health

---

## FR-005 — Event Processing

The platform shall ingest operational events such as:

- Device offline
- Device recovered
- High CPU
- High memory
- Packet loss
- Latency increase
- Interface errors
- Service failure
- Connectivity degradation

---

## FR-006 — Incident Management

Authorized users shall be able to:

- Create incidents
- View incidents
- Assign incidents
- Change status
- Add investigation notes
- Resolve incidents
- Review incident history

---

## FR-007 — Event Correlation

The system should identify relationships between multiple events.

Example:

Twenty POS devices become unavailable.

The system should determine whether they share a common network dependency.

---

## FR-008 — Root-Cause Analysis

The system should calculate probable causes using:

- Network topology
- Telemetry
- Events
- Device dependencies
- Historical information
- Recent configuration changes

The result should include supporting evidence.

---

## FR-009 — Connectivity Monitoring

The platform shall track:

- Connection state
- Available bandwidth
- Current utilization
- Latency
- Packet loss
- Data consumption

---

## FR-010 — Traffic Classification

Traffic shall be assigned operational priority.

Initial categories:

- Critical
- High
- Normal
- Low
- Bulk

---

## FR-011 — Adaptive Bandwidth Management

The system should support:

- Priority rules
- Traffic throttling
- Queuing
- Scheduled transfers
- Bandwidth budgets
- Consumption tracking

---

## FR-012 — Edge Operation

Essential platform functionality shall continue operating locally
when external connectivity is unavailable.

---

## FR-013 — Synchronization

The edge system shall synchronize locally generated information
with cloud services after connectivity recovery.

Synchronization must account for:

- Retry
- Duplicate events
- Temporary failures
- Ordering
- Conflict handling

---

## FR-014 — Authentication

The system shall authenticate users before protected operations.

---

## FR-015 — Authorization

The system shall implement role-based authorization.

Example roles:

- Administrator
- IT Officer
- Technician
- Read-only Operator

---

## FR-016 — Audit Logging

Security-sensitive and operationally significant actions shall
produce auditable records.

---

## FR-017 — AI-Assisted Diagnosis

Authorized users shall be able to request natural-language analysis
of operational incidents.

The AI system should use structured ShipOps data including:

- Topology
- Telemetry
- Logs
- Incidents
- Device history
- Connectivity state

Responses should provide:

- Probable cause
- Evidence
- Affected systems
- Recommended action
- Uncertainty/confidence

---

# 4. Non-Functional Requirements

## NFR-001 — Reliability

Core edge functionality should remain available during temporary
external connectivity loss.

## NFR-002 — Security

Secrets must not be committed to source control.

Protected resources must require authorization.

## NFR-003 — Observability

Services should provide:

- Structured logs
- Metrics
- Health checks
- Error information

## NFR-004 — Testability

Important business logic shall have automated tests.

## NFR-005 — Maintainability

Components should have clear responsibilities and interfaces.

## NFR-006 — Performance

The system should support a realistic simulated vessel workload
without significant degradation.

## NFR-007 — Recoverability

Failure scenarios must have defined recovery behavior.

---

# 5. Demonstration Scenario

The primary demonstration should eventually perform the following:

1. Start a simulated vessel.
2. Display its infrastructure.
3. Display network topology.
4. Generate normal telemetry.
5. Inject a network failure.
6. Observe resulting device failures.
7. Correlate affected devices.
8. Identify the probable root cause.
9. Create an incident.
10. Apply connectivity-management policies.
11. Disconnect external connectivity.
12. Continue local operations.
13. Restore connectivity.
14. Synchronize queued events.
15. Ask the AI Operations Engineer to explain the incident.

---

# 6. Scope Boundaries

The initial version will focus on IT infrastructure and connectivity.

The following are outside the initial scope:

- Navigation control
- Propulsion control
- Engine control
- Safety-critical maritime control systems
- Direct control of real vessel hardware
- Real-world satellite provider integration

These may only be considered in future versions after appropriate
safety, regulatory, and technical analysis.