from db import execute


async def log_action(
    actor: dict,
    action: str,
    entry_id: str | None = None,
    target_label: str | None = None,
    detail: str | None = None,
    ip: str | None = None,
) -> None:
    await execute(
        """
        INSERT INTO audit_log (user_id, actor_email, action, entry_id, target_label, detail, ip_address) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            actor.get("sub"),
            actor.get("email"),
            action,
            entry_id,
            target_label,
            detail,
            ip,
        ),
    )
