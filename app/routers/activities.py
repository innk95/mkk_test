from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.dependencies import get_db, verify_api_key
from app.models.activity import Activity
from app.models.organization import Organization, organization_activity
from app.schemas import ActivityTreeNode, OrganizationOut, Page

router = APIRouter(
    prefix="/activities",
    tags=["activities"],
    dependencies=[Depends(verify_api_key)],
)


@router.get(
    "/tree",
    response_model=list[ActivityTreeNode],
)
async def activities_tree(
    db: AsyncSession = Depends(get_db),
) -> list[ActivityTreeNode]:
    stmt = select(Activity).order_by(Activity.path)
    result = await db.execute(stmt)
    activities = result.scalars().all()

    nodes: dict[int, ActivityTreeNode] = {
        a.id: ActivityTreeNode(id=a.id, name=a.name) for a in activities
    }

    roots: list[ActivityTreeNode] = []
    for activity in activities:
        node = nodes[activity.id]
        if activity.parent_id is None or activity.parent_id not in nodes:
            roots.append(node)
        else:
            nodes[activity.parent_id].children.append(node)

    return roots


@router.get(
    "/{activity_id}/organizations",
    response_model=Page[OrganizationOut],
)
async def organizations_by_activity(
    activity_id: int,
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[OrganizationOut]:
    activity = await db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    root_path_sq = (
        select(Activity.path)
        .where(Activity.id == activity_id)
        .scalar_subquery()
    )

    count_stmt = (
        select(func.count(func.distinct(Organization.id)))
        .select_from(Organization)
        .join(
            organization_activity,
            Organization.id == organization_activity.c.organization_id,
        )
        .join(Activity, Activity.id == organization_activity.c.activity_id)
        .where(Activity.path.op("<@")(root_path_sq))
    )
    total = (await db.execute(count_stmt)).scalar_one()

    if total == 0:
        return Page(items=[], limit=limit, offset=offset, count=0)

    items_stmt = (
        select(Organization)
        .options(
            joinedload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities),
        )
        .join(
            organization_activity,
            Organization.id == organization_activity.c.organization_id,
        )
        .join(Activity, Activity.id == organization_activity.c.activity_id)
        # тут находим по пути находим всех предков
        .where(Activity.path.op("<@")(root_path_sq))
        .distinct()
        .order_by(Organization.name)
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(items_stmt)
    return Page(
        items=result.unique().scalars().all(),
        limit=limit,
        offset=offset,
        count=total,
    )
