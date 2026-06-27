from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import init_pool, close_pool, fetch_one
from routers.admin import router as admin_router
from routers.auth import router as auth_router
from routers.vault import router as vault_router
from routers.totp import router as totp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield  # is where the app lives
    await close_pool()


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(vault_router)
app.include_router(totp_router)
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    result = await fetch_one("SELECT 1 AS ok")
    if result is None:
        return {"status": "error", "database": "unreachable"}
    return {"status": "Vauly Key OK", "database": "connected"}
