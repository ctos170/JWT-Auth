from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status,Request,BackgroundTasks
from fastapi.exceptions import HTTPException
from src.core.decorators import handle_service_errors
from datetime import datetime,timezone,timedelta
from src.core.config import settings
from typing import Any
from secrets import token_urlsafe
from hashlib import sha256
from pydantic import EmailStr
from src.auth.repository import (
    get_user_by_email_or_phone_number,
    revoke_sessions,
    get_revoke_sessions_ids,
    get_revoke_sessions_access_token,
    get_jti_from_blacklist,
    add_blacklist
)
from .repository import revoke_user_reset_token,get_password_reset_token
from src.database.models.models import Password_Reset_Token
from src.email.service import send_email
from .schemas import Reset_Password_Request
from src.core.security import hash_password



@handle_service_errors
async def password_reset_request(email:EmailStr,background_tasks:BackgroundTasks,session:AsyncSession):

    async with session.begin():
       response = {
            "message":"Eposta adresiniz sistemimizde kayıtlı ise şifre sıfırlama bağlanısı gönredilecektir."
        }
       
       user = await get_user_by_email_or_phone_number(session,email)
    
       if not user:
            return response
       
       await revoke_user_reset_token(user.user_id,session)
       
        
       now = datetime.now(timezone.utc)

       reset_token = token_urlsafe(32)
       hashed_reset_token = sha256(reset_token.encode("utf-8")).hexdigest()
       
       session.add(
           Password_Reset_Token(
               user_id = user.user_id,
               token_hash = hashed_reset_token,
               expires_at = now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
           )
       )       
       
        
       frontend_base_url = settings.FRONTEND_BASE_URL.rstrip("/")
       reset_link = f"{frontend_base_url}/auth/reset-password?token={reset_token}"
       
       background_tasks.add_task(
           send_email,
           subject="Şifre sıfırlama talebi",
           email_to=[email],
           template_name="password_reset_request.html",
           template_body={"email":email,"link":reset_link}
       )

    return response   


@handle_service_errors
async def reset_user_password(form_data:Reset_Password_Request,session:AsyncSession):
    now = datetime.now(timezone.utc)
    new_password = form_data.password
    raw_token=form_data.token
   
    token_hash = sha256(raw_token.encode("utf-8")).hexdigest()
    password_hash = hash_password(new_password)

    async with session.begin():

        token_row = await get_password_reset_token(token_hash,session)

        if not token_row or token_row.used_at or token_row.revoked_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geçersiz şifre sıfırlama tokenı.",
            )

        if token_row.expires_at < now :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Şifre sıfırlama bağlantısının süresi geçmiş"
            ) 

        # * Token geçerli
        user = token_row.user
        # * Şifre değiştirildi. 
        user.credential.password_hash = password_hash
        token_row.used_at = now
        
        # * Oturumlar iptal edilecek.
        await revoke_sessions(session,user.id)  
        revoke_session_ids = await get_revoke_sessions_ids(session,user.id)
        live_access_rows = await get_revoke_sessions_access_token(session,revoke_session_ids)
        live_access_jtis = [ token_row.jti for token_row in live_access_rows]
         
        blacklisted_jtis = set(await get_jti_from_blacklist(session,live_access_jtis))

        # * Geçerli access tokenlardan blacklistte olmayanlar blackliste eklendi
        for access_row in live_access_rows:
            if access_row.jti not in blacklisted_jtis:
                blacklist_dict = {
                    "jti":access_row.jti,
                    "revoked_at": now,
                    "expires_at":access_row.expires_at
                }

                await add_blacklist(session,blacklist_dict)

    return {"message":"Şifreniz başarıyla değiştirilmiştir.Giriş yapabilirsiniz."}        

        
    
