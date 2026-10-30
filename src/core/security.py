from pwdlib import PasswordHash
import argon2
import jwt
from .config import settings
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from fastapi.exceptions import HTTPException
from fastapi import status


password_hash = PasswordHash.recommended()


def hash_password(passsword:str) :
    return password_hash.hash(passsword)


def verify_password(password:str,hashed_password:str):
    return password_hash.verify(password,hashed_password)


def create_random_token():
    return str(uuid4())


def create_access_token(sub:str,jti:str):
    "ACCESS TOKEN ÜRETİMİ"

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload :dict[str,Any] = {
        "sub":sub,
        "jti" : jti,
        "iat": now,
        "type" : "access",
        "exp" : expires
    }
    
    encoded_jwt = jwt.encode(payload,settings.SECRET_KEY,algorithm=settings.ALGORITHM)
    return encoded_jwt
    

def create_refresh_token(sub:str,jti:str):
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload : dict[str,Any] = {
        "sub":sub,
        "jti" : jti,
        "iat": now,
        "type" : "refresh",
        "exp" : expires
    }

    encoded_jwt = jwt.encode(payload,settings.SECRET_KEY,algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token:str,type:str):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=settings.ALGORITHM
        )

        token_type = payload.get("type")
        if token_type != type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Geçersiz token türü. '{type}' bekleniyordu ama '{token_type}' geldi."
            )
            
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token süresi dolmuş. Lütfen tekrar giriş yapın veya token'ı yenileyin."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya işlenemeyen token."
        )