from pydantic import BaseModel,EmailStr
from typing import Optional
from datetime import datetime


class User_Profile_Response(BaseModel):
    name:str
    surname:str
    age:int
    is_active:bool 
    credential : Credential


class Credential(BaseModel):
    email:EmailStr
    phone_number : Optional[str] = None


class User_Sessions_Response(BaseModel):
    device_info:str
    ip_address:str
    is_revoked:bool 
    expires_at:datetime
    created_at:datetime