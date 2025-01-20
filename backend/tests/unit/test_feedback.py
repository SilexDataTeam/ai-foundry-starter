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

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client() -> TestClient:
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def valid_feedback() -> dict[str, Any]:
    return {
        "score": 1,
        "text": "Great response!",
        "run_id": "test-123",
        "log_type": "feedback",
    }


def test_receive_feedback_success(
    test_client: TestClient,
    mock_token_verification: Any,
    mock_jwt_token: str,
    valid_feedback: dict[str, Any],
) -> None:
    response = test_client.post(
        "/feedback",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json=valid_feedback,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def test_receive_feedback_invalid_score(
    test_client: TestClient,
    mock_token_verification: Any,
    mock_jwt_token: str,
    valid_feedback: dict[str, Any],
) -> None:
    invalid_feedback = valid_feedback.copy()
    invalid_feedback["score"] = 2  # Score must be between 0-1

    response = test_client.post(
        "/feedback",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json=invalid_feedback,
    )

    assert response.status_code == 422


def test_receive_feedback_missing_required(
    test_client: TestClient, mock_token_verification: Any, mock_jwt_token: str
) -> None:
    incomplete_feedback = {
        "score": 1  # Missing required fields
    }

    response = test_client.post(
        "/feedback",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json=incomplete_feedback,
    )

    assert response.status_code == 422


def test_receive_feedback_invalid_type(
    test_client: TestClient,
    mock_token_verification: Any,
    mock_jwt_token: str,
    valid_feedback: dict[str, Any],
) -> None:
    invalid_feedback = valid_feedback.copy()
    invalid_feedback["log_type"] = "invalid_type"  # Must be "feedback"

    response = test_client.post(
        "/feedback",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json=invalid_feedback,
    )

    assert response.status_code == 422


def test_receive_feedback_no_auth(
    test_client: TestClient, valid_feedback: dict[str, Any]
) -> None:
    response = test_client.post("/feedback", json=valid_feedback)

    assert response.status_code == 401
