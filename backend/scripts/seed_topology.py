from sqlalchemy import select

from app.db.database import SessionLocal
from app.models import (
    Asset,
    Deck,
    NetworkInterface,
    NetworkLink,
    Organization,
    Vessel,
    Zone,
)


ORGANIZATION_NAME = "ShipOps Demo Fleet"
VESSEL_CODE = "SHIPOPS-001"
VESSEL_NAME = "MV ShipOps One"
DECK_NUMBER = 7
DECK_NAME = "Deck 7"
ZONE_CODE = "D07-IT"
ZONE_NAME = "Deck 7 IT Zone"


def get_or_create_organization(db):
    organization = db.scalar(
        select(Organization).where(
            Organization.name == ORGANIZATION_NAME
        )
    )

    if organization is None:
        organization = Organization(
            name=ORGANIZATION_NAME,
        )
        db.add(organization)
        db.flush()

    return organization


def get_or_create_vessel(db, organization):
    vessel = db.scalar(
        select(Vessel).where(
            Vessel.organization_id == organization.id,
            Vessel.code == VESSEL_CODE,
        )
    )

    if vessel is None:
        vessel = Vessel(
            organization_id=organization.id,
            name=VESSEL_NAME,
            code=VESSEL_CODE,
        )
        db.add(vessel)
        db.flush()

    return vessel


def get_or_create_deck(db, vessel):
    deck = db.scalar(
        select(Deck).where(
            Deck.vessel_id == vessel.id,
            Deck.deck_number == DECK_NUMBER,
        )
    )

    if deck is None:
        deck = Deck(
            vessel_id=vessel.id,
            deck_number=DECK_NUMBER,
            name=DECK_NAME,
        )
        db.add(deck)
        db.flush()

    return deck


def get_or_create_zone(db, deck):
    zone = db.scalar(
        select(Zone).where(
            Zone.deck_id == deck.id,
            Zone.code == ZONE_CODE,
        )
    )

    if zone is None:
        zone = Zone(
            deck_id=deck.id,
            code=ZONE_CODE,
            name=ZONE_NAME,
        )
        db.add(zone)
        db.flush()

    return zone


def get_or_create_asset(
    db,
    zone,
    *,
    asset_type: str,
    name: str,
    identifier: str,
):
    asset = db.scalar(
        select(Asset).where(
            Asset.identifier == identifier,
        )
    )

    if asset is None:
        asset = Asset(
            zone_id=zone.id,
            asset_type=asset_type,
            name=name,
            identifier=identifier,
            status="online",
        )
        db.add(asset)
        db.flush()
    else:
        asset.zone_id = zone.id
        asset.asset_type = asset_type
        asset.name = name
        asset.status = "online"
        db.flush()

    return asset


def get_or_create_interface(
    db,
    asset,
    *,
    name: str,
    interface_type: str,
    speed_mbps: int,
):
    interface = db.scalar(
        select(NetworkInterface).where(
            NetworkInterface.asset_id == asset.id,
            NetworkInterface.name == name,
        )
    )

    if interface is None:
        interface = NetworkInterface(
            asset_id=asset.id,
            name=name,
            interface_type=interface_type,
            speed_mbps=speed_mbps,
            administrative_up=True,
            operational_up=True,
        )
        db.add(interface)
        db.flush()
    else:
        interface.interface_type = interface_type
        interface.speed_mbps = speed_mbps
        interface.administrative_up = True
        interface.operational_up = True
        db.flush()

    return interface


def get_or_create_link(
    db,
    source_interface,
    destination_interface,
    *,
    link_type: str,
    capacity_mbps: int,
):
    link = db.scalar(
        select(NetworkLink).where(
            NetworkLink.source_interface_id == source_interface.id,
            NetworkLink.destination_interface_id == destination_interface.id,
        )
    )

    if link is None:
        link = NetworkLink(
            source_interface_id=source_interface.id,
            destination_interface_id=destination_interface.id,
            link_type=link_type,
            capacity_mbps=capacity_mbps,
            operational_up=True,
        )
        db.add(link)
        db.flush()
    else:
        link.link_type = link_type
        link.capacity_mbps = capacity_mbps
        link.operational_up = True
        db.flush()

    return link


