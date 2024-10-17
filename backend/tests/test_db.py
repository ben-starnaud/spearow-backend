import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, CollectionInvalid
from app.db import close_mongo_connection

MONGO_URL = "mongodb+srv://25917021:by3rANvSi3bC8PIw@pwnedproject.yfx9bzf.mongodb.net/"
DB_NAME = "pwned_db"

# ------------------------------------------------------------------- Database Test Functions --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_mongo_connection():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Test connection to the database
    try:
        await client.admin.command('ping')
    except ConnectionFailure:
        pytest.fail("Failed to connect to MongoDB")

    # Test if the collection is created or exists
    collection_names = await db.list_collection_names()
    assert "password_resets" in collection_names, "password_resets collection does not exist"

    # Close the client connection after test
    await close_mongo_connection()


# ------------------------------------------------------------------- OTP Test Functions ------------------------------------------------------------------------------- #


from unittest.mock import patch, AsyncMock
from app.otp_service import generate_otp

@pytest.mark.asyncio
@patch('app.otp_service.get_or_create_secret_key', new_callable=AsyncMock)
@patch('pyotp.TOTP.now', return_value='123456')
async def test_generate_otp(mock_now, mock_get_or_create_secret_key):
    # Arrange
    user_email = "test@example.com"
    mock_get_or_create_secret_key.return_value = "JBSWY3DPEHPK3PXP"  # Example secret key

    # Act
    otp = await generate_otp(user_email)

    # Assert
    mock_get_or_create_secret_key.assert_awaited_once_with(user_email)
    mock_now.assert_called_once()
    assert otp == '123456'

from app.otp_service import get_or_create_secret_key

@pytest.mark.asyncio
@patch('app.otp_service.db')
async def test_get_or_create_secret_key_existing_user(mock_db):
    # Mock the database response for an existing user with a secret key
    mock_db.users.find_one = AsyncMock(return_value={"email": "test@example.com", "secret_key": "existing_secret_key"})
    
    secret_key = await get_or_create_secret_key("test@example.com")
    
    assert secret_key == "existing_secret_key"
    mock_db.users.find_one.assert_awaited_once_with({"email": "test@example.com"})
    mock_db.users.update_one.assert_not_called()

@pytest.mark.asyncio
@patch('app.otp_service.db')
@patch('app.otp_service.pyotp.random_base32', return_value="new_secret_key")
async def test_get_or_create_secret_key_new_user(mock_random_base32, mock_db):
    # Mock the database response for a new user without a secret key
    mock_db.users.find_one = AsyncMock(return_value={"email": "newuser@example.com"})
    mock_db.users.update_one = AsyncMock()

    secret_key = await get_or_create_secret_key("newuser@example.com")
    
    assert secret_key == "new_secret_key"
    mock_db.users.find_one.assert_awaited_once_with({"email": "newuser@example.com"})
    mock_db.users.update_one.assert_awaited_once_with({"email": "newuser@example.com"}, {"$set": {"secret_key": "new_secret_key"}})
    mock_random_base32.assert_called_once()