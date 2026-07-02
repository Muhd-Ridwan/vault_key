import logging
import jwt
import resend
import html

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, field_validator

from audit import log_action
from config import settings
from db import execute, fetch_one

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

resend.api_key = settings.resend_api

# PYDANTIC SCHEMAS


class GoogleLoginRequest(BaseModel):
    token: str


class AccessRequestForm(BaseModel):
    name: str
    email: EmailStr
    phone: str
    reason: str

    @field_validator("email")
    @classmethod
    def must_be_google_account(cls, v: str) -> str:
        allowed_domains = {"gmail.com", "googlemail.com"}
        domain = v.split("@")[-1].lower()
        if domain not in allowed_domains:
            raise ValueError("Only Google accounts (gmail.com) are accepted")
        return v.lower()


# HELPERS


def issue_jwt(user: dict) -> str:
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def send_approval_email(to_email: str, name: str) -> None:
    try:
        resend.Emails.send(
            {
                "from": settings.resend_email_from,
                "to": to_email,
                "subject": "Your Vault Key Access has been approved",
                "html": f"""
                <p>Hi {html.escape(name)}, </p>
                <p>Your request to access VaultKey has been approved.</p>
                <p>You can now sign in using your Google account.</p>
                <p>Best Regards</p>
                <p>Ridwan</p>
            """,
            }
        )
    except Exception:
        logger.exception("Failed to send approval email to %s", to_email)


# ROUTES


@router.post("/google")
async def google_login(body: GoogleLoginRequest, request: Request) -> dict:
    try:
        id_info = id_token.verify_oauth2_token(
            body.token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token.",
        )

    email = id_info["email"].lower()

    user = await fetch_one(
        "SELECT id, email, role, status FROM users WHERE email = %s",
        (email,),
    )

    if user:
        if user["status"] == "revoked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your access has been revoked. Contact the administrator",
            )
        await log_action(
            actor={"sub": str(user["id"]), "email": user["email"]},
            action="login",
            ip=request.client.host if request.client else None,
        )
        return {"access_token": issue_jwt(user), "token_type": "bearer"}

    access_request = await fetch_one(
        "SELECT status FROM access_requests WHERE email = %s",
        (email,),
    )

    if access_request:
        if access_request["status"] == "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your access request is pending approval.",
            )
        if access_request["status"] == "rejected":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your access request was rejected. Contact the administrator.",
            )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access. Please request access first.",
    )


@router.post("/request-access", status_code=status.HTTP_201_CREATED)
async def request_access(body: AccessRequestForm) -> dict:
    existing = await fetch_one(
        "SELECT id FROM access_requests WHERE email = %s OR phone = %s",
        (body.email, body.phone),
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A request with this email or phone number already exists.",
        )

    await execute(
        """
        INSERT INTO access_requests (name, email, phone, reason)
        VALUES (%s, %s, %s, %s)
        """,
        (body.name, body.email, body.phone, body.reason),
    )

    try:
        resend.Emails.send(
            {
                "from": settings.resend_email_from,
                "to": settings.resend_email_from,
                "subject": f"New Vault Key access request from {html.escape(body.name)}",
                "html": f"""
                <p>A new access request has been submitted.</p>
                <p><strong>Name:</strong> {html.escape(body.name)}</p>
                <p><strong>Email:</strong> {html.escape(body.email)}</p>
                <p><strong>Phone:</strong> {html.escape(body.phone)}</p>
                <p><strong>Reason:</strong> {html.escape(body.reason)}</p>
                <p>Best Regards</p>
                <p>Ridwan</p>
            """,
            }
        )
    except Exception:
        logger.exception("Failed to send access request notification email.")

    return {"message": "Access request submitted successfully"}
