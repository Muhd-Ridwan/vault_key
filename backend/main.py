from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import init_pool, close_pool, fetch_one
from routers.admin import router as admin_router
from routers.auth import router as auth_router
from routers.vault import router as vault_router
from routers.totp import router as totp_router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield  # is where the app lives
    await close_pool()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[url.strip() for url in settings.frontend_url.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Require-TOTP"],
)
app.include_router(auth_router)
app.include_router(vault_router)
app.include_router(totp_router)
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    result = await fetch_one("SELECT 1 AS ok")
    if result is None:
        return {"status": "error", "database": "unreachable"}
    return {"status": "Vault Key OK", "database": "connected"}
