"""
Tests for:
  GET /organizations              - список организаций с фильтрами
  GET /organizations/{id}         - одна организация

Примечание по радиус-фильтру:
  Эндпоинт сравнивает acos(...) * 6371 <= radius_km.
  Угловое расстояние умножается на радиус Земли (6371 км).
  При запросе из точки A до той же точки acos(1)*6371 = 0, любой
  положительный radius_km подходит.

Ответ:
  GET /organizations возвращает Page:
  {"items": [...], "count": N, "limit": N, "offset": N}
"""
import pytest

from tests.conftest import make_org

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /organizations - без фильтров
# ---------------------------------------------------------------------------

async def test_empty_db_returns_empty_list(client):
    resp = await client.get("/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["items"] == []
    assert page["count"] == 0


async def test_returns_all_organizations_without_filter(client, db_session):
    await make_org(db_session, "Org A", lat=55.0, lon=37.0)
    await make_org(db_session, "Org B", lat=56.0, lon=38.0)

    resp = await client.get("/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert len(page["items"]) == 2
    assert page["count"] == 2


async def test_response_schema_contains_expected_fields(client, db_session):
    await make_org(
        db_session,
        "Schema Org",
        lat=55.75,
        lon=37.62,
        address="ul. Lenina 1",
        phones=["79001112233"],
    )

    resp = await client.get("/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert "items" in page
    assert "count" in page
    assert "limit" in page
    assert "offset" in page
    org = page["items"][0]

    assert org["name"] == "Schema Org"
    assert org["building"]["address"] == "ul. Lenina 1"
    assert org["building"]["latitude"] == 55.75
    assert org["building"]["longitude"] == 37.62
    assert org["phones"][0]["phone"] == "79001112233"
    assert org["activities"] == []


# ---------------------------------------------------------------------------
# GET /organizations - фильтр по имени
# ---------------------------------------------------------------------------

async def test_name_filter_returns_matching_org(client, db_session):
    await make_org(db_session, "Alpha Corp", lat=55.0, lon=37.0)
    await make_org(db_session, "Beta LLC", lat=56.0, lon=38.0)

    resp = await client.get("/organizations", params={"name": "Alpha"})
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["name"] == "Alpha Corp"


async def test_name_filter_is_case_insensitive(client, db_session):
    await make_org(db_session, "Alpha Corp", lat=55.0, lon=37.0)

    resp = await client.get("/organizations", params={"name": "alpha"})
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1


async def test_name_filter_partial_match(client, db_session):
    await make_org(db_session, "Alpha Corp", lat=55.0, lon=37.0)
    await make_org(db_session, "Beta LLC", lat=56.0, lon=38.0)

    resp = await client.get("/organizations", params={"name": "Corp"})
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["name"] == "Alpha Corp"


async def test_name_filter_no_match_returns_empty(client, db_session):
    await make_org(db_session, "Alpha Corp", lat=55.0, lon=37.0)

    resp = await client.get(
        "/organizations", params={"name": "Nonexistent"}
    )
    assert resp.status_code == 200
    page = resp.json()
    assert page["items"] == []
    assert page["count"] == 0


# ---------------------------------------------------------------------------
# GET /organizations/{id}
# ---------------------------------------------------------------------------

async def test_get_organization_by_id_returns_correct_org(
    client, db_session
):
    org = await make_org(
        db_session, "Target Org", lat=55.75, lon=37.62, phones=["71234567890"]
    )
    resp = await client.get(f"/organizations/{org.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == org.id
    assert data["name"] == "Target Org"
    assert data["phones"][0]["phone"] == "71234567890"


async def test_get_organization_by_id_not_found(client):
    resp = await client.get("/organizations/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Organization not found"


async def test_get_organization_by_id_schema(client, db_session):
    org = await make_org(
        db_session, "Schema Check", lat=55.0, lon=37.0, address="Test Ave 10"
    )
    resp = await client.get(f"/organizations/{org.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "name" in data
    assert "building" in data
    assert "phones" in data
    assert "activities" in data
    assert data["building"]["address"] == "Test Ave 10"


# ---------------------------------------------------------------------------
# GET /organizations - bbox фильтр
# ---------------------------------------------------------------------------

async def test_bbox_org_inside_is_returned(client, db_session):
    await make_org(db_session, "Inside Org", lat=55.75, lon=37.62)

    resp = await client.get("/organizations", params={
        "lat_min": 55.0, "lat_max": 56.0,
        "lon_min": 37.0, "lon_max": 38.0,
    })
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["name"] == "Inside Org"


async def test_bbox_org_outside_is_not_returned(client, db_session):
    await make_org(db_session, "Outside Org", lat=60.0, lon=30.0)

    resp = await client.get("/organizations", params={
        "lat_min": 55.0, "lat_max": 56.0,
        "lon_min": 37.0, "lon_max": 38.0,
    })
    assert resp.status_code == 200
    page = resp.json()
    assert page["items"] == []
    assert page["count"] == 0


async def test_bbox_org_on_boundary_is_returned(client, db_session):
    await make_org(db_session, "Boundary Org", lat=55.0, lon=37.0)

    resp = await client.get("/organizations", params={
        "lat_min": 55.0, "lat_max": 56.0,
        "lon_min": 37.0, "lon_max": 38.0,
    })
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1


async def test_bbox_returns_only_orgs_inside(client, db_session):
    await make_org(db_session, "Inside 1", lat=55.5, lon=37.5)
    await make_org(db_session, "Inside 2", lat=55.8, lon=37.9)
    await make_org(db_session, "Outside", lat=60.0, lon=30.0)

    resp = await client.get("/organizations", params={
        "lat_min": 55.0, "lat_max": 56.0,
        "lon_min": 37.0, "lon_max": 38.0,
    })
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 2
    names = {o["name"] for o in page["items"]}
    assert names == {"Inside 1", "Inside 2"}


async def test_bbox_partial_params_disables_geo_filter(client, db_session):
    """Если переданы не все 4 параметра к прямоугольной области, гео-фильтр не применяется"""
    await make_org(db_session, "Any Org", lat=55.75, lon=37.62)

    resp = await client.get(
        "/organizations", params={"lat_min": 55.0, "lat_max": 56.0}
    )
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1


# ---------------------------------------------------------------------------
# GET /organizations - радиус-фильтр
# ---------------------------------------------------------------------------

async def test_radius_org_at_same_point_is_returned(client, db_session):
    await make_org(db_session, "Same Point Org", lat=55.75, lon=37.62)

    resp = await client.get("/organizations", params={
        "lat": 55.75, "lon": 37.62, "radius_km": 1.0,
    })
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["name"] == "Same Point Org"


async def test_radius_org_far_away_is_not_returned(client, db_session):
    await make_org(db_session, "Far Org", lat=43.1, lon=131.9)

    resp = await client.get("/organizations", params={
        "lat": 55.75, "lon": 37.62, "radius_km": 100,
    })
    assert resp.status_code == 200
    page = resp.json()
    assert page["items"] == []
    assert page["count"] == 0


async def test_radius_returns_only_nearby_org(client, db_session):
    await make_org(db_session, "Nearby Org", lat=55.75, lon=37.62)
    await make_org(db_session, "Far Org", lat=43.1, lon=131.9)

    resp = await client.get("/organizations", params={
        "lat": 55.75, "lon": 37.62, "radius_km": 100,
    })
    assert resp.status_code == 200
    page = resp.json()
    names = [o["name"] for o in page["items"]]
    assert "Nearby Org" in names
    assert "Far Org" not in names


async def test_radius_partial_params_disables_geo_filter(client, db_session):
    """Если не передан radius_km, гео-фильтр по радиусу не применяется"""
    await make_org(db_session, "Any Org", lat=55.75, lon=37.62)

    resp = await client.get(
        "/organizations", params={"lat": 55.75, "lon": 37.62}
    )
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
