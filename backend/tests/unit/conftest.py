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
from typing import Any, Generator
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(autouse=True)
def setup_test_env() -> Generator[Any, Any, Any]:
    """Setup test environment variables"""
    # Set environment variables to match the JWT token claims
    os.environ["KEYCLOAK_URL"] = "http://test-auth:8080"
    os.environ["ISSUER_URL"] = "http://test-auth:8080"
    os.environ["KEYCLOAK_REALM"] = "test-realm"
    os.environ["FRONTEND_KEYCLOAK_CLIENT_ID"] = "ai-foundry-chat-app"
    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["MODEL_GATEWAY_MODEL_ID"] = "test-model-id"
    os.environ["USE_CHAIN"] = "invoice_agent"

    yield
    # Clean up
    for key in [
        "KEYCLOAK_URL",
        "ISSUER_URL",
        "KEYCLOAK_REALM",
        "FRONTEND_KEYCLOAK_CLIENT_ID",
        "OPENAI_API_KEY",
        "MODEL_GATEWAY_MODEL_ID",
    ]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_key_pair() -> tuple[bytes, bytes]:
    # Generate a keypair for RS256
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


@pytest.fixture
def mock_jwt_token(mock_key_pair: tuple[bytes, bytes]) -> str:
    private_key, _ = mock_key_pair
    return jwt.encode(
        {
            "sub": "test_user",
            "preferred_username": "test_user",
            "azp": "ai-foundry-chat-app",
            "aud": "account",
            "iss": "http://test-auth:8080/realms/test-realm",
            "exp": 9999999999,  # Far future expiration
        },
        private_key,
        algorithm="RS256",
    )


@pytest.fixture
def mock_token_verification(
    mock_key_pair: tuple[bytes, bytes],
) -> Generator[Any, Any, Any]:
    _, public_key = mock_key_pair

    async def mock_verify(token: str) -> dict[str, Any]:
        return {
            "sub": "test_user",
            "preferred_username": "test_user",
            "azp": "ai-foundry-chat-app",
            "aud": "account",
            "iss": "http://test-auth:8080/realms/test-realm",
        }

    with (
        patch("backend.main.verify_token", new=mock_verify),
        patch("backend.main.get_public_key", return_value=public_key.decode()),
    ):
        yield


@pytest.fixture
def mock_public_key() -> str:
    return "test_key"
