from fastapi import APIRouter, HTTPException, Depends
from app.models.login import LoginData, RegisterData, OTPVerification
from app.db import get_db
from app.auth import create_access_token
from passlib.context import CryptContext
from ..otp_service import send_otp_email, generate_otp, get_or_create_secret_key
import pyotp
from datetime import timedelta, datetime
from jose import jwt, JWTError
from app.auth import SECRET_KEY, ALGORITHM
from app.models.reset_password import ForgotPasswordRequest, ResetPasswordRequest
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register")
async def register(data: RegisterData, db: AsyncIOMotorDatabase = Depends(get_db)):
 
    existing_user = await db.users.find_one({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = pwd_context.hash(data.password)

    new_user = {
        "name": data.name,
        "email": data.email,
        "password": hashed_password,
        "user_type": "standard",  # Can be customized based on your needs
        "verified": False  # Default is False; can be updated later
    }

    try:
        result = await db.users.insert_one(new_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
    return {"message": "User registered successfully", "user_id": str(result.inserted_id)}

@router.post("/login")
async def login(data: LoginData, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Add "verified" field if it's missing
    if "verified" not in user:
        await db.users.update_one({"email": data.email}, {"$set": {"verified": False}})
        user["verfied"] = False

    # If user not verified
    if True:
        if pwd_context.verify(data.password, user["password"]):
            # Second stage (user entering OTP)
            if data.otp:
                # Verify OTP
                secret_key = await get_or_create_secret_key(user["email"])
                totp = pyotp.TOTP(secret_key)

                if totp.verify(data.otp, valid_window=2):
                    # OTP is valid
                    access_token_expires = timedelta(minutes=30)
                    access_token = create_access_token(
                        data={"sub": user["email"]}, expires_delta=access_token_expires
                    )
                    return {
                        "message": "OTP is valid. Login successful!",
                        "token": access_token,
                        "name": user["name"],
                    }
                else:
                    # Invalid OTP
                    raise HTTPException(status_code=400, detail="Invalid OTP. Please try again or request a new OTP.")
                
            else:
                # First stage (email and password correct), send OTP
                otp = await generate_otp(user["email"])
                await send_otp_email(user["email"], otp)  # Send OTP via email
                return {"message": "OTP sent. Please check your email."}

        else:
            # Invalid credentials
            raise HTTPException(status_code=400, detail="Invalid password")

    else:
        # If user is verified, allow regular login
        if pwd_context.verify(data.password, user["password"]):
            # Create a JWT token
            access_token_expires = timedelta(minutes=30)
            access_token = create_access_token(
                data={"sub": user["email"]}, expires_delta=access_token_expires
            )
            return {
                "message": "Login successful",
                "token": access_token,
                "name": user["name"],
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid password")


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncIOMotorDatabase = Depends(get_db)): 
    user = await db.users.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Send OTP
    otp = await generate_otp(user["email"])
    await send_otp_email(user["email"], otp)  # Send OTP via email

    return {"message": "Password reset request received"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncIOMotorDatabase = Depends(get_db)):

    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    hashed_password = pwd_context.hash(request.new_password)

    await db.users.update_one({"email": request.email}, {"$set": {"password": hashed_password}})

    return {"message": "Password reset successful"}


@router.post("/verify-otp")
async def verify_otp(data: OTPVerification, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Retrieve user's secret key
    secret_key = await get_or_create_secret_key(user["email"])

    totp = pyotp.TOTP(secret_key)

    is_valid = totp.verify(data.otp, valid_window=2)

    if is_valid:
        return {"message": "OTP is valid. Login successful!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP")