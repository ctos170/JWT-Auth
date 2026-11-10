from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status,Request,BackgroundTasks
from fastapi.exceptions import HTTPException
from src.core.decorators import handle_service_errors
from secrets import token_urlsafe
from hashlib import sha256
from datetime import datetime,timezone,timedelta
from src.core.config import settings
from src.database.models.models import Email_Verification_Token
from src.email.service import send_email
from ..repository import get_user_by_email_or_phone_number
from .repository import revoke_user_email_verification_tokens,get_active_email_verificaion_token



@handle_service_errors
async def resend_email_verification_token(
        email:str,
        background_tasks:BackgroundTasks,
        session:AsyncSession
    ):

      async with session.begin():
        now = datetime.now(timezone.utc)

        response = {
           "message":"Eposta adresiniz sistemimize kayıtlı ise eposta doğrulama bağlantınız gönderilecektir"
        }
        
        user = await get_user_by_email_or_phone_number(session,email) 
        
        if not user or user.user.email_verified:
           return response

        token = await get_active_email_verificaion_token(user.user_id,session)

        if token:
            passed_time = now - token.created_at
            timeout = timedelta(minutes=2)

            if passed_time < timeout:
                return response
        
        await revoke_user_email_verification_tokens(session,user.user_id)

            
        verification_token = token_urlsafe(32)
        hashed_verification_token = sha256(verification_token.encode("utf-8")).hexdigest()

        session.add(
            Email_Verification_Token(
                user_id=user.user_id,
                verification_token_hash=hashed_verification_token,
                expires_at=now + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
            )
        )

      frontend_base_url = settings.FRONTEND_BASE_URL.rstrip("/")
      verification_link = f"{frontend_base_url}/auth/verify-email?token={verification_token}"
      background_tasks.add_task(
            send_email,
            subject="Eposta Doğrulama Talebi",
            email_to=[email],
            template_name="email_verification.html",
            template_body={"email":email,"link":verification_link}
       )  

      return response














