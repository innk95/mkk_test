"""
Проверка проверки ключа в ендпоинтах
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio

PROTECTED_URLS = [
    "/organizations",
    "/organizations/1",
    "/buildings",
    "/buildings/1/organizations",
    "/activities/1/organizations",
    "/activities/tree",
]


@pytest.mark.parametrize("url", PROTECTED_URLS)
async def test_wrong_api_key_returns_403(url: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "wrong-key"},
    ) as anon:
        resp = await anon.get(url)
    assert resp.status_code == 403
