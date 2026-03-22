"""
Tests for:
  GET /activities/tree
      - дерево активностей
  GET /activities/{id}/organizations
      - организации в поддереве активности (рекурсивно через ltree)
  ORM-уровень: создание активностей и связи parent/children
"""
import pytest
from sqlalchemy import select

from app.models.activity import Activity
from tests.conftest import make_activity, make_activity_tree, make_org

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /activities/tree
# ---------------------------------------------------------------------------

async def test_tree_empty_db_returns_empty_list(client):
    """Пустая БД - возвращает пустой список."""
    resp = await client.get("/activities/tree")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_tree_single_root_node_no_children(client, db_session):
    """Один корневой узел без детей - список из одного элемента с пустыми children."""
    activity = await make_activity(db_session, name="Единственный корень")
    await db_session.commit()

    resp = await client.get("/activities/tree")
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1
    node = tree[0]
    assert node["id"] == activity.id
    assert node["name"] == "Единственный корень"
    assert node["children"] == []


async def test_tree_multiple_root_nodes(client, db_session):
    """Несколько корневых узлов без parent_id - все отображаются как корни."""
    root_a = await make_activity(db_session, name="Root A")
    root_b = await make_activity(db_session, name="Root B")
    root_c = await make_activity(db_session, name="Root C")
    await db_session.commit()

    resp = await client.get("/activities/tree")
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 3
    ids = {node["id"] for node in tree}
    assert ids == {root_a.id, root_b.id, root_c.id}
    # все корни без детей
    for node in tree:
        assert node["children"] == []


async def test_tree_multiple_roots_some_with_children(client, db_session):
    """Несколько корней, у одного есть дети - остальные корни без детей"""
    root_with_children = await make_activity(db_session, name="Root With Kids")
    root_leaf = await make_activity(db_session, name="Root Leaf")
    child = await make_activity(
        db_session, name="Child", parent=root_with_children
    )
    await db_session.commit()

    resp = await client.get("/activities/tree")
    assert resp.status_code == 200
    result = resp.json()

    # Два корня
    assert len(result) == 2
    nodes_by_id = {node["id"]: node for node in result}

    # root_leaf - без детей
    assert nodes_by_id[root_leaf.id]["children"] == []

    # root_with_children - один ребёнок
    kids = nodes_by_id[root_with_children.id]["children"]
    assert len(kids) == 1
    assert kids[0]["id"] == child.id


# ---------------------------------------------------------------------------
# GET /activities/{id}/organizations
# ---------------------------------------------------------------------------

async def test_organizations_by_activity_not_found(client):
    resp = await client.get("/activities/99999/organizations")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Activity not found"


async def test_organizations_by_activity_empty_list(client, db_session):
    activity = await make_activity(db_session, name="Empty Activity")
    await db_session.commit()

    resp = await client.get(f"/activities/{activity.id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["items"] == []
    assert page["count"] == 0


async def test_organizations_by_activity_returns_linked_orgs(
    client, db_session
):
    activity = await make_activity(db_session, name="Tech")
    await make_org(
        db_session,
        "Org With Activity",
        lat=55.0,
        lon=37.0,
        activities=[activity],
    )
    await make_org(db_session, "Org Without Activity", lat=56.0, lon=38.0)

    resp = await client.get(f"/activities/{activity.id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["name"] == "Org With Activity"


async def test_organizations_by_activity_multiple_orgs(client, db_session):
    activity = await make_activity(db_session, name="Finance")
    await make_org(
        db_session, "Bank A", lat=55.0, lon=37.0, activities=[activity]
    )
    await make_org(
        db_session, "Bank B", lat=55.1, lon=37.1, activities=[activity]
    )
    await make_org(db_session, "Unrelated", lat=56.0, lon=38.0)

    resp = await client.get(f"/activities/{activity.id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 2
    assert len(page["items"]) == 2
    names = {o["name"] for o in page["items"]}
    assert names == {"Bank A", "Bank B"}


async def test_organizations_by_activity_response_schema(client, db_session):
    activity = await make_activity(db_session, name="Retail")
    await make_org(
        db_session,
        "Shop",
        lat=55.75,
        lon=37.62,
        address="Market St 1",
        phones=["79991234567"],
        activities=[activity],
    )

    resp = await client.get(f"/activities/{activity.id}/organizations")
    assert resp.status_code == 200
    page = resp.json()
    assert "items" in page
    assert "count" in page
    assert page["count"] == 1
    assert len(page["items"]) == 1
    item = page["items"][0]
    assert item["name"] == "Shop"
    assert item["building"]["address"] == "Market St 1"
    assert item["phones"][0]["phone"] == "79991234567"
    assert any(a["id"] == activity.id for a in item["activities"])


async def test_organizations_by_activity_includes_subtree_orgs(
    client, db_session
):
    """
    Эндпоинт работает рекурсивно через ltree (<@):
    организации дочерних активностей должны попадать в результат
    при запросе к родительской активности
    """
    tree = await make_activity_tree(db_session)
    await make_org(
        db_session,
        "Child Org",
        lat=55.0,
        lon=37.0,
        activities=[tree["child"]],
    )
    await make_org(
        db_session,
        "Grandchild Org",
        lat=55.1,
        lon=37.1,
        activities=[tree["grandchild"]],
    )

    resp = await client.get(
        f"/activities/{tree['root'].id}/organizations"
    )
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 2
    names = {o["name"] for o in page["items"]}
    assert names == {"Child Org", "Grandchild Org"}


async def test_organizations_by_activity_pagination(client, db_session):
    """Параметры limit и offset работают корректно"""
    activity = await make_activity(db_session, name="Paging Activity")
    for i in range(5):
        await make_org(
            db_session,
            f"Org {i}",
            lat=55.0 + i * 0.01,
            lon=37.0,
            activities=[activity],
        )

    resp = await client.get(
        f"/activities/{activity.id}/organizations",
        params={"limit": 2, "offset": 0},
    )
    assert resp.status_code == 200
    page = resp.json()
    assert page["count"] == 5
    assert len(page["items"]) == 2

    resp2 = await client.get(
        f"/activities/{activity.id}/organizations",
        params={"limit": 2, "offset": 2},
    )
    assert resp2.status_code == 200
    page2 = resp2.json()
    assert page2["count"] == 5
    assert len(page2["items"]) == 2

    # страницы не должны пересекаться
    ids_page1 = {o["id"] for o in page["items"]}
    ids_page2 = {o["id"] for o in page2["items"]}
    assert ids_page1.isdisjoint(ids_page2)


# ---------------------------------------------------------------------------
# ORM-уровень: создание активностей и связи parent/children
# ---------------------------------------------------------------------------

async def test_parent_relationship_works(db_session):
    """ORM relationship `parent` возвращает корректный объект"""
    tree = await make_activity_tree(db_session)

    result = await db_session.execute(
        select(Activity).where(Activity.id == tree["child"].id)
    )
    child = result.scalars().first()
    parent = await db_session.get(Activity, child.parent_id)

    assert parent is not None
    assert parent.id == tree["root"].id
    assert parent.name == "Root Activity"


async def test_activity_path_is_set_by_trigger(db_session):
    """На PostgreSQL триггер автоматически заполняет path при INSERT"""
    activity = await make_activity(db_session, name="Has Path")
    await db_session.commit()

    result = await db_session.execute(
        select(Activity.path).where(Activity.id == activity.id)
    )
    path_value = result.scalar()
    assert path_value is not None
