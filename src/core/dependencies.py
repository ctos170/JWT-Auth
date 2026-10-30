from src.users.repository import get_user_by_id
from src.auth.repository import get_access_token_by_jti, get_active_access_token_jti
from typing import Annotated
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from fastapi import Depends,status,Cookie
from .security import verify_token
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_db
from fastapi.exceptions import HTTPException
from src.auth.repository import get_active_session
from typing import Any



security = HTTPBearer()


def get_access_payload(
    credentials:Annotated[HTTPAuthorizationCredentials,Depends(security)],
    ):

    token = credentials.credentials
    payload = verify_token(token,"access")

    return payload


async def get_current_user(
        payload:dict[str,Any] = Depends(get_access_payload),
        session:AsyncSession=Depends(get_db)
    ):

    jti = payload["jti"]
    user_id = payload["sub"]

    # * Token Blacklist tablosunda gelen token'ın payloadunda jti'yi buluyoruz.
    access_token_jti = await get_access_token_by_jti(jti,session)

    if access_token_jti :
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturumunuzdan çıkış yapılmıştır.Lütfen tekrar giriş yapınız."
        )

    active_token = await get_active_access_token_jti(jti, session)
    if not active_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturumunuz etkin değil. Lütfen tekrar giriş yapın.",
        )

    user = await get_user_by_id(user_id,session)

    return user


async def verify_refresh_token(refresh_token:str|None=Cookie(default=None)):
    if not refresh_token :
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token çerezi bulunamadı.Süresi doldu veya çıkış yapıldı."
        )

    
    payload = verify_token(refresh_token,"refresh")


    return payload
