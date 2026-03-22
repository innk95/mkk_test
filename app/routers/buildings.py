from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.dependencies import get_db, verify_api_key
from app.models.building import Building
from app.models.organization import Organization
from app.schemas import BuildingOut, OrganizationOut, Page

router = APIRouter(
    prefix="/buildings",
    tags=["buildings"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=Page[BuildingOut])
async def list_buildings(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[BuildingOut]:
    total = (await db.execute(select(func.count(Building.id)))).scalar()
    result = await db.execute(
        select(Building).order_by(Building.id).offset(offset).limit(limit)
    )
    return Page(
        items=result.scalars().all(),
        limit=limit,
        offset=offset,
        count=total,
    )


@router.get("/{building_id}", response_model=BuildingOut)
async def get_building(
    building_id: int,
    db: AsyncSession = Depends(get_db),
) -> BuildingOut:
    building = await db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/{building_id}/organizations",
    response_model=Page[OrganizationOut],
)
async def organizations_by_building(
    building_id: int,
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[OrganizationOut]:
    building = await db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    total = (
        await db.execute(
            select(func.count(Organization.id)).filter(
                Organization.building_id == building_id
            )
        )
    ).scalar()
    result = await db.execute(
        select(Organization)
        .options(
            joinedload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities),
        )
        .filter(Organization.building_id == building_id)
        .order_by(Organization.name)
        .offset(offset)
        .limit(limit)
    )
    return Page(
        items=result.unique().scalars().all(),
        limit=limit,
        offset=offset,
        count=total,
    )
