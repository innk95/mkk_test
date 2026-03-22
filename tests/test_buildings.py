"""
Тесты:
  GET /buildings                             - список зданий
  GET /buildings/{building_id}/organizations - организации в здании

Формат ответа":
  GET /buildings и GET /buildings/{id}/organizations возвращают Page:
  {"items": [...], "count": N, "limit": N, "offset": N}
"""
import pytest

from tests.conftest import make_building, make_org

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /buildings
# ---------------------------------------------------------------------------

async def test_list_buildings_empty(client):
    resp = await client.get("/buildings")
    assert resp.status_code == 200
    page = resp.json()
    assert page["items"] == []
    assert page["count"] == 0


async def test_list_buildings_returns_all(client, db_session):
    await make_building(
        db_session, lat=55.75, lon=37.62, address="ul. Lenina 1"
    )
    await make_building(
        db_session, lat=59.93, lon=30.32, address="Nevskiy pr. 1"
    )
    await db_session.commit()

    resp = await client.get("/buildings")
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 2
    assert len(page["items"]) == 2
    addresses = {b["address"] for b in page["items"]}
    assert addresses == {"ul. Lenina 1", "Nevskiy pr. 1"}


async def test_list_buildings_response_schema(client, db_session):
    await make_building(db_session, lat=55.75, lon=37.62, address="Test St 42")
    await db_session.commit()

    resp = await client.get("/buildings")
    assert resp.status_code == 200
    page = resp.json()
    assert "items" in page
    assert "count" in page
    assert "limit" in page
    assert "offset" in page
    building = page["items"][0]
    assert "id" in building
    assert building["address"] == "Test St 42"
    assert building["latitude"] == 55.75
    assert building["longitude"] == 37.62


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/organizations
# ---------------------------------------------------------------------------

async def test_organizations_by_building_returns_correct_orgs(
    client, db_session
):
    from app.models.organization import Organization

    b1 = await make_building(
        db_session, lat=55.75, lon=37.62, address="Building 1"
    )
    b2 = await make_building(
        db_session, lat=59.93, lon=30.32, address="Building 2"
    )
    await db_session.commit()

    org1 = Organization(name="Org in B1", building_id=b1.id)
    org2 = Organization(name="Org in B2", building_id=b2.id)
    db_session.add_all([org1, org2])
    await db_session.commit()

    resp = await client.get(f"/buildings/{b1.id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["name"] == "Org in B1"


async def test_organizations_by_building_empty(client, db_session):
    b = await make_building(db_session, lat=55.75, lon=37.62)
    await db_session.commit()

    resp = await client.get(f"/buildings/{b.id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["items"] == []
    assert page["count"] == 0


async def test_organizations_by_building_not_found(client):
    resp = await client.get("/buildings/99999/organizations")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Building not found"


async def test_organizations_by_building_multiple_orgs(client, db_session):
    from app.models.organization import Organization

    b = await make_building(db_session, lat=55.75, lon=37.62)
    await db_session.commit()

    db_session.add_all([
        Organization(name="Org 1", building_id=b.id),
        Organization(name="Org 2", building_id=b.id),
        Organization(name="Org 3", building_id=b.id),
    ])
    await db_session.commit()

    resp = await client.get(f"/buildings/{b.id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 3
    assert len(page["items"]) == 3


async def test_organizations_by_building_response_schema(client, db_session):
    org = await make_org(
        db_session,
        "Schema Org",
        lat=55.75,
        lon=37.62,
        address="Schema St 1",
        phones=["79990001122"],
    )
    resp = await client.get(f"/buildings/{org.building_id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
    item = page["items"][0]
    assert item["name"] == "Schema Org"
    assert "building" in item
    assert "phones" in item
    assert "activities" in item
    assert item["phones"][0]["phone"] == "79990001122"
