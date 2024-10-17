import httpx
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict
from ..auth import get_current_user
from ..db import db
from bson import ObjectId
import json
import os
import logging
from datetime import datetime, timedelta

router = APIRouter()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for HIBP data classes
HIBP_DATA_CLASSES: List[str] = []
LAST_UPDATE_TIME: datetime = datetime.min

async def update_hibp_data_classes():
    global HIBP_DATA_CLASSES, LAST_UPDATE_TIME
    current_time = datetime.now()
    
    # Update only if it's been more than a day since the last update
    if current_time - LAST_UPDATE_TIME > timedelta(days=1):
        hibp_api_key = os.getenv("HIBP_API_KEY")
        if not hibp_api_key:
            logger.error("HIBP_API_KEY is not set in the environment variables")
            raise HTTPException(status_code=500, detail="Server configuration error")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://haveibeenpwned.com/api/v3/dataclasses",
                    headers={"hibp-api-key": hibp_api_key}
                )
                response.raise_for_status()
                HIBP_DATA_CLASSES = response.json()
                LAST_UPDATE_TIME = current_time
                logger.info("HIBP data classes updated successfully")
        except httpx.HTTPError as e:
            logger.error(f"Error fetching HIBP data classes: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch data classes")

@router.get("/dataclasses")
async def get_dataclasses():
    try:
        await update_hibp_data_classes()
        return {"dataclasses": HIBP_DATA_CLASSES}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in get_dataclasses: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.post("/data-upload")
async def upload_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Optional[str] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch users data from the database
    user = await db.users.find_one({"email": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is verified
    if not user.get('verified', False):
        raise HTTPException(status_code=403, detail="Only verified users can upload data")

    # Read and process the file
    file_content = await file.read()
    try:
        standard_data = json.loads(file_content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

    # Create upload doc
    upload_doc = {
        "user_id": user['_id'],
        "upload_date": datetime.utcnow(),
        "file_name": file.filename,
        "file_type": 'json',
        "content": standard_data,
        "status": "unverified",
    }

    # Insert into Uploads collection
    upload_result = await db.uploads.insert_one(upload_doc)

    # Update user
    await db.users.update_one(
        {"_id": user['_id']},
        {
            "$push": {
                "uploaded_data": {
                    "upload_id": upload_result.inserted_id,
                    "upload_date": upload_doc["upload_date"],
                    "file_name": file.filename,
                    "file_type": 'json',
                    "processed": False
                }
            }
        }
    )

    # Trigger asynchronous processing
    background_tasks.add_task(process_upload_async, upload_result.inserted_id)

    return {
        "message": "Data uploaded successfully. It will be processed and added to reports as unverified data once reviewed.",
        "upload_id": str(upload_result.inserted_id)
    }

async def transform_to_standard_format(file_content: bytes) -> Dict:
    if not file_content:
        raise ValueError("File content is empty")

    try:
        return json.loads(file_content.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Error transforming file content: {str(e)}")
        raise ValueError(f"Error processing file: {str(e)}")

async def process_upload_async(upload_id: ObjectId):
    try:
        # Retrieve the upload document
        upload_doc = await db.uploads.find_one({"_id": upload_id})
        if not upload_doc:
            raise ValueError(f"Upload with id {upload_id} not found")

        # Process the content (e.g., validate against HIBP data classes)
        processed_content = process_content(upload_doc['content'])

        # Update the upload document with processed content
        await db.uploads.update_one(
            {"_id": upload_id},
            {
                "$set": {
                    "processed_content": processed_content,
                    "processing_completed_at": datetime.utcnow()
                }
            }
        )

        # Update the user's doc
        await db.users.update_one(
            {"_id": upload_doc['user_id']},
            {
                "$set": {
                    "uploaded_data.$[elem].processed": True,
                }
            },
            array_filters=[{"elem.upload_id": upload_id}]
        )

        logger.info(f"Upload {upload_id} processed successfully")

    except Exception as e:
        logger.error(f"Error processing upload {upload_id}: {str(e)}")
        # Update uplooad status to "error" if an exception occurs
        await db.uploads.update_one(
            {"_id": upload_id},
            {
                "$set": {
                    "status": "error",
                    "error_message": str(e)
                }
            }
        )

def process_content(content: Dict) -> Dict:
    processed_content = {}
    for key, value in content.items():
        if key.lower() in [dc.lower() for dc in HIBP_DATA_CLASSES]:
            processed_content[key] = value
    return processed_content

@router.post("/admin/verify-upload/{upload_id}")
async def verify_upload(
    upload_id: str,
    current_user: str = Depends(get_current_user)
):
    if not await is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can verify uploads")

    upload = await db.uploads.find_one({"_id": ObjectId(upload_id)})
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    await db.uploads.update_one(
        {"_id": ObjectId(upload_id)},
        {"$set": {"status": "verified", "verified_at": datetime.utcnow()}}
    )

    # Update user's uploaded_data
    await db.users.update_one(
        {"_id": upload["user_id"]},
        {"$set": {"uploaded_data.$[elem].verified": True}},
        array_filters=[{"elem.upload_id": ObjectId(upload_id)}]
    )

    return {"message": "Upload verified successfully"}

@router.get("/admin/unverified-uploads")
async def get_unverified_uploads(current_user: str = Depends(get_current_user)):
    if not await is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

    unverified_uploads = await db.uploads.find({"status": "unverified"}).to_list(length=100)
    return [
        {
            "id": str(upload["_id"]),
            "user_id": str(upload["user_id"]),
            "file_name": upload["file_name"],
            "upload_date": upload["upload_date"],
            "file_type": upload["file_type"]
        }
        for upload in unverified_uploads
    ]

async def is_admin(user_email: str) -> bool:
    try:
        user = await db.users.find_one({"email": user_email})
        if not user:
            logger.warning(f"User with email {user_email} not found")
            return False
        
        # Check if the user_type is 'admin'
        return user.get('user_type') == 'admin'
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_email}: {str(e)}")
        return False  # Default to non-admin in case of errors
