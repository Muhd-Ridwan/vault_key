from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import settings

pool: AsyncConnectionPool | None = None


async def init_pool() -> None:
    global pool
    pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row},
    )
    await pool.open()


async def close_pool() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None


async def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    if pool is None:
        raise RuntimeError("Database pool is not initialized.")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchone()


async def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    if pool is None:
        raise RuntimeError("Database pool is not initialized.")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def execute(sql: str, params: tuple = ()) -> None:
    if pool is None:
        raise RuntimeError("Database pool is not initialized.")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
