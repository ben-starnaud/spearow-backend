from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from app.db import db
from app.models.report import RequestData
from app.routes.report_routes import generate_report_on_auth_user, generate_csv, generate_pdf
from app.auth import create_access_token
from jose import jwt
from bson import ObjectId
from ..otp_service import send_verified_email, send_report_generated_email

router = APIRouter()


@router.post("/user/{user_id}/send-verified-email")
async def send_verified_email_endpoint(user_id: str, request: Request):
    # Check for Authorization token in the header
    authorization: str = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token not provided")

    token = authorization.split(" ")[1]  # Extract the token from 'Bearer <token>'

    try:
        # Decode the JWT to retrieve the email (sub field)
        admin_email = jwt.decode(
            token, key=None, algorithms=["HS256"], options={"verify_signature": False}
        ).get("sub")
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Ensure the requesting user is an admin
    admin_user = await db.users.find_one({"email": admin_email})
    if not admin_user or admin_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # Find the user by user_id
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Send the verified email
    await send_verified_email(user["email"])

    return {"message": "Verification email sent successfully"}


@router.get("/user-data")
async def fetch_user_data(request: Request):
    # Extract the token from the Authorization header
    authorization: str = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token not provided")

    token = authorization.split(" ")[1]  # Extract the token from 'Bearer <token>'

    try:
        # Decode the JWT to retrieve the email (sub field)
        user_email = jwt.decode(
            token, key=None, algorithms=["HS256"], options={"verify_signature": False}
        ).get("sub")

    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Ensure the user exists in the database
    admin_user = await db.users.find_one({"email": user_email})

    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    # Check if the user is an admin
    if admin_user.get("user_type") != "admin":
        raise HTTPException(
            status_code=403, detail="You do not have access to this resource"
        )

    # Fetch all users' data from the database
    users = await db.users.find().to_list(100)  # Limit to 100 users for performance

    # Prepare the data for response
    users_data = [
        {
            "name": user.get("name"),
            "email": user.get("email"),
            "verified": user.get("verified", False),
            "admin": True if user.get("user_type") == "admin" else False,
            "id": str(user.get("_id")),  # Convert ObjectId to string
            "id_file": user.get("id_file"),
        }
        for user in users
    ]

    return {"message": "User data fetched successfully", "users": users_data}


@router.post("/user-report")
async def get_user_report(request: Request):
    data = await request.json()  # Get JSON data from the request body
    is_admin = data.get("admin")

    # Ensure the value is provided and valid
    if is_admin is None:
        raise HTTPException(status_code=400, detail="Admin status is required")

    # Extract the token from the Authorization header
    authorization: str = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token not provided")

    token = authorization.split(" ")[1]  # Extract the token from 'Bearer <token>'

    try:
        # Decode the JWT to retrieve the email (sub field)
        user_email = jwt.decode(
            token, key=None, algorithms=["HS256"], options={"verify_signature": False}
        ).get("sub")
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Ensure the requesting user is an admin
    admin_user = await db.users.find_one({"email": user_email})
    if not admin_user or admin_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # Find the user's data
    user_data = await db['users'].find_one({"_id": ObjectId(data['userId'])})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Create a temporary access token for the user
    access_token_expires = timedelta(minutes=5)
    access_token = create_access_token(
        data={"sub": user_data["email"]}, expires_delta=access_token_expires
    )

    request_data = RequestData(
        reportType="user",
        reportCategory=None,
        reportFormat=data['reportFormat'],
        notes=None,
        token=access_token
    )

    # notify user that report has been generated
    send_report_generated_email(user_data["email"])

    # Check if the user has any breaches linked to their account
    if "breaches" in user_data:
        if data['reportFormat'] == "CSV":
            return await generate_csv(request_data, user_data['breaches'])
        else:
            return await generate_pdf(request_data, user_data['breaches'])
    else:
        # Generate the report
        user_report = await generate_report_on_auth_user(request_data)

        if data['reportFormat'] == "CSV":
            return await generate_csv(request_data, user_report)
        else:
            return await generate_pdf(request_data, user_report)


@router.patch("/user/{user_id}/admin-status")
async def update_admin_status(user_id: str, request: Request):
    data = await request.json()  # Get JSON data from the request body
    is_admin = data.get("admin")

    # Ensure the value is provided and valid
    if is_admin is None:
        raise HTTPException(status_code=400, detail="Admin status is required")

    # Extract the token from the Authorization header
    authorization: str = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token not provided")

    token = authorization.split(" ")[1]  # Extract the token from 'Bearer <token>'

    try:
        # Decode the JWT to retrieve the email (sub field)
        user_email = jwt.decode(
            token, key=None, algorithms=["HS256"], options={"verify_signature": False}
        ).get("sub")
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Ensure the requesting user is an admin
    admin_user = await db.users.find_one({"email": user_email})
    if not admin_user or admin_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # Find the user to update
    user_to_update = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user's admin status in the database
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"user_type": "admin" if is_admin else "standard"}},
    )

    return {"message": "Admin status updated successfully", "admin": is_admin}


@router.patch("/user/{user_id}/verify-status")
async def update_verify_status(user_id: str, request: Request):
    data = await request.json()  # Get JSON data from the request body
    is_verified = data.get("verified")

    # Ensure the value is provided and valid
    if is_verified is None:
        raise HTTPException(status_code=400, detail="Admin status is required")

    # Extract the token from the Authorization header
    authorization: str = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token not provided")

    token = authorization.split(" ")[1]  # Extract the token from 'Bearer <token>'

    try:
        # Decode the JWT to retrieve the email (sub field)
        user_email = jwt.decode(
            token, key=None, algorithms=["HS256"], options={"verify_signature": False}
        ).get("sub")
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Ensure the requesting user is an admin
    admin_user = await db.users.find_one({"email": user_email})
    if not admin_user or admin_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # Find the user to update
    user_to_update = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user's admin status in the database
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"verified": is_verified}},
    )

    return {"message": "Admin status updated successfully", "admin": is_verified}

 # find all admins email addresses
async def get_admin_emails():
    # Fetch all users with user_type 'admin' and get their email addresses
    admins = await db.users.find({"user_type": "admin"}, {"_id": 0, "email": 1}).to_list(None)
    
    # Extract email addresses into a list
    email_list = [admin.get('email') for admin in admins]

    return email_list