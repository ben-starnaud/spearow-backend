from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginData(BaseModel):
    email: str
    password: str
    otp: Optional[str] = None  # OTP is optional

class RegisterData(BaseModel):
    name: str
    email: str
    password: str

class OTPVerification(BaseModel):
    email: EmailStr
    otp: str