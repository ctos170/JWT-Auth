from fastapi import APIRouter,Depends,status
from src.database.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from src.core.dependencies import get_current_user
from src.database.models.models import User
from typing import Annotated
from datetime import datetime,timezone,timedelta
from .schemas import User_Profile_Response

router = APIRouter()


@router.get("/me",status_code=status.HTTP_200_OK,summary="Profil",response_model=User_Profile_Response)
async def profile(user:User=Depends(get_current_user)):
    return user


