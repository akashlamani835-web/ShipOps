from datetime import datetime, timezone
from uuid import uuid4

from app.telemetry.cache import TelemetryCache


class FakeRedis:
    """Small in-memory Redis replacement for unit tests."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def set(self, key: str, value: str) -> bool:
        self.data[key] = value
        return True

    def get(self, key: str):
        return self.data.get(key)

    def delete(self, key: str) -> int:
        return int(self.data.pop(key, None) is not None)


class BrokenRedis:
    """Redis client that always fails."""

    def set(self, key: str, value: str) -> None:
        raise ConnectionError("Redis unavailable")

    def get(self, key: str):
        raise ConnectionError("Redis unavailable")

    def delete(self, key: str) -> int:
        raise ConnectionError("Redis unavailable")


def build_times():
    observed_at = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    received_at = datetime(
        2026,
        9,
        9,
        12,
        0,
        2,
        tzinfo=timezone.utc,
    )

    return observed_at, received_at


def test_set_and_get_latest():
    client = FakeRedis()
    cache = TelemetryCache(client)

    asset_id = uuid4()
    telemetry_id = uuid4()
    observed_at, received_at = build_times()

    stored = cache.set_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
        value=38,
        unit="percent",
        observed_at=observed_at,
        received_at=received_at,
        source="edge_gateway",
        quality="good",
        source_sequence=104,
        telemetry_id=telemetry_id,
    )

    assert stored is True

    result = cache.get_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
    )

    assert result is not None
    assert result["telemetry_id"] == str(telemetry_id)
    assert result["asset_id"] == str(asset_id)
    assert result["metric"] == "packet_loss"
    assert result["value"] == 38
    assert result["unit"] == "percent"
    assert result["source_sequence"] == 104


def test_missing_latest_returns_none():
    cache = TelemetryCache(FakeRedis())

    result = cache.get_latest(
        asset_id=uuid4(),
        metric_code="packet_loss",
    )

    assert result is None


def test_delete_removes_latest_value():
    client = FakeRedis()
    cache = TelemetryCache(client)

    asset_id = uuid4()
    observed_at, received_at = build_times()

    cache.set_latest(
        asset_id=asset_id,
        metric_code="latency",
        value=42,
        unit="milliseconds",
        observed_at=observed_at,
        received_at=received_at,
        source="simulator",
        quality="good",
        source_sequence=1,
        telemetry_id=uuid4(),
    )

    assert cache.get_latest(
        asset_id=asset_id,
        metric_code="latency",
    ) is not None

    assert cache.delete(
        asset_id=asset_id,
        metric_code="latency",
    ) is True

    assert cache.get_latest(
        asset_id=asset_id,
        metric_code="latency",
    ) is None


def test_redis_failure_does_not_raise_on_set():
    cache = TelemetryCache(BrokenRedis())
    observed_at, received_at = build_times()

    result = cache.set_latest(
        asset_id=uuid4(),
        metric_code="packet_loss",
        value=38,
        unit="percent",
        observed_at=observed_at,
        received_at=received_at,
        source="edge_gateway",
        quality="good",
        source_sequence=104,
        telemetry_id=uuid4(),
    )

    assert result is False


def test_redis_failure_does_not_raise_on_get():
    cache = TelemetryCache(BrokenRedis())

    result = cache.get_latest(
        asset_id=uuid4(),
        metric_code="packet_loss",
    )

    assert result is None


def test_redis_failure_does_not_raise_on_delete():
    cache = TelemetryCache(BrokenRedis())

    result = cache.delete(
        asset_id=uuid4(),
        metric_code="packet_loss",
    )

    assert result is False


def test_older_sequence_does_not_overwrite_newer_value():
    client = FakeRedis()
    cache = TelemetryCache(client)

    asset_id = uuid4()
    newer_id = uuid4()
    older_id = uuid4()

    observed_at, received_at = build_times()

    cache.set_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
        value=40,
        unit="percent",
        observed_at=observed_at,
        received_at=received_at,
        source="edge_gateway",
        quality="good",
        source_sequence=105,
        telemetry_id=newer_id,
    )

    cache.set_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
        value=12,
        unit="percent",
        observed_at=observed_at,
        received_at=received_at,
        source="edge_gateway",
        quality="good",
        source_sequence=103,
        telemetry_id=older_id,
    )

    result = cache.get_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
    )

    assert result is not None
    assert result["value"] == 40
    assert result["source_sequence"] == 105
    assert result["telemetry_id"] == str(newer_id)


def test_newer_sequence_replaces_older_value():
    client = FakeRedis()
    cache = TelemetryCache(client)

    asset_id = uuid4()
    older_id = uuid4()
    newer_id = uuid4()

    observed_at, received_at = build_times()

    cache.set_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
        value=12,
        unit="percent",
        observed_at=observed_at,
        received_at=received_at,
        source="edge_gateway",
        quality="good",
        source_sequence=103,
        telemetry_id=older_id,
    )

    cache.set_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
        value=40,
        unit="percent",
        observed_at=observed_at,
        received_at=received_at,
        source="edge_gateway",
        quality="good",
        source_sequence=105,
        telemetry_id=newer_id,
    )

    result = cache.get_latest(
        asset_id=asset_id,
        metric_code="packet_loss",
    )

    assert result is not None
    assert result["value"] == 40
    assert result["source_sequence"] == 105
    assert result["telemetry_id"] == str(newer_id)