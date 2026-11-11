from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,update
from sqlalchemy.orm import joinedload
from uuid import UUID
from src.database.models.models import Email_Verification_Token,User


async def revoke_user_email_verification_tokens(session:AsyncSession,user_id:UUID):
    "Geçerli olan eposta doğrulama tokenlarının iptali"

    await session.execute(
        update(Email_Verification_Token)
        .where(
            Email_Verification_Token.user_id == user_id,
            Email_Verification_Token.used_at.is_(None),
            Email_Verification_Token.revoked_at.is_(None)
        ).values(revoked_at=datetime.now(timezone.utc))
    )


async def get_active_email_verificaion_token(user_id:UUID,session:AsyncSession): 
    now = datetime.now(timezone.utc)

    token = await session.scalar(
        select(Email_Verification_Token)
        .where(
          Email_Verification_Token.user_id==user_id,
          Email_Verification_Token.expires_at > now,
          Email_Verification_Token.revoked_at.is_(None),
          Email_Verification_Token.used_at.is_(None)
        )
    )

    return token


async def get_email_verification_token_row(hashed_token:str,session:AsyncSession):
    result = await session.scalars(
        select(Email_Verification_Token)
        .options(joinedload(Email_Verification_Token.user))
        .where(Email_Verification_Token.verification_token_hash == hashed_token)
        .with_for_update(of=Email_Verification_Token)
    )

    return result.unique().one_or_none()


