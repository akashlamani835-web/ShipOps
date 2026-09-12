import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  getRCAEvent,
  getEvents,
  submitTelemetry,
} from "../api";

describe("ShipOps API service", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("submits telemetry with the expected request", async () => {
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        new Response(JSON.stringify({ accepted: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );

    vi.stubGlobal("fetch", fetchMock);

    const payload = {
      asset_identifier: "SW-07",
      metric: "packet_loss",
      value: 38,
      unit: "%",
      observed_at: "2026-09-12T12:00:00Z",
      source: "frontend-test",
      source_sequence: 1,
      quality: "good",
      idempotency_key: "test-telemetry-1",
    };

    const result = await submitTelemetry(payload);

    expect(result).toEqual({ accepted: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/telemetry",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
  });

  it("builds event and RCA URLs correctly", async () => {
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        new Response(JSON.stringify({}), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );

    vi.stubGlobal("fetch", fetchMock);

    await getEvents(25);
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/events?limit=25",
      expect.anything(),
    );

    await getRCAEvent("event/123");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/rca/events/event%2F123",
      expect.anything(),
    );
  });

  it("throws ApiError with backend detail on failed requests", async () => {
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        new Response(JSON.stringify({ detail: "Authentication required." }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
    );

    vi.stubGlobal("fetch", fetchMock);

    await expect(getEvents()).rejects.toEqual(
      expect.objectContaining({
        name: "ApiError",
        status: 401,
        detail: "Authentication required.",
      }),
    );

    try {
      await getEvents();
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
    }
  });
});