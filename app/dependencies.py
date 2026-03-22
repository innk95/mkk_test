import os
from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

API_KEY = os.getenv("API_KEY", "")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def verify_api_key(x_api_key: str = Header(...)) -> None:
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(
            status_code=403, detail="Invalid or missing API key"
        )
