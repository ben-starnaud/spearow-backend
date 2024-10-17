
import pytest
from unittest.mock import patch, AsyncMock
from app.models.report import RequestData, UserReport
from app.routes.report_routes import generate_report_on_auth_user
# ------------------------------------------------------------------- Auth users Report-Gen tests --------------------------------------------------------------------------- #

@pytest.mark.asyncio
@patch("app.routes.report_routes.db")
@patch("app.routes.report_routes.httpx.AsyncClient")
@patch("app.routes.report_routes.jwt.decode")
async def test_generate_report_on_auth_user_local_data(mock_jwt_decode, mock_httpx_client, mock_db):
    # Mock data
    mock_jwt_decode.return_value = {"sub": "test@example.com"}
    mock_db.users.find_one = AsyncMock(return_value={"email": "test@example.com", "breaches": "local breach data"})

    data = RequestData(token="fake_token", reportType="user", reportFormat="json", reportCategory="local")

    # Call the function
    result = await generate_report_on_auth_user(data)

    # Assertions
    assert result == "local breach data"
    mock_jwt_decode.assert_called_once_with("fake_token", key=None, algorithms=["HS256"], options={"verify_signature": False})
    mock_db.users.find_one.assert_called_once_with({"email": "test@example.com"})
    mock_httpx_client.assert_not_called()


