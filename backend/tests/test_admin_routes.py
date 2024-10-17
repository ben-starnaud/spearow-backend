import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.routes.admin_routes import fetch_user_data
from app.db import db
from jose import jwt
from unittest.mock import patch, AsyncMock

client = TestClient(fetch_user_data)

@pytest.fixture
def mock_request():
    class MockRequest:
        headers = {"Authorization": "Bearer valid_token"}
    return MockRequest()

@pytest.fixture
def mock_invalid_request():
    class MockRequest:
        headers = {"Authorization": "Bearer invalid_token"}
    return MockRequest()

@pytest.fixture
def mock_no_auth_request():
    class MockRequest:
        headers = {}
    return MockRequest()

@pytest.mark.asyncio
async def test_fetch_user_data_no_auth(mock_no_auth_request):
    with pytest.raises(HTTPException) as exc_info:
        await fetch_user_data(mock_no_auth_request)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authorization token not provided"

@pytest.mark.asyncio
@patch("app.routes.admin_routes.jwt.decode")
async def test_fetch_user_data_invalid_token(mock_jwt_decode, mock_invalid_request):
    mock_jwt_decode.side_effect = jwt.JWTError

    with pytest.raises(HTTPException) as exc_info:
        await fetch_user_data(mock_invalid_request)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid token"

