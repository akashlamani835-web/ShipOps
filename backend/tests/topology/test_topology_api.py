from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_topology_impact_for_sw07():
    response = client.get(
        "/api/v1/topology/assets/SW-07/impact",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["root_asset"] == "SW-07"

    assert data["affected_assets"] == [
        "AP-07-01",
        "AP-07-02",
        "POS-07-01",
        "POS-07-02",
        "POS-07-03",
        "POS-07-04",
        "R1",
    ]

    assert data["affected_count"] == 7


def test_topology_impact_for_pos_terminal():
    response = client.get(
        "/api/v1/topology/assets/POS-07-01/impact",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["root_asset"] == "POS-07-01"
    assert "POS-07-01" not in data["affected_assets"]


def test_unknown_asset_returns_404():
    response = client.get(
        "/api/v1/topology/assets/DOES-NOT-EXIST/impact",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Asset 'DOES-NOT-EXIST' not found."
    )