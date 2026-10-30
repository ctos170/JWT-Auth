from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,update
from sqlalchemy.orm import selectinload,joinedload
from sqlalchemy.exc import IntegrityError
from typing import Optional,Any
from uuid import UUID
from src.database.models.models import Password_Reset_Token,User



async def revoke_user_reset_token(user_id:UUID,session:AsyncSession):
    "Geçerli olan şifre sıfırlama tokenlarının iptali"
    stmt =(
        update(Password_Reset_Token)
        .where(
            Password_Reset_Token.user_id == user_id,
            Password_Reset_Token.revoked_at == None,
            Password_Reset_Token.used_at == None,
        )
        .values(revoked_at=datetime.now(timezone.utc))
    ) 

    await session.execute(stmt)


async def get_password_reset_token(token_hash:str,session:AsyncSession):
    stmt = (
        select(Password_Reset_Token).
        options(joinedload(Password_Reset_Token.user).joinedload(User.credential))
        .where(Password_Reset_Token.token_hash == token_hash)
    ).with_for_update(of=Password_Reset_Token)

    result = await session.scalars(stmt)

    return result.unique().one_or_none()