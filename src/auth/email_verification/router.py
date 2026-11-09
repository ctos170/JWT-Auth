from fastapi import APIRouter,Depends,status,Request,BackgroundTasks,Body
from src.database.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from typing import Any
from src.main import limiter
from pydantic import EmailStr


router = APIRouter()


@router.post("/resend-email-verification",status_code=status.HTTP_200_OK,summary="Eposta doğrulama bağlantısını yeniden gönderme")
@limiter.limit("3/hour")
async def resend_email_verification_token(
    request:Request,
    background_tasks:BackgroundTasks,
    email:EmailStr=Body(embed=True),
    session:AsyncSession=Depends(get_db)
    ):
    pass