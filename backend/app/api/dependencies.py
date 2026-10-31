"""API route dependencies for user resolution and security boundaries."""

from typing import Optional
import uuid
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ValidationError
from backend.app.db.dependencies import get_db
from backend.app.models.user import User


async def get_current_user_id(
    db: AsyncSession = Depends(get_db),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
) -> uuid.UUID:
    """Resolve the current active user ID.

    Supports:
    - Standard UUID strings
    - Firebase UID strings (deterministically hashed via uuid5)
    - Optional X-User-Email and X-User-Name headers for real Google/Firebase profile names
    """
    if x_user_id:
        try:
            parsed_id = uuid.UUID(x_user_id)
        except (ValueError, TypeError):
            # Deterministically map Firebase/external auth UID to a stable UUID
            parsed_id = uuid.uuid5(uuid.NAMESPACE_URL, f"firebase:{x_user_id}")

        stmt = select(User).where(User.id == parsed_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            display_name = x_user_name or f"User {str(parsed_id)[:8]}"
            email = x_user_email or f"user-{str(parsed_id)[:8]}@paisaflow.app"
            # Provision user on demand
            user = User(
                id=parsed_id,
                display_name=display_name,
                email=email,
                locale="en-IN",
                timezone="Asia/Kolkata",
                default_currency="INR",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        elif x_user_name or x_user_email:
            # Update profile info if newly available from Google login
            if x_user_name and user.display_name != x_user_name:
                user.display_name = x_user_name
            if x_user_email and user.email != x_user_email:
                user.email = x_user_email
            await db.commit()

        return user.id

    # Fallback: Query first existing user or provision Asha Mehta
    stmt = select(User).limit(1)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        user = User(
            id=uuid.uuid4(),
            display_name="Asha Mehta (Demo)",
            email="asha.mehta@synthetic-paisaflow.demo",
            locale="en-IN",
            timezone="Asia/Kolkata",
            default_currency="INR",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user.id

