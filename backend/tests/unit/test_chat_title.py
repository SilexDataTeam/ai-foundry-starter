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

from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client() -> TestClient:
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def valid_chat_title_request() -> dict[str, str]:
    return {"initial_message": "What is the weather like today?"}


@pytest.fixture
def mock_llm_response() -> Generator[MagicMock, None, None]:
    with patch("langchain_openai.ChatOpenAI.invoke") as mock_invoke:
        mock_invoke.return_value.content = "Mock Title"
        yield mock_invoke


def test_generate_chat_title_success(
    test_client: TestClient,
    mock_token_verification: Any,
    mock_jwt_token: str,
    valid_chat_title_request: dict[str, str],
    mock_llm_response: Any,
) -> None:
    response = test_client.post(
        "/generate_chat_title",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json=valid_chat_title_request,
    )

    assert response.status_code == 200
    assert "title" in response.json()
    assert isinstance(response.json()["title"], str)
    assert len(response.json()["title"]) > 0


def test_generate_chat_title_missing_message(
    test_client: TestClient, mock_token_verification: Any, mock_jwt_token: str
) -> None:
    response = test_client.post(
        "/generate_chat_title",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json={},
    )

    assert response.status_code == 422


def test_generate_chat_title_no_auth(
    test_client: TestClient, valid_chat_title_request: dict[str, str]
) -> None:
    response = test_client.post("/generate_chat_title", json=valid_chat_title_request)

    assert response.status_code == 401


def test_generate_chat_title_llm_error(
    test_client: TestClient,
    mock_token_verification: Any,
    mock_jwt_token: str,
    valid_chat_title_request: dict[str, str],
) -> None:
    with patch("langchain_openai.ChatOpenAI.invoke") as mock_invoke:
        mock_invoke.side_effect = Exception("LLM Error")

        response = test_client.post(
            "/generate_chat_title",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
            json=valid_chat_title_request,
        )

        assert response.status_code == 500
        assert "detail" in response.json()
        assert response.json()["detail"] == "error"


def test_generate_chat_title_empty_message(
    test_client: TestClient, mock_token_verification: Any, mock_jwt_token: str
) -> None:
    with patch("langchain_openai.ChatOpenAI.invoke") as mock_invoke:
        # Just to prevent real calls
        mock_invoke.return_value.content = "Mock Title"

        response = test_client.post(
            "/generate_chat_title",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
            json={"initial_message": ""},
        )

        assert response.status_code == 422


def test_generate_chat_title_response_format(
    test_client: TestClient,
    mock_token_verification: Any,
    mock_jwt_token: str,
    valid_chat_title_request: dict[str, str],
    mock_llm_response: Any,
) -> None:
    response = test_client.post(
        "/generate_chat_title",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json=valid_chat_title_request,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "title" in data
    assert isinstance(data["title"], str)
    assert len(data["title"]) > 0
