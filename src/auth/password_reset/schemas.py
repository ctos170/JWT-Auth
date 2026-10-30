from pydantic import BaseModel,Field,field_validator
from src.utils.password_validator import validate_password_complexity
import re

NO_WHITESPACE_REGEX = r"^\S+$" 

class Reset_Password_Request(BaseModel):
    password : str = Field(...,min_length=8,examples=["!dr0wss@P"])
    token: str = Field(min_length=43, max_length=43)


    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v,NO_WHITESPACE_REGEX)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
            raise ValueError("Invalid token format")
    
        return value
    


