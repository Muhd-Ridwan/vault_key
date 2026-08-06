import base64
import logging
import pyotp
import qrcode

from datetime import datetime, timezone, timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from audit import log_action
from crypto import encrypt, decrypt
from db import execute, fetch_one, fetch_all
from dependencies import get_current_user, unlock_windows

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/totp", tags=["totp"])

UNLOCK_MINUTES = 30


# SCHEMAS
class TOTPEnrollRequest(BaseModel):
    label: str


class TOTPVerifyRequest(BaseModel):
    device_id: str
    code: str


class TOTPCodeRequest(BaseModel):
    code: str


# HELPERS
async def get_confirmed_devices(user_id: str) -> list[dict]:
    return await fetch_all(
        "SELECT id, secret FROM totp_devices WHERE user_id = %s AND confirmed = TRUE",
        (user_id,),
    )


def set_unlock(user_id: str) -> datetime:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=UNLOCK_MINUTES)
    unlock_windows[user_id] = expires_at
    return expires_at


# ROUTES


@router.get("/status")
async def totp_status(current_user: dict = Depends(get_current_user)) -> dict:
    user_id = current_user["sub"]
    row = await fetch_one(
        "SELECT 1 FROM totp_devices WHERE user_id = %s AND confirmed = TRUE LIMIT 1",
        (user_id,),
    )
    enrolled = row is not None
    expiry = unlock_windows.get(user_id)
    unlocked = expiry is not None and datetime.now(timezone.utc) < expiry
    return {"enrolled": enrolled, "unlocked": unlocked}


@router.get("/devices")
async def list_devices(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return await fetch_all(
        """
        SELECT id, label, confirmed, created_at, last_used_at
        FROM totp_devices
        WHERE user_id = %s
        ORDER BY created_at
        """,
        (current_user["sub"],),
    )


@router.post("/enroll")
async def enroll(
    body: TOTPEnrollRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = current_user["sub"]
    plain_secret = pyotp.random_base32()
    encrypted_secret = encrypt(plain_secret)

    row = await fetch_one(
        """
        INSERT INTO totp_devices (user_id, label, secret, confirmed)
        VALUES (%s, %s, %s, FALSE)
        RETURNING id
        """,
        (user_id, body.label, encrypted_secret),
    )

    totp = pyotp.TOTP(plain_secret)
    uri = totp.provisioning_uri(
        name=f"{current_user['email']} ({body.label})", issuer_name="VaultKey"
    )

    img = qrcode.make(uri)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return {"device_id": row["id"], "qr_code": qr_b64, "secret": plain_secret}


@router.post("/verify")
async def verify_enrollment(
    body: TOTPVerifyRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    row = await fetch_one(
        "SELECT id, user_id, label, secret, confirmed FROM totp_devices WHERE id = %s AND user_id = %s",
        (body.device_id, current_user["sub"]),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching enrollment found.",
        )
    if row["confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This device is already active.",
        )

    plain_secret = decrypt(bytes(row["secret"]))
    totp = pyotp.TOTP(plain_secret)

    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code.",
        )

    await execute(
        "UPDATE totp_devices SET confirmed = TRUE WHERE id = %s",
        (row["id"],),
    )
    expires_at = set_unlock(current_user["sub"])
    await log_action(
        actor=current_user,
        action="add_totp_device",
        detail=f"Added TOTP device '{row['label']}'.",
    )
    return {
        "message": "TOTP device enrolled and unlocked.",
        "expires_at": expires_at.isoformat(),
    }


@router.post("/unlock")
async def unlock(
    body: TOTPCodeRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = current_user["sub"]
    devices = await get_confirmed_devices(user_id)
    if not devices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not enrolled. Call /enroll first.",
        )

    matched_device_id = None
    for device in devices:
        plain_secret = decrypt(bytes(device["secret"]))
        totp = pyotp.TOTP(plain_secret)
        if totp.verify(body.code, valid_window=1):
            matched_device_id = device["id"]
            break

    if matched_device_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code.",
        )

    await execute(
        "UPDATE totp_devices SET last_used_at = now() WHERE id = %s",
        (matched_device_id,),
    )
    expires_at = set_unlock(user_id)
    return {
        "message": f"Unlocked for {UNLOCK_MINUTES} minutes.",
        "expires_at": expires_at.isoformat(),
    }


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    row = await fetch_one(
        "SELECT id, label FROM totp_devices WHERE id = %s AND user_id = %s",
        (device_id, current_user["sub"]),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found.",
        )

    await execute("DELETE FROM totp_devices WHERE id = %s", (device_id,))
    await log_action(
        actor=current_user,
        action="delete_totp_device",
        detail=f"Removed TOTP device '{row['label']}'.",
    )
    return {"message": "Device removed."}


@router.delete("/reset/{user_id}")
async def reset_totp(
    user_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user["role"] != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required.",
        )

    row = await fetch_one(
        """
        SELECT u.email, COUNT(td.id) AS device_count
        FROM users u
        LEFT JOIN totp_devices td ON td.user_id = u.id
        WHERE u.id = %s
        GROUP BY u.email
        """,
        (user_id,),
    )
    if row is None or row["device_count"] == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No TOTP enrollment found for this user.",
        )

    await execute("DELETE FROM totp_devices WHERE user_id = %s", (user_id,))

    unlock_windows.pop(user_id, None)
    await log_action(
        actor=current_user,
        action="reset_totp",
        target_label=row["email"],
        detail=f"All TOTP devices reset by superadmin for {row['email']}",
    )
    return {"message": "All TOTP devices reset. User may re-enroll."}
