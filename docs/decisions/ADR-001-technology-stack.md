# ADR-001: Technology Stack

**Status:** Accepted  
**Date:** 2026-09-09

---

## Context

ShipOps requires a technology stack capable of supporting:

- A web-based operator interface
- Backend APIs
- Relational data
- Real-time operational information
- Network and infrastructure simulation
- Edge computing
- Distributed synchronization
- Automated testing
- Containerized development
- AI-assisted operations

The stack should also be suitable for demonstrating practical
computer-science and software-engineering skills.

---

## Decision

ShipOps will initially use the following technologies.

| Layer | Technology |
|---|---|
| Web frontend | Next.js + TypeScript |
| Backend API | Python + FastAPI |
| Primary database | PostgreSQL |
| Cache / transient coordination | Redis |
| Containerization | Docker |
| Local orchestration | Docker Compose |
| API style | REST |
| Real-time communication | WebSocket |
| Backend testing | Pytest |
| Frontend testing | TypeScript-compatible testing framework |
| Observability | OpenTelemetry-compatible design |
| AI | Provider-agnostic service abstraction |

---

## Rationale

### Next.js + TypeScript

The web application requires a modern component-based frontend with
strong typing and support for interactive operational dashboards.

TypeScript provides compile-time type checking and helps maintain
contracts between UI components and API data.

### FastAPI

The backend requires:

- High development velocity
- Strong Python ecosystem support
- Typed request/response models
- Automatic API documentation
- Good support for asynchronous operations

Python is also useful for telemetry processing, simulation,
diagnostic algorithms, and AI integration.

### PostgreSQL

ShipOps contains strongly relational data such as:

- Assets
- Users
- Incidents
- Network relationships
- Telemetry metadata
- Policies
- Audit events
- Synchronization state

PostgreSQL provides transactions, constraints, indexing, and
mature relational capabilities.

### Redis

Redis will be used only where transient state, caching, or
coordination requires it.

It will not replace PostgreSQL as the system of record.

### Docker

Docker provides reproducible development environments and allows
ShipOps components to run consistently across machines.

### Docker Compose

The initial system is not expected to require a large-scale
orchestration platform.

Docker Compose provides an appropriate local environment for
running multiple cooperating services.

### REST

REST provides a simple and explicit interface for the initial
service boundaries.

Real-time requirements can use WebSockets where appropriate.

### Provider-Agnostic AI

The application should not be tightly coupled to a single AI
provider.

The AI layer will therefore be accessed through an internal
service abstraction.

This allows models/providers to be changed without redesigning
the core platform.

---

## Alternatives Considered

### Node.js Backend

Node.js could provide a unified TypeScript stack.

It was not selected for the initial backend because Python provides
stronger alignment with the project's telemetry processing,
simulation, diagnostic, and AI workloads.

### MongoDB

MongoDB could provide flexible document storage.

It was not selected as the primary database because much of the
ShipOps domain has strong relational relationships and transactional
requirements.

### Kubernetes

Kubernetes could eventually be useful for larger deployments.

It is intentionally not part of the initial local development
architecture because it would introduce operational complexity
without providing enough benefit at this stage.

### Direct AI-First Architecture

An AI-first architecture was rejected.

Deterministic system components must establish infrastructure state,
events, dependencies, and evidence before AI is asked to interpret
them.

---

## Consequences

### Positive

- Strong separation between frontend and backend
- Good support for networking and systems-oriented workloads
- Strong relational data model
- Reproducible local development
- Clear service boundaries
- AI provider flexibility
- Good testing and observability opportunities

### Negative

- Multiple languages must be maintained
- Multiple services increase development complexity
- Docker introduces an additional development layer
- Real-time functionality requires additional infrastructure

These costs are accepted because the project is intentionally
designed as a systems-oriented engineering platform rather than a
simple web application.

---

## Future Re-evaluation

This decision may be revisited if:

- Production scale requires additional orchestration
- Edge deployments require a different runtime model
- Telemetry volume exceeds the capabilities of the current storage
  architecture
- A different communication model becomes necessary
- AI workloads require specialized infrastructure