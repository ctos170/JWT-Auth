from fastapi import APIRouter,Depends,status,Request
from src.database.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from .schemas import Register_Request,Login_Request
from .service import register_user,user_login,refresh_tokens,user_logout
from src.core.config import settings
from src.core.dependencies import verify_refresh_token,get_access_payload
from typing import Any
from src.database.models.models import User
from .password_reset.router import router as password_reset_router


router = APIRouter()

router.include_router(password_reset_router)

@router.post("/register",status_code=status.HTTP_201_CREATED,summary="Kullanıcı kayıt")
async def register(form_data:Register_Request,session:AsyncSession=Depends(get_db)):
   
   result = await register_user(form_data,session)

   return JSONResponse(content=result)


@router.post("/login",status_code=status.HTTP_200_OK,summary="Giriş")
async def login(form_data:Login_Request,req:Request,session:AsyncSession=Depends(get_db)):

   result : dict[str, str] = await user_login(form_data,req,session)

   refresh_token = result["refresh_token"]
   token_exp = settings.REFRESH_TOKEN_EXPIRE_DAYS

   access_token = result["access_token"]

   response = JSONResponse(
      content={
         "message":"Giriş başarılı.",
         "access_token":access_token,
         "token_type": "bearer"
      }
   )

   response.set_cookie(
      "refresh_token",
      value=refresh_token,
      max_age=token_exp*24*60*60,
      httponly=True,
      secure=settings.REFRESH_COOKIE_SECURE,
      samesite=settings.REFRESH_COOKIE_SAMESITE,
      domain=settings.REFRESH_COOKIE_DOMAIN,
      path="/",
   )           

   return response


@router.post("/refresh",status_code=status.HTTP_200_OK,summary="Tokenları yenileme")
async def refresh(
   payload:dict[str,Any]=Depends(verify_refresh_token),
   session:AsyncSession=Depends(get_db)

   ):

   result : dict[str, str] = await refresh_tokens(session,payload["jti"])

   refresh_token = result["refresh_token"]
   token_exp = settings.REFRESH_TOKEN_EXPIRE_DAYS
   access_token = result["access_token"]

   response = JSONResponse(
         content={
            "message":"Tokenlar başarıyla yenilendi.",
            "access_token":access_token,
            "token_type": "bearer"
         }
      )
   
   response.set_cookie(
         "refresh_token",
         value=refresh_token,
         max_age=token_exp*24*60*60,
         httponly=True,
         secure=settings.REFRESH_COOKIE_SECURE,
         samesite=settings.REFRESH_COOKIE_SAMESITE,
         domain=settings.REFRESH_COOKIE_DOMAIN,
         path="/",
      )           
   
   return response


@router.post("/logout",status_code=status.HTTP_200_OK,summary="Çıkış yapma")
async def logout(
   payload:dict[str,Any]=Depends(get_access_payload),
   session:AsyncSession=Depends(get_db)
   ):
   
   result = await user_logout(session,payload)

   response = JSONResponse(
      content=result
   )

   response.delete_cookie(
      "refresh_token",
      domain=settings.REFRESH_COOKIE_DOMAIN,
      path="/",
   )

   return response
   

