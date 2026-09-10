from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from app.api.routes.connectivity import get_connectivity_service
from app.core.config import get_settings
from app.core.security import require_api_token
from app.db.database import get_db
from app.main import app
from app.models import (
    Asset,
    Base,
    Deck,
    NetworkInterface,
    NetworkLink,
    Organization,
    Vessel,
    Zone,
)
from app.telemetry.models import MetricDefinition


TEST_API_TOKEN = "test-shipops-api-token"


def build_test_database_url() -> URL:
    """Build the PostgreSQL URL for the isolated test database."""

    application_url = make_url(get_settings().database_url)

    return application_url.set(
        database="shipops_test",
    )


@pytest.fixture(scope="session")
def test_engine():
    """Create the isolated PostgreSQL test engine."""

    engine = create_engine(
        build_test_database_url(),
        pool_pre_ping=True,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Provide a transaction-isolated PostgreSQL session."""

    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield session
    finally:
        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()


@pytest.fixture
def seeded_topology(
    db_session: Session,
) -> dict[str, Asset]:
    """Create the deterministic topology used by integration tests."""

    organization = Organization(
        name="Test Fleet",
    )

    vessel = Vessel(
        name="Test Vessel",
        code="TEST-001",
        organization=organization,
    )

    deck = Deck(
        deck_number=7,
        name="Deck 7",
        vessel=vessel,
    )

    zone = Zone(
        code="D07-TEST",
        name="Deck 7 Test Zone",
        deck=deck,
    )

    router = Asset(
        asset_type="router",
        name="Core Router",
        identifier="R1",
        status="online",
        zone=zone,
    )

    switch = Asset(
        asset_type="switch",
        name="Deck 7 Switch",
        identifier="SW-07",
        status="online",
        zone=zone,
    )

    ap1 = Asset(
        asset_type="access_point",
        name="Deck 7 AP 1",
        identifier="AP-07-01",
        status="online",
        zone=zone,
    )

    ap2 = Asset(
        asset_type="access_point",
        name="Deck 7 AP 2",
        identifier="AP-07-02",
        status="online",
        zone=zone,
    )

    pos1 = Asset(
        asset_type="pos_terminal",
        name="Deck 7 POS 1",
        identifier="POS-07-01",
        status="online",
        zone=zone,
    )

    pos2 = Asset(
        asset_type="pos_terminal",
        name="Deck 7 POS 2",
        identifier="POS-07-02",
        status="online",
        zone=zone,
    )

    pos3 = Asset(
        asset_type="pos_terminal",
        name="Deck 7 POS 3",
        identifier="POS-07-03",
        status="online",
        zone=zone,
    )

    pos4 = Asset(
        asset_type="pos_terminal",
        name="Deck 7 POS 4",
        identifier="POS-07-04",
        status="online",
        zone=zone,
    )

    db_session.add_all(
        [
            organization,
            vessel,
            deck,
            zone,
            router,
            switch,
            ap1,
            ap2,
            pos1,
            pos2,
            pos3,
            pos4,
        ]
    )

    db_session.flush()

    router_if = NetworkInterface(
        asset_id=router.id,
        name="Gi0/1",
        interface_type="ethernet",
        speed_mbps=1000,
    )

    switch_if1 = NetworkInterface(
        asset_id=switch.id,
        name="Gi0/1",
        interface_type="ethernet",
        speed_mbps=1000,
    )

    switch_if2 = NetworkInterface(
        asset_id=switch.id,
        name="Gi0/2",
        interface_type="ethernet",
        speed_mbps=1000,
    )

    switch_if3 = NetworkInterface(
        asset_id=switch.id,
        name="Gi0/3",
        interface_type="ethernet",
        speed_mbps=1000,
    )

    ap1_if = NetworkInterface(
        asset_id=ap1.id,
        name="eth0",
        interface_type="ethernet",
        speed_mbps=1000,
    )

    ap2_if = NetworkInterface(
        asset_id=ap2.id,
        name="eth0",
        interface_type="ethernet",
        speed_mbps=1000,
    )

    pos1_if = NetworkInterface(
        asset_id=pos1.id,
        name="eth0",
        interface_type="ethernet",
        speed_mbps=100,
    )

    pos2_if = NetworkInterface(
        asset_id=pos2.id,
        name="eth0",
        interface_type="ethernet",
        speed_mbps=100,
    )

    pos3_if = NetworkInterface(
        asset_id=pos3.id,
        name="eth0",
        interface_type="ethernet",
        speed_mbps=100,
    )

    pos4_if = NetworkInterface(
        asset_id=pos4.id,
        name="eth0",
        interface_type="ethernet",
        speed_mbps=100,
    )

    db_session.add_all(
        [
            router_if,
            switch_if1,
            switch_if2,
            switch_if3,
            ap1_if,
            ap2_if,
            pos1_if,
            pos2_if,
            pos3_if,
            pos4_if,
        ]
    )

    db_session.flush()

    db_session.add_all(
        [
            NetworkLink(
                source_interface_id=router_if.id,
                destination_interface_id=switch_if1.id,
                link_type="ethernet",
                capacity_mbps=1000,
            ),
            NetworkLink(
                source_interface_id=switch_if2.id,
                destination_interface_id=ap1_if.id,
                link_type="ethernet",
                capacity_mbps=1000,
            ),
            NetworkLink(
                source_interface_id=switch_if3.id,
                destination_interface_id=ap2_if.id,
                link_type="ethernet",
                capacity_mbps=1000,
            ),
            NetworkLink(
                source_interface_id=ap1_if.id,
                destination_interface_id=pos1_if.id,
                link_type="ethernet",
                capacity_mbps=100,
            ),
            NetworkLink(
                source_interface_id=ap1_if.id,
                destination_interface_id=pos2_if.id,
                link_type="ethernet",
                capacity_mbps=100,
            ),
            NetworkLink(
                source_interface_id=ap2_if.id,
                destination_interface_id=pos3_if.id,
                link_type="ethernet",
                capacity_mbps=100,
            ),
            NetworkLink(
                source_interface_id=ap2_if.id,
                destination_interface_id=pos4_if.id,
                link_type="ethernet",
                capacity_mbps=100,
            ),
        ]
    )

    db_session.flush()

    return {
        "router": router,
        "switch": switch,
        "ap1": ap1,
        "ap2": ap2,
        "pos1": pos1,
        "pos2": pos2,
        "pos3": pos3,
        "pos4": pos4,
    }


@pytest.fixture
def packet_loss_metric(
    db_session: Session,
) -> MetricDefinition:
    """Create the packet-loss metric used by telemetry tests."""

    metric = MetricDefinition(
        code="packet_loss",
        name="Packet Loss",
        unit="percent",
        minimum_value=0,
        maximum_value=100,
        description="Percentage of packets lost.",
        active=True,
    )

    db_session.add(metric)
    db_session.flush()

    return metric


@pytest.fixture(autouse=True)
def override_authentication():
    """
    Override API authentication for the existing automated test suite.

    Dedicated security tests temporarily remove this override when they
    need to exercise the real authentication dependency.
    """

    app.dependency_overrides[require_api_token] = (
        lambda: TEST_API_TOKEN
    )

    yield

    app.dependency_overrides.pop(
        require_api_token,
        None,
    )


@pytest.fixture
def api_client(
    db_session: Session,
    seeded_topology: dict[str, Asset],
    packet_loss_metric: MetricDefinition,
) -> Generator[TestClient, None, None]:
    """Provide an API client connected to the isolated test session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(
            get_db,
            None,
        )