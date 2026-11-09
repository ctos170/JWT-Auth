from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status,Request,BackgroundTasks
from fastapi.exceptions import HTTPException
from src.core.decorators import handle_service_errors
from secrets import token_urlsafe
from hashlib import sha256
from src.email.service import send_email