def seed() -> None:
    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # Organization
        # ---------------------------------------------------------
        organization = get_or_create_organization(db)

        # ---------------------------------------------------------
        # Vessel
        # ---------------------------------------------------------
        vessel = get_or_create_vessel(
            db,
            organization,
        )

        # ---------------------------------------------------------
        # Deck
        # ---------------------------------------------------------
        deck = get_or_create_deck(
            db,
            vessel,
        )

        # ---------------------------------------------------------
        # Zone
        # ---------------------------------------------------------
        zone = get_or_create_zone(
            db,
            deck,
        )

        # ---------------------------------------------------------
        # Assets
        # ---------------------------------------------------------
        router = get_or_create_asset(
            db,
            zone,
            asset_type="router",
            name="Core Router",
            identifier="R1",
        )

        switch = get_or_create_asset(
            db,
            zone,
            asset_type="switch",
            name="Deck 7 Switch",
            identifier="SW-07",
        )

        ap1 = get_or_create_asset(
            db,
            zone,
            asset_type="access_point",
            name="Deck 7 AP 1",
            identifier="AP-07-01",
        )

        ap2 = get_or_create_asset(
            db,
            zone,
            asset_type="access_point",
            name="Deck 7 AP 2",
            identifier="AP-07-02",
        )

        pos1 = get_or_create_asset(
            db,
            zone,
            asset_type="pos_terminal",
            name="Deck 7 POS 1",
            identifier="POS-07-01",
        )

        pos2 = get_or_create_asset(
            db,
            zone,
            asset_type="pos_terminal",
            name="Deck 7 POS 2",
            identifier="POS-07-02",
        )

        pos3 = get_or_create_asset(
            db,
            zone,
            asset_type="pos_terminal",
            name="Deck 7 POS 3",
            identifier="POS-07-03",
        )

        pos4 = get_or_create_asset(
            db,
            zone,
            asset_type="pos_terminal",
            name="Deck 7 POS 4",
            identifier="POS-07-04",
        )

        # ---------------------------------------------------------
        # Network interfaces
        # ---------------------------------------------------------
        router_if = get_or_create_interface(
            db,
            router,
            name="Gi0/1",
            interface_type="ethernet",
            speed_mbps=1000,
        )

        switch_if1 = get_or_create_interface(
            db,
            switch,
            name="Gi0/1",
            interface_type="ethernet",
            speed_mbps=1000,
        )

        switch_if2 = get_or_create_interface(
            db,
            switch,
            name="Gi0/2",
            interface_type="ethernet",
            speed_mbps=1000,
        )

        switch_if3 = get_or_create_interface(
            db,
            switch,
            name="Gi0/3",
            interface_type="ethernet",
            speed_mbps=1000,
        )

        ap1_if = get_or_create_interface(
            db,
            ap1,
            name="eth0",
            interface_type="ethernet",
            speed_mbps=1000,
        )

        ap2_if = get_or_create_interface(
            db,
            ap2,
            name="eth0",
            interface_type="ethernet",
            speed_mbps=1000,
        )

        pos1_if = get_or_create_interface(
            db,
            pos1,
            name="eth0",
            interface_type="ethernet",
            speed_mbps=100,
        )

        pos2_if = get_or_create_interface(
            db,
            pos2,
            name="eth0",
            interface_type="ethernet",
            speed_mbps=100,
        )

        pos3_if = get_or_create_interface(
            db,
            pos3,
            name="eth0",
            interface_type="ethernet",
            speed_mbps=100,
        )

        pos4_if = get_or_create_interface(
            db,
            pos4,
            name="eth0",
            interface_type="ethernet",
            speed_mbps=100,
        )

        # ---------------------------------------------------------
        # Network links
        #
        # Current topology:
        #
        # R1
        #  |
        # SW-07
        #  | \
        # AP1 AP2
        # /\  /\
        # P1 P2 P3 P4
        #
        # We currently represent these as directed topology edges.
        # Physical-link semantics will be hardened in the next step.
        # ---------------------------------------------------------

        get_or_create_link(
            db,
            router_if,
            switch_if1,
            link_type="ethernet",
            capacity_mbps=1000,
        )

        get_or_create_link(
            db,
            switch_if2,
            ap1_if,
            link_type="ethernet",
            capacity_mbps=1000,
        )

        get_or_create_link(
            db,
            switch_if3,
            ap2_if,
            link_type="ethernet",
            capacity_mbps=1000,
        )

        get_or_create_link(
            db,
            ap1_if,
            pos1_if,
            link_type="ethernet",
            capacity_mbps=100,
        )

        get_or_create_link(
            db,
            ap1_if,
            pos2_if,
            link_type="ethernet",
            capacity_mbps=100,
        )

        get_or_create_link(
            db,
            ap2_if,
            pos3_if,
            link_type="ethernet",
            capacity_mbps=100,
        )

        get_or_create_link(
            db,
            ap2_if,
            pos4_if,
            link_type="ethernet",
            capacity_mbps=100,
        )

        db.commit()

        print("Topology seed completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()