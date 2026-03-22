import os
from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

API_KEY = os.getenv("API_KEY", "")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="API key missing")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
