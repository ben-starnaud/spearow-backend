import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.routes.login_routes import router
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
app.include_router(router)

# --------------------------------------------------------------------- Login / Sign up / Register Test cases ---------------------------------------------------------------------- #

@pytest.fixture
def client():
    return AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
@patch("app.db.db.users")
async def test_register_user(mock_users, client):
    mock_users.find_one = AsyncMock(return_value=None)
    mock_users.insert_one = AsyncMock(return_value=AsyncMock(inserted_id="mocked_id"))
    
    register_data = {
        "name": "John Doe",
        "email": "johndoe@example.com",
        "password": "password123"
    }

    response = await client.post("/register", json=register_data)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User registered successfully"
    assert "user_id" in data

    mock_users.find_one.assert_called_once_with({"email": register_data["email"]})
    mock_users.insert_one.assert_called_once()

    assert pwd_context.verify(register_data["password"], pwd_context.hash(register_data["password"]))


@pytest.mark.asyncio
@patch("app.db.db.users")
@patch("app.otp_service.generate_otp")
@patch("app.otp_service.send_otp_email")
async def test_login_otp(mock_send_otp_email, mock_generate_otp, mock_users, client):
    user_data = {
        "email": "johndoe@example.com",
        "name": "John Doe",
        "password": pwd_context.hash("password123"),
        "verified": False
    }

    mock_users.find_one = AsyncMock(return_value=user_data)
    mock_users.update_one = AsyncMock()
    mock_generate_otp.return_value = "123456"

    login_data = {
        "email": "johndoe@example.com",
        "password": "password123"
    }

    response = await client.post("/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "OTP sent. Please check your email."


@pytest.mark.asyncio
@patch("app.db.db.users")
@patch("app.otp_service.get_or_create_secret_key")
async def test_login_with_valid_otp(mock_get_or_create_secret_key, mock_users, client):
    user_data = {
        "email": "johndoe@example.com",
        "name": "John Doe",
        "password": pwd_context.hash("password123"),
        "verified": False
    }

    mock_users.find_one = AsyncMock(return_value=user_data)
    mock_users.update_one = AsyncMock()
    mock_get_or_create_secret_key.return_value = "testsecret"

    with patch("pyotp.TOTP.verify", return_value=True):
        login_data = {
            "email": "johndoe@example.com",
            "password": "password123",
            "otp": "123456"
        }

        response = await client.post("/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "OTP is valid. Login successful!"
        assert "token" in data


@pytest.mark.asyncio
@patch("app.db.db.users")
async def test_login_user_not_found(mock_users, client):
    mock_users.find_one = AsyncMock(return_value=None)

    login_data = {
        "email": "notfound@example.com",
        "password": "wrongpassword"
    }

    response = await client.post("/login", json=login_data)

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"

    mock_users.find_one.assert_called_once_with({"email": login_data["email"]})


@pytest.mark.asyncio
@patch("app.db.db.users")
async def test_reset_password_success(mock_users, client):
    user_data = {
        "email": "johndoe@example.com",
        "password": pwd_context.hash("oldpassword")
    }

    mock_users.find_one = AsyncMock(return_value=user_data)
    mock_users.update_one = AsyncMock()

    reset_password_data = {
        "email": "johndoe@example.com",
        "new_password": "newpassword123"
    }

    response = await client.post("/reset-password", json=reset_password_data)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password reset successful"


@pytest.mark.asyncio
@patch("app.db.db.users")
async def test_reset_password_user_not_found(mock_users, client):
    mock_users.find_one = AsyncMock(return_value=None)

    reset_password_data = {
        "email": "notfound@example.com",
        "new_password": "newpassword123"
    }

    response = await client.post("/reset-password", json=reset_password_data)

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"

    mock_users.find_one.assert_called_once_with({"email": reset_password_data["email"]})