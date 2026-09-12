# ShipOps

> Edge-based IT operations and adaptive connectivity platform for
> bandwidth-constrained maritime environments.

## Overview

ShipOps is a systems-oriented CSE project that models ship-side IT
operations in an environment where local infrastructure must continue
operating despite intermittent, degraded, or unavailable external
connectivity.

The platform combines:

- Network topology and dependency modeling
- Infrastructure telemetry
- Sustained threshold detection
- Operational event and incident management
- Evidence-based root-cause analysis
- Adaptive connectivity and bandwidth policy
- Local queueing and recovery behavior
- PostgreSQL persistence
- Redis-backed telemetry caching
- Protected APIs
- Operator-focused web console
- Automated backend testing and integration validation

The architecture follows an edge-first principle:

```text
                         External / Shore Systems
                                  |
                           Intermittent Link
                                  |
                         +--------+--------+
                         |   ShipOps Edge  |
                         |     Services    |
                         +--------+--------+
                                  |
                  +---------------+---------------+
                  |                               |
            Ship Network                    Local Operations
                  |                               |
        +---------+---------+              +------+------+
        |         |         |              |             |
      Router    Switch      APs        Telemetry       Events
        |         |         |              |             |
     Endpoints / Services             Evidence / RCA
                  |
            Operator Console