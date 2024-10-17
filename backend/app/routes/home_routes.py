from fastapi import APIRouter, HTTPException, Depends, Request, File, UploadFile
from app.db import db
from jose import jwt
import os
from app.otp_service import notify_admins_of_verification
from app.routes.admin_routes import get_admin_emails

router = APIRouter()

# Define the folder where the files will be stored
UPLOAD_FOLDER = "uploaded_ids"


@router.get("/home")
async def home():
    return {"message": "Welcome to the home page"}


@router.get("/get-user-info")
async def get_user_info(request: Request):

    # Extract the token from the Authorization header
    authorization: str = request.headers.get("Authorization")

    if authorization:
        token = authorization.split(" ")[1]  # Extract the token from 'Bearer <token>'
        # Decode the JWT to retrieve the email (sub field)
        user_email = jwt.decode(
            token, key=None, algorithms=["HS256"], options={"verify_signature": False}
        ).get("sub")

        user = await db.users.find_one({"email": user_email})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Add "user_type" field if it's missing
        if "user_type" not in user:
            await db.users.update_one(
                {"email": user_email}, {"$set": {"user_type": "standard"}}
            )
            user["user_type"] = "standard"

        id_file = False
        if "id_file" not in user:
            id_file = False
        else:
            id_file = True

        return {
            "message": "Users info:",
            "user_type": user["user_type"],
            "name": user["name"],
            "verified": user["verified"],
            "id_file": id_file,
        }
    else:
        raise HTTPException(status_code=401, detail="Authorization token not provided")


@router.post("/uploadID")
async def upload_id(request: Request, file: UploadFile = File(...)):

    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Extract the token from the Authorization header
    authorization: str = request.headers.get("Authorization")

    if authorization:
        token = authorization.split(" ")[1]  # Extract the token from 'Bearer <token>'
        # Decode the JWT to retrieve the email (sub field)
        user_email = jwt.decode(
            token, key=None, algorithms=["HS256"], options={"verify_signature": False}
        ).get("sub")

        user = await db.users.find_one({"email": user_email})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get the original file extension
        _, file_extension = os.path.splitext(file.filename)

        # Construct a new filename using the user's name or email and file extension
        new_filename = f"{user_email}_id{file_extension}"

        # Save the file to the server with the new filename
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Update the database with the file path (not the actual file)
        await db.users.update_one(
            {"email": user_email}, {"$set": {"id_file": file_path}}
        )

        #notify admins of new upload
        admins = await get_admin_emails()
        await notify_admins_of_verification(admins,user_email)
        

        return {"message": "Your ID has been successfully uploaded!"}
    else:
        raise HTTPException(status_code=401, detail="Authorization token not provided")
