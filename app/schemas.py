from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    offset: int
    limit: int
    count: int


class ActivityOut(BaseModel):
    id: int
    name: str
    parent_id: int | None

    model_config = {"from_attributes": True}


class ActivityTreeNode(BaseModel):
    id: int
    name: str
    children: list[ActivityTreeNode] = []

    model_config = {"from_attributes": True}


class BuildingOut(BaseModel):
    id: int
    address: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


class PhoneOut(BaseModel):
    id: int
    phone: str

    model_config = {"from_attributes": True}


class OrganizationOut(BaseModel):
    id: int
    name: str
    building: BuildingOut
    phones: list[PhoneOut]
    activities: list[ActivityOut]

    model_config = {"from_attributes": True}
