import logging
import math
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, field_validator
from crypto import encrypt, decrypt
from db import execute, fetch_one, fetch_all
from audit import log_action
from dependencies import get_current_user, require_totp_unlock

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vault", tags=["vault"])


# SCHEMAS
class VaultEntryCreate(BaseModel):
    entry_type: str
    title: str
    username: str | None = None
    secret: str
    url: str | None = None
    notes: str | None = None
    description: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty.")
        return v.strip()


class VaultEntryUpdate(BaseModel):
    title: str | None = None
    username: str | None = None
    secret: str | None = None
    url: str | None = None
    notes: str | None = None
    description: str | None = None


# HELPERS


async def get_visibility() -> str:
    row = await fetch_one("SELECT vault_visibility FROM app_settings WHERE id = 1")
    return row["vault_visibility"] if row else "shared"


# ROUTES


@router.get("/entries")
async def list_entries(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    created_by_name: str | None = Query(None),
    title: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    visibility = await get_visibility()

    conditions = ["ve.is_deleted = FALSE"]
    params: list = []

    if visibility == "private":
        conditions.append("ve.created_by = %s")
        params.append(current_user["sub"])
    if date_from:
        conditions.append("ve.created_at::date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("ve.created_at::date <= %s")
        params.append(date_to)
    if title:
        conditions.append("ve.title ILIKE %s")
        params.append(f"{title}%")
    # Created by name filter only applies
    if visibility == "shared" and created_by_name:
        conditions.append("u.name ILIKE %s")
        params.append(f"%{created_by_name}%")
    where_clause = " AND ".join(conditions)
    offset = (page - 1) * limit

    base_query = f"""
            FROM vault_entries ve LEFT JOIN users u ON u.id = ve.created_by
            WHERE {where_clause}
    """
    count_row = await fetch_one(
        f"SELECT COUNT(*) AS total {base_query}",
        tuple(params),
    )
    total = count_row["total"]
    items = await fetch_all(
        f"""
        SELECT ve.id, ve.entry_type, ve.title, ve.username, ve.url, ve.description,
            ve.created_by, ve.created_at, ve.updated_at,
            u.name AS created_by_name
        {base_query}
        ORDER BY ve.created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (limit, offset),
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
        "visibility": visibility,
    }


@router.get("/creators")
async def list_creators(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return await fetch_all("""
        SELECT DISTINCT u.id, u.name
        FROM vault_entries ve
        JOIN users u ON u.id = ve.created_by
        WHERE ve.is_deleted = FALSE
        ORDER BY u.name
        """)


@router.post("/entries", status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: VaultEntryCreate,
    current_user: dict = Depends(require_totp_unlock),
) -> dict:
    encrypted_secret = encrypt(body.secret)
    encrypted_notes = encrypt(body.notes) if body.notes else None

    row = await fetch_one(
        """
        INSERT INTO vault_entries (entry_type, title, username, encrypted_secret, url, description, notes, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, entry_type, title, username, url, description, created_at
        """,
        (
            body.entry_type,
            body.title,
            body.username,
            encrypted_secret,
            body.url,
            body.description,
            encrypted_notes,
            current_user["sub"],
        ),
    )
    await log_action(
        actor=current_user,
        action="create",
        entry_id=str(row["id"]),
        target_label=row["title"],
    )
    return row


@router.get("/entries/{entry_id}/secret")
async def reveal_secret(
    entry_id: str,
    current_user: dict = Depends(require_totp_unlock),
) -> dict:
    row = await fetch_one(
        """
        SELECT encrypted_secret, notes, title
        FROM vault_entries
        WHERE id = %s AND is_deleted = FALSE
        """,
        (entry_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault entry not found.",
        )
    await log_action(
        actor=current_user,
        action="view",
        entry_id=entry_id,
        target_label=row["title"],
    )
    return {
        "secret": decrypt(bytes(row["encrypted_secret"])),
        "notes": decrypt(bytes(row["notes"])) if row["notes"] else None,
    }


@router.put("/entries/{entry_id}")
async def update_entry(
    entry_id: str,
    body: VaultEntryUpdate,
    current_user: dict = Depends(require_totp_unlock),
) -> dict:
    row = await fetch_one(
        "SELECT id FROM vault_entries WHERE id = %s AND is_deleted = FALSE",
        (entry_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vault entry not found."
        )
    updated = await fetch_one(
        """
        UPDATE vault_entries SET
        title = COALESCE(%s, title),
        username = COALESCE(%s, username),
        encrypted_secret = COALESCE(%s, encrypted_secret),
        url = COALESCE(%s, url),
        description = COALESCE(%s, description),
        notes = COALESCE(%s, notes),
        updated_by = %s,
        updated_at = now()
        WHERE id = %s
        RETURNING id, entry_type, title, username, url, description, updated_at
        """,
        (
            body.title,
            body.username,
            encrypt(body.secret) if body.secret else None,
            body.url,
            body.description,
            encrypt(body.notes) if body.notes else None,
            current_user["sub"],
            entry_id,
        ),
    )
    await log_action(
        actor=current_user,
        action="update",
        entry_id=entry_id,
        target_label=updated["title"],
    )
    return updated


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    row = await fetch_one(
        "SELECT id, title FROM vault_entries WHERE id = %s AND is_deleted = FALSE",
        (entry_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault entry not found.",
        )

    await execute(
        """
        UPDATE vault_entries SET
        is_deleted = TRUE,
        deleted_at = now(),
        deleted_by = %s
        WHERE id = %s
        """,
        (current_user["sub"], entry_id),
    )
    await log_action(
        actor=current_user,
        action="delete",
        entry_id=entry_id,
        target_label=row["title"],
    )
    return {"message": "Vault entry deleted successfully."}
