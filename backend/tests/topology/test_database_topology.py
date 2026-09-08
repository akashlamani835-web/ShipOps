from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.topology.repository import TopologyRepository
from app.topology.service import TopologyService


def test_seeded_sw07_impact():
    """Verify impact analysis against the real PostgreSQL topology."""
    db: Session = SessionLocal()

    try:
        repository = TopologyRepository(db)
        switch = repository.get_asset_by_identifier("SW-07")

        assert switch is not None

        service = TopologyService.from_database(db)

        affected_ids = service.impacted_assets(str(switch.id))
        identifiers = repository.get_asset_identifiers(affected_ids)

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

    finally:
        db.close()