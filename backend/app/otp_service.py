from fastapi_mail import FastMail, MessageSchema
from pydantic import EmailStr
from .config import conf  # Email configuration
import pyotp
from app.db import db

# Generate or retrieve a user's secret key
async def get_or_create_secret_key(user_email: str):
    user = await db.users.find_one({"email": user_email})
    if "secret_key" not in user:
        secret_key = pyotp.random_base32()  # Generate a new secret key
        await db.users.update_one({"email": user_email}, {"$set": {"secret_key": secret_key}})
    else:
        secret_key = user["secret_key"]  # Retrieve existing secret key

    return secret_key

# Generate the OTP for a user
async def generate_otp(user_email: str):
    secret_key = await get_or_create_secret_key(user_email)
    totp = pyotp.TOTP(secret_key)  # Initialize TOTP with the user's secret key
    return totp.now()  # Generate the current time-based OTP

# Send the OTP via email
async def send_otp_email(email: EmailStr, otp:str):
    message = MessageSchema(
        subject="Your OTP Code for Spearow authentication",
        recipients=[email],
        body=f"Your OTP code is: {otp}",
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)

async def send_verified_email(email: EmailStr):
    message = MessageSchema(
        subject="Account Verified",
        recipients=[email],
        body=f"Your Spearow Account has been Verified! Login with your details to Generate a custom Report of your account breaches!",
        subtype="html",
    )

    fm = FastMail(conf)
    await fm.send_message(message)

# send email to user when a report generated on their behalf
async def send_report_generated_email(email: EmailStr):
    message = MessageSchema(
        subject="Report Generate",
        recipients=[email],
        body=f"A report has been generated on your behalf.",
        subtype="html",
    )

    fm = FastMail(conf)
    await fm.send_message(message)

# send a report to all admins when an unverified user uploads an ID
async def notify_admins_of_verification(admin_emails: list, user_email: str):
    message = MessageSchema(
        subject="User Verification Needed",
        recipients=admin_emails,
        body=f"The user with email {user_email} needs to be verified. Please log in to the system to review.",
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)