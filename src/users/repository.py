from sqlalchemy import select,or_,update
from sqlalchemy.orm import selectinload,joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.models import User,User_Credential,Session,Token_Blacklist
from sqlalchemy.exc import IntegrityError
from typing import Optional,Any
from uuid import UUID


async def get_user_with_credential_by_id(id:UUID,session:AsyncSession):
    stmt = (
        select(User)
        .options(
            joinedload(User.credential)
        ).where(User.id == id)
    )

    result = await session.scalars(stmt)

    return result.unique().one()


