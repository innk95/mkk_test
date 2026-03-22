from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.dependencies import get_db, verify_api_key
from app.models.building import Building
from app.models.organization import Organization
from app.schemas import OrganizationOut, Page

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(verify_api_key)],
)


def _base_select() -> Select:
    return select(Organization).options(
        joinedload(Organization.building),
        selectinload(Organization.phones),
        selectinload(Organization.activities),
    )


def _apply_filters(
    q: Select,
    name: str | None,
    lat: float | None,
    lon: float | None,
    radius_km: float | None,
    lat_min: float | None,
    lat_max: float | None,
    lon_min: float | None,
    lon_max: float | None,
) -> Select:
    if name is not None:
        q = q.filter(Organization.name.ilike(f"%{name}%"))

    if lat is not None and lon is not None and radius_km is not None:
        q = q.join(Organization.building).filter(
            func.acos(
                func.cos(func.radians(lat))
                * func.cos(func.radians(Building.latitude))
                * func.cos(
                    func.radians(Building.longitude) - func.radians(lon)
                )
                + func.sin(func.radians(lat))
                * func.sin(func.radians(Building.latitude))
            )
            * 6371
            <= radius_km
        )
    elif (
        lat_min is not None
        and lat_max is not None
        and lon_min is not None
        and lon_max is not None
    ):
        q = q.join(Organization.building).filter(
            Building.latitude >= lat_min,
            Building.latitude <= lat_max,
            Building.longitude >= lon_min,
            Building.longitude <= lon_max,
        )
    return q


@router.get("", response_model=Page[OrganizationOut])
async def list_organizations(
    name: str | None = None,
    # переменные для поиска по радиусу
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = None,
    # переменные для поиска по прямоугольнику
    lat_min: float | None = None,
    lat_max: float | None = None,
    lon_min: float | None = None,
    lon_max: float | None = None,
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[OrganizationOut]:
    count_q = _apply_filters(
        select(func.count(Organization.id.distinct())),
        name, lat, lon, radius_km, lat_min, lat_max, lon_min, lon_max,
    )
    total = (await db.execute(count_q)).scalar()

    data_q = _apply_filters(
        _base_select(),
        name, lat, lon, radius_km, lat_min, lat_max, lon_min, lon_max,
    ).order_by(Organization.name).offset(offset).limit(limit)
    result = await db.execute(data_q)
    return Page(
        items=result.unique().scalars().all(),
        limit=limit,
        offset=offset,
        count=total,
    )


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
) -> OrganizationOut:
    result = await db.execute(
        _base_select().filter(Organization.id == org_id)
    )
    org = result.unique().scalars().first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org
