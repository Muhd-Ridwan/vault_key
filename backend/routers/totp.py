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
from db import execute, fetch_one
from dependencies import get_current_user, unlock_windows

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/totp", tags=["totp"])

UNLOCK_MINUTES = 30


# SCHEMAS
class TOTPCodeRequest(BaseModel):
    code: str


# HELPERS
async def get_totp_secret_plaintext(user_id: str) -> str | None:
    row = await fetch_one(
        "SELECT secret, confirmed FROM totp_secrets WHERE user_id = %s",
        (user_id,),
    )
    if row is None or not row["confirmed"]:
        return None
    return decrypt(bytes(row["secret"]))


def set_unlock(user_id: str) -> datetime:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=UNLOCK_MINUTES)
    unlock_windows[user_id] = expires_at
    return expires_at


# ROUTES


@router.get("/status")
async def totp_status(current_user: dict = Depends(get_current_user)) -> dict:
    user_id = current_user["sub"]
    row = await fetch_one(
        "SELECT confirmed FROM totp_secrets WHERE user_id = %s",
        (user_id,),
    )
    enrolled = row is not None and row["confirmed"]
    expiry = unlock_windows.get(user_id)
    unlocked = expiry is not None and datetime.now(timezone.utc) < expiry
    return {"enrolled": enrolled, "unlocked": unlocked}


@router.post("/enroll")
async def enroll(current_user: dict = Depends(get_current_user)) -> dict:
    user_id = current_user["sub"]
    existing = await fetch_one(
        "SELECT confirmed FROM totp_secrets WHERE user_id = %s",
        (user_id,),
    )
    if existing and existing["confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="TOTP already active on your account.",
        )

    plain_secret = pyotp.random_base32()
    encrypted_secret = encrypt(plain_secret)

    await execute(
        """
        INSERT INTO totp_secrets (user_id, secret, confirmed)
        VALUES (%s, %s, FALSE)
        ON CONFLICT (user_id) DO UPDATE SET secret = EXCLUDED.secret, confirmed = FALSE
        """,
        (user_id, encrypted_secret),
    )

    totp = pyotp.TOTP(plain_secret)
    uri = totp.provisioning_uri(name=current_user["email"], issuer_name="VaultKey")

    img = qrcode.make(uri)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return {"qr_code": qr_b64, "secret": plain_secret}


@router.post("/verify")
async def verify_enrollment(
    body: TOTPCodeRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = current_user["sub"]
    row = await fetch_one(
        "SELECT secret, confirmed FROM totp_secrets WHERE user_id = %s",
        (user_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enrollment in progress. Call /enroll first.",
        )
    if row["confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="TOTP already active on your account",
        )

    plain_secret = decrypt(bytes(row["secret"]))
    totp = pyotp.TOTP(plain_secret)

    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code.",
        )

    await execute(
        "UPDATE totp_secrets SET confirmed = TRUE WHERE user_id = %s",
        (user_id,),
    )
    expires_at = set_unlock(user_id)
    await log_action(
        actor=current_user,
        action="enroll_totp",
        detail="TOTP enrollment complete.",
    )
    return {
        "message": "TOTP enrolled and unlocked.",
        "expires_at": expires_at.isoformat(),
    }


@router.post("/unlock")
async def unlock(
    body: TOTPCodeRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = current_user["sub"]

    plain_secret = await get_totp_secret_plaintext(user_id)
    if plain_secret is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not enrolled. Call /enroll first.",
        )
    totp = pyotp.TOTP(plain_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code.",
        )
    expires_at = set_unlock(user_id)
    return {
        "message": f"Unlocked for {UNLOCK_MINUTES} minutes.",
        "expires_at": expires_at.isoformat(),
    }


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
        SELECT ts.user_id, u.email
        FROM totp_secrets ts
        JOIN users u ON u.id = ts.user_id
        WHERE ts.user_id = %s
        """,
        (user_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No TOTP enrollment found for this user.",
        )

    await execute(
        "DELETE FROM totp_secrets WHERE user_id = %s",
        (user_id,),
    )

    unlock_windows.pop(user_id, None)
    await log_action(
        actor=current_user,
        action="reset_totp",
        target_label=row["email"],
        detail=f"TOTP reset by superadmin for {row['email']}",
    )
    return {"message": "TOTP enrollment reset. User may re-enroll."}
