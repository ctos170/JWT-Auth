from pydantic import BaseModel,EmailStr,ConfigDict
from typing import Optional
from datetime import datetime
from pydantic_extra_types.phone_numbers import PhoneNumber 

class Credential(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email:EmailStr
    phone_number : Optional[PhoneNumber] = None


class User_Profile_Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name:str
    surname:str
    age:int
    is_active:bool 
    credential : Credential


class User_Sessions_Response(BaseModel):
    device_info:str
    ip_address:str
    is_revoked:bool 
    expires_at:datetime
    created_at:datetime