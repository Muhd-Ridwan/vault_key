import logging
import math
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from audit import log_action
from db import execute, fetch_one, fetch_all
from dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# HELPERS


def require_superadmin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required.",
        )
    return current_user


# ACCESS REQUESTS


@router.get("/access-requests")
async def list_access_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=150),
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(require_superadmin),
) -> dict:
    conditions = []
    params: list = []

    if status_filter:
        conditions.append("status = %s")
        params.append(status_filter)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit
    base_query = f"FROM access_requests {where_clause}"

    count_row = await fetch_one(
        f"SELECT COUNT(*) AS total {base_query}",
        tuple(params),
    )
    total = count_row["total"]

    items = await fetch_all(
        f"""
        SELECT id, name, email, phone, reason, status, requested_at, actioned_at
        {base_query}
        ORDER BY requested_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (limit, offset),
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@router.post("/access-requests/{request_id}/approve")
async def approve_access_request(
    request_id: str,
    current_user: dict = Depends(require_superadmin),
) -> dict:
    row = await fetch_one(
        "SELECT id, name, email, status FROM access_requests WHERE id = %s",
        (request_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found."
        )
    if row["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {row['status']}.",
        )

    await execute(
        """
        UPDATE access_requests
        SET status = 'approved', actioned_at = now(), actioned_by = %s
        WHERE id = %s
        """,
        (current_user["sub"], request_id),
    )

    await execute(
        """
        INSERT INTO users (email, name, role, status)
        VALUES (%s, %s, 'member', 'approved')
        ON CONFLICT (email) DO NOTHING
        """,
        (row["email"], row["name"]),
    )

    await log_action(
        actor=current_user,
        action="approve_user",
        target_label=row["email"],
        detail=f"Approved access request for {row['name']}",
    )
    return {"message": f"Access request approved. {row['name']} can log in."}


@router.post("/access-requests/{request_id}/reject")
async def reject_access_request(
    request_id: str,
    current_user: dict = Depends(require_superadmin),
) -> dict:
    row = await fetch_one(
        "SELECT id, name, email, status FROM access_requests WHERE id = %s",
        (request_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found."
        )
    if row["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {row['status']}.",
        )

    await execute(
        """
        UPDATE access_requests
        SET status = 'rejected', actioned_at = now(), actioned_by = %s
        WHERE id = %s
        """,
        (current_user["sub"], request_id),
    )
    await log_action(
        actor=current_user,
        action="reject_user",
        target_label=row["email"],
        detail=f"Rejected access request for {row['name']}",
    )
    return {"message": f"Access request rejected for {row['name']}."}


# USERS
@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=150),
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(require_superadmin),
) -> dict:

    conditions = []
    params: list = []

    if status_filter:
        conditions.append("status = %s")
        params.append(status_filter)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit
    base_query = f"FROM users {where_clause}"

    count_row = await fetch_one(
        f"SELECT COUNT(*) AS total {base_query}",
        tuple(params),
    )
    total = count_row["total"]

    items = await fetch_all(
        f"""
        SELECT id, email, name, role, status, created_at
        {base_query}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (limit, offset),
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@router.post("/users/{user_id}/revoke")
async def revoke_user(
    user_id: str,
    current_user: dict = Depends(require_superadmin),
) -> dict:
    row = await fetch_one(
        "SELECT id, email, name, status FROM users WHERE id = %s",
        (user_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if row["status"] == "revoked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already revoked."
        )

    await execute(
        "UPDATE users SET status = 'revoked' WHERE id = %s",
        (user_id,),
    )
    await log_action(
        actor=current_user,
        action="revoke_user",
        target_label=row["email"],
        detail=f"Revoked access for {row['name']}",
    )
    return {"message": f"User {row['name']} has been revoked."}


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    current_user: dict = Depends(require_superadmin),
) -> dict:
    row = await fetch_one(
        "SELECT id, email, name, status FROM users WHERE id = %s",
        (user_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if row["status"] == "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already approved."
        )

    await execute(
        "UPDATE users SET status = 'approved' WHERE id = %s",
        (user_id,),
    )
    await log_action(
        actor=current_user,
        action="approve_user",
        target_label=row["email"],
        detail=f"Re-approved access for {row['name']}",
    )
    return {"message": f"User {row['name']} has been approved."}


# AUDIT LOG


@router.get("/audit")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    action: str | None = Query(None),
    current_user: dict = Depends(require_superadmin),
) -> dict:
    conditions = []
    params: list = []

    if date_from:
        conditions.append('"timestamp"::date >= %s')
        params.append(date_from)
    if date_to:
        conditions.append('"timestamp"::date <= %s')
        params.append(date_to)
    if action:
        conditions.append("action = %s")
        params.append(action)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    base_query = f"FROM audit_log {where_clause}"

    count_row = await fetch_one(
        f"SELECT COUNT(*) AS total {base_query}",
        tuple(params),
    )
    total = count_row["total"]

    items = await fetch_all(
        f"""
        SELECT id, actor_email, action, target_label, detail, ip_address, "timestamp"
        {base_query}
        ORDER BY "timestamp" DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (limit, offset),
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }
