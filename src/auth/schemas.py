from pydantic import BaseModel,Field,EmailStr,field_validator
from typing import Optional
from src.utils.password_validator import  validate_password_complexity



NO_WHITESPACE_REGEX = r"^\S+$" 


class Register_Request(BaseModel):
    name : str = Field(...,min_length=2,examples=["Arda"])
    surname : str = Field(...,min_length=2,examples=["Kaymak"])
    age : int = Field(...,ge=18,examples=[21])
    email : EmailStr = Field(...,examples=["abc@gmail.com"])
    phone_number : Optional[str] = None
    password : str = Field(...,min_length=8,examples=["P@ssw0rd!"])

   
    @field_validator("password")
    def validate_password(cls, v:str):
         return validate_password_complexity(v,NO_WHITESPACE_REGEX)



class Login_Request(BaseModel):
    email : EmailStr  = Field(...,examples=["abc@gmail.com"])
    password : str = Field(...,min_length=8,examples=["P@ssw0rd!"],pattern=NO_WHITESPACE_REGEX)
        