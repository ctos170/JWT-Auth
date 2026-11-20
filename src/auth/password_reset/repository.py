from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime,timezone
from sqlalchemy import select,update
from sqlalchemy.orm import contains_eager
from uuid import UUID
from src.database.models.models import Password_Reset_Token,User



async def revoke_user_reset_token(user_id:UUID,session:AsyncSession):
    "Geçerli olan şifre sıfırlama tokenlarının iptali"
    now = datetime.now(timezone.utc)

    await session.execute(
        update(Password_Reset_Token)
        .where(
            Password_Reset_Token.user_id == user_id,
            Password_Reset_Token.expires_at >= now,
            Password_Reset_Token.revoked_at.is_(None),
            Password_Reset_Token.used_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )


async def get_active_password_reset_token(user_id:UUID,session:AsyncSession):
    now = datetime.now(timezone.utc)
    
    return await session.scalar(
        select(Password_Reset_Token)
        .where(
            Password_Reset_Token.user_id == user_id,
            Password_Reset_Token.used_at.is_(None),
            Password_Reset_Token.revoked_at.is_(None),
            Password_Reset_Token.expires_at >= now
        )
    )


async def get_password_reset_token(token_hash:str,session:AsyncSession):
    result = await session.scalars(
        select(Password_Reset_Token)
        .join(Password_Reset_Token.user)
        .join(User.credential)
        .options(contains_eager(Password_Reset_Token.user).contains_eager(User.credential))
        .where(Password_Reset_Token.token_hash == token_hash)
        .with_for_update(of=Password_Reset_Token)
    )
        

    return result.unique().one_or_none()