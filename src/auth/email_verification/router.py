from fastapi import APIRouter,Depends,status,Request,BackgroundTasks,Body,Query
from src.database.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from typing import Any
from src.main import limiter
from pydantic import EmailStr
from .service import resend_email_verification_token,verify_user_email
from .schemas import Email_Verification_Request


router = APIRouter()


@router.post("/resend",status_code=status.HTTP_200_OK,summary="Eposta doğrulama bağlantısını yeniden gönderme")
@limiter.limit("3/hour")
async def resend(
    request:Request,
    background_tasks:BackgroundTasks,
    email:EmailStr=Body(embed=True,examples=["abc@gmail.com"]),
    session:AsyncSession=Depends(get_db)
    ):
    return await resend_email_verification_token(email,background_tasks,session)



@router.get("/verify",status_code=status.HTTP_200_OK,summary="Eposta adresi doğrulama")
@limiter.limit("5/minute")
async def verify(
    request:Request,
    token_data:Email_Verification_Request=Query(),
    session:AsyncSession=Depends(get_db)
    ):

    return await verify_user_email(token_data.token,session)










