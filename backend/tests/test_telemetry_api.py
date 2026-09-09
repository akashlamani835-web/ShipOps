from datetime import datetime, timedelta, timezone


def build_payload(
    *,
    value: float = 38,
    source_sequence: int = 1,
    idempotency_key: str = "api-sample-001",
) -> dict:
    observed_at = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    received_at = observed_at + timedelta(seconds=2)

    return {
        "asset_identifier": "SW-07",
        "metric": "packet_loss",
        "value": value,
        "unit": "percent",
        "observed_at": observed_at.isoformat(),
        "received_at": received_at.isoformat(),
        "source": "edge_gateway",
        "source_sequence": source_sequence,
        "quality": "good",
        "idempotency_key": idempotency_key,
    }


def test_ingest_telemetry_returns_201(
    api_client,
    db_session,
    packet_loss_metric,
):
    response = api_client.post(
        "/api/v1/telemetry",
        json=build_payload(
            idempotency_key="api-create-001",
            source_sequence=1,
        ),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "accepted"
    assert data["asset_identifier"] == "SW-07"
    assert data["metric"] == "packet_loss"
    assert data["idempotent_replay"] is False
    assert data["telemetry_id"] is not None


def test_repeated_idempotent_request_returns_200(
    api_client,
    db_session,
    packet_loss_metric,
):
    payload = build_payload(
        value=38,
        source_sequence=10,
        idempotency_key="api-replay-001",
    )

    first_response = api_client.post(
        "/api/v1/telemetry",
        json=payload,
    )

    second_response = api_client.post(
        "/api/v1/telemetry",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert first_data["telemetry_id"] == second_data["telemetry_id"]
    assert second_data["idempotent_replay"] is True


def test_invalid_metric_returns_422(
    api_client,
    packet_loss_metric,
):
    payload = build_payload(
        idempotency_key="api-invalid-metric-001",
        source_sequence=20,
    )

    payload["metric"] = "does_not_exist"

    response = api_client.post(
        "/api/v1/telemetry",
        json=payload,
    )

    assert response.status_code == 422
    assert "does_not_exist" in response.json()["detail"]


def test_unknown_asset_returns_422(
    api_client,
    packet_loss_metric,
):
    payload = build_payload(
        idempotency_key="api-unknown-asset-001",
        source_sequence=21,
    )

    payload["asset_identifier"] = "DOES-NOT-EXIST"

    response = api_client.post(
        "/api/v1/telemetry",
        json=payload,
    )

    assert response.status_code == 422
    assert "DOES-NOT-EXIST" in response.json()["detail"]


def test_invalid_value_returns_422(
    api_client,
    packet_loss_metric,
):
    payload = build_payload(
        value=101,
        idempotency_key="api-invalid-value-001",
        source_sequence=22,
    )

    response = api_client.post(
        "/api/v1/telemetry",
        json=payload,
    )

    assert response.status_code == 422
    assert "maximum" in response.json()["detail"]