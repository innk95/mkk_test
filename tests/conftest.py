import os
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

os.environ.setdefault("API_KEY", "testkey")

from app.dependencies import get_db
from app.main import app
from app.models.activity import Activity
from app.models.building import Building
from app.models.organization import Organization, OrganizationPhone


def run_alembic_migrations(sync_url: str) -> None:
    # Надо явно установить переменную окружения перед миграциями
    os.environ["DATABASE_URL"] = sync_url
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as container:
        sync_url = container.get_connection_url()
        async_url = sync_url.replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        )
        run_alembic_migrations(sync_url)
        yield async_url


@pytest_asyncio.fixture
async def db_engine(postgres_container):
    engine = create_async_engine(postgres_container, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_engine):
    yield
    try:
        async with db_engine.begin() as conn:
            await conn.execute(text(
                "TRUNCATE organization_activity, organization_phones, "
                "organizations, buildings, activities "
                "RESTART IDENTITY CASCADE"
            ))
    except ProgrammingError:
        pass


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "testkey"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def make_building(
    session: AsyncSession,
    lat: float,
    lon: float,
    address: str = "Тестовая улица 1",
) -> Building:
    building = Building(address=address, latitude=lat, longitude=lon)
    session.add(building)
    await session.flush()
    return building


async def make_org(
    session: AsyncSession,
    name: str,
    lat: float,
    lon: float,
    address: str = "Тестовая улица 1",
    phones: list[str] | None = None,
    activities: list[Activity] | None = None,
) -> Organization:
    building = await make_building(session, lat=lat, lon=lon, address=address)
    org = Organization(name=name, building_id=building.id)
    session.add(org)
    await session.flush()
    for phone in phones or []:
        session.add(OrganizationPhone(organization_id=org.id, phone=phone))
    if activities:
        from app.models.organization import organization_activity
        await session.flush()
        for activity in activities:
            await session.execute(
                organization_activity.insert().values(
                    organization_id=org.id, activity_id=activity.id
                )
            )
    await session.commit()
    return org


async def make_activity(
    session: AsyncSession,
    name: str,
    parent: Activity | None = None,
) -> Activity:
    """path в пути автоматически заполняется тригером"""
    activity = Activity(name=name, parent_id=parent.id if parent else None)
    session.add(activity)
    await session.flush()
    return activity


async def make_activity_tree(
    session: AsyncSession,
) -> dict[str, Activity]:
    """
    Создать дерево активностей трёх уровней:
      root
        child
          grandchild
    Возвращает словарь {'root': ..., 'child': ..., 'grandchild': ...}.
    """
    root = await make_activity(session, name="Root Activity")
    child = await make_activity(session, name="Child Activity", parent=root)
    grandchild = await make_activity(
        session, name="Grandchild Activity", parent=child
    )
    await session.commit()
    return {"root": root, "child": child, "grandchild": grandchild}
