from sqlalchemy.orm import Session

from app.topology.repository import TopologyRepository
from app.topology.service import TopologyService


def test_seeded_sw07_impact(
    db_session: Session,
    seeded_topology,
):
    """Verify impact analysis against isolated PostgreSQL."""
    repository = TopologyRepository(db_session)

    switch = repository.get_asset_by_identifier("SW-07")

    assert switch is not None

    service = TopologyService.from_database(db_session)

    affected_ids = service.impacted_assets(
        str(switch.id),
    )

    identifiers = repository.get_asset_identifiers(
        affected_ids,
    )

    assert set(identifiers.values()) == {
        "R1",
        "AP-07-01",
        "AP-07-02",
        "POS-07-01",
        "POS-07-02",
        "POS-07-03",
        "POS-07-04",
    }

    assert "SW-07" not in identifiers.values()