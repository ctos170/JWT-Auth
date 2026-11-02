from fastapi import APIRouter,Depends,status,Body,BackgroundTasks,Query
from src.database.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from src.core.config import settings
from typing import Any
from pydantic import EmailStr
from src.auth.password_reset import service
from .schemas import Reset_Password_Request


router = APIRouter()


@router.post("/forgot-password",status_code=status.HTTP_200_OK,summary="Şifre sıfırlama talebi")
async def password_reset_request(
    background_tasks:BackgroundTasks,
    email:EmailStr=Body(embed=True,examples=["abc@gmail.com"]),
    session:AsyncSession = Depends(get_db)
    ):

    result = await service.password_reset_request(email,background_tasks,session)

    return JSONResponse(
        content=result
    )    


@router.post("/reset-password",status_code=status.HTTP_200_OK,summary="Şifre sıfırlama.Yenisini belirleme.")
async def reset_user_password(form_data:Reset_Password_Request,session:AsyncSession=Depends(get_db)):

      result = await service.reset_user_password(form_data,session)       

      return JSONResponse(
           content=result
      )      























