# Copyright 2025 Silex Data Solutions dba Data Science Technologies, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def clear_public_key_cache() -> None:
    from backend.main import _public_key_cache

    _public_key_cache.update({"key": None, "timestamp": 0.0})


@patch("requests.get")
def test_get_public_key_success(mock_get: Any) -> None:
    from backend.main import get_public_key

    mock_response = MagicMock()
    mock_response.json.return_value = {"public_key": "test_key"}
    mock_get.return_value = mock_response
    mock_response.raise_for_status.return_value = None

    result = get_public_key()
    assert "test_key" in result
    mock_get.assert_called_once()
    mock_response.raise_for_status.assert_called_once()


@patch("requests.get")
def test_get_public_key_failure(mock_get: Any) -> None:
    from backend.main import _public_key_cache, get_public_key

    # Ensure cache is empty
    _public_key_cache.update({"key": None, "timestamp": 0.0})

    mock_response = MagicMock()

    def raise_error() -> None:
        raise requests.exceptions.RequestException("Connection error")

    mock_response.raise_for_status.side_effect = raise_error
    mock_get.return_value = mock_response

    with pytest.raises(HTTPException) as exc_info:
        get_public_key()

    assert exc_info.value.status_code == 500
    assert "Failed to fetch public key" in str(exc_info.value.detail)
    mock_get.assert_called_once()


@patch("requests.get")
def test_get_public_key_json_failure(mock_get: Any) -> None:
    from backend.main import _public_key_cache, get_public_key

    # Ensure cache is empty
    _public_key_cache.update({"key": None, "timestamp": 0.0})

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Invalid JSON", "", 0
    )
    mock_get.return_value = mock_response

    with pytest.raises(HTTPException) as exc_info:
        get_public_key()

    assert exc_info.value.status_code == 500
    assert "Failed to fetch public key" in str(exc_info.value.detail)
    mock_get.assert_called_once()
    mock_response.json.assert_called_once()


@pytest.mark.asyncio
async def test_verify_token_expired(mock_jwt_token: str) -> None:
    import jwt

    from backend.main import verify_token

    with patch("jwt.decode") as mock_decode:
        mock_decode.side_effect = jwt.ExpiredSignatureError

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(mock_jwt_token)

        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()
        mock_decode.assert_called()


@pytest.mark.asyncio
async def test_verify_token_invalid_signature(mock_jwt_token: str) -> None:
    import jwt

    from backend.main import verify_token

    with (
        patch("jwt.decode") as mock_decode,
        patch("backend.main.get_public_key", return_value="mock_public_key"),
    ):
        # Mock first decode (unverified) to return valid claims
        mock_decode.side_effect = [
            {
                "aud": "account",
                "azp": "ai-foundry-chat-app",
                "iss": f"{os.getenv('KEYCLOAK_URL')}/realms/{os.getenv('KEYCLOAK_REALM')}",
                "sub": "test_user",
            },
            # Second decode raises InvalidSignatureError
            jwt.InvalidSignatureError("Invalid signature"),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(mock_jwt_token)

        assert exc_info.value.status_code == 401
        assert str(exc_info.value.detail) == "Invalid signature"


@pytest.mark.asyncio
async def test_verify_token_invalid_azp(mock_jwt_token: str) -> None:
    from backend.main import verify_token

    with (
        patch("jwt.decode") as mock_decode,
        patch("backend.main.get_public_key", return_value="mock_public_key"),
    ):
        # Mock only the first decode call since the second one won't happen
        mock_decode.return_value = {
            "aud": "account",
            "azp": "wrong-client-id",
            "iss": f"{os.getenv('KEYCLOAK_URL')}/realms/{os.getenv('KEYCLOAK_REALM')}",
            "sub": "test_user",
        }

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(mock_jwt_token)

        assert exc_info.value.status_code == 401
        assert str(exc_info.value.detail) == "Token verification failed"


@pytest.mark.asyncio
async def test_verify_token_invalid_claims() -> None:
    from backend.main import verify_token

    invalid_token = "invalid.token.format"

    with pytest.raises(HTTPException) as exc_info:
        await verify_token(invalid_token)

    assert exc_info.value.status_code == 401
