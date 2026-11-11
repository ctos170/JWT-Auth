from pydantic import BaseModel,Field,field_validator
import re

NO_WHITESPACE_REGEX = r"^\S+$" 

class Email_Verification_Request(BaseModel):
    token: str = Field(min_length=43, max_length=43)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
            raise ValueError("Invalid token format")
    
        return value
    


