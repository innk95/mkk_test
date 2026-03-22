from fastapi import FastAPI

from app.routers import activities, buildings, organizations

app = FastAPI(
    description="**X-API-KEY для тестирования:** prod - `your_api_key`; dev - `testkey`",
)

app.include_router(buildings.router)
app.include_router(organizations.router)
app.include_router(activities.router)


@app.get("/healthcheck")
def healthcheck() -> dict:
    return {"status": "ok"}

