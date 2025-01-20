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

import json
from typing import Any, AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.models.requests import ConversationInputWrapper


@pytest.fixture
def test_client() -> TestClient:
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def valid_conversation_input() -> ConversationInputWrapper:
    from langchain_core.messages import HumanMessage

    from backend.models.requests import ConversationInputWrapper, UserChatMessage

    return ConversationInputWrapper(
        input_data=UserChatMessage(
            messages=[HumanMessage(content="Test message")],
            user_id="test_user",
            session_id="test_session",
        )
    )


async def mock_success_stream() -> AsyncGenerator[Any, Any]:
    events = [
        {"event": "metadata", "data": {"run_id": "test-123"}},
        {"event": "on_tool_start", "data": {"tool": "test_tool"}},
        {"event": "end"},
    ]
    for event in events:
        yield json.dumps(event) + "\n"


async def mock_error_stream() -> AsyncGenerator[Any, Any]:
    yield json.dumps({"event": "error", "data": {"message": "Test error"}}) + "\n"


async def mock_comprehensive_stream() -> AsyncGenerator[Any, Any]:
    events = [
        {"event": "metadata", "data": {"run_id": "test-123"}},
        {
            "event": "on_tool_start",
            "data": {
                "tool": "fetch_invoice_info",
                "input": {"invoice_id": "invoice_001"},
            },
        },
        {
            "event": "on_chat_model_stream",
            "data": {"content": "Checking invoice details..."},
        },
        {
            "event": "on_tool_end",
            "data": {"result": {"status": "Paid", "amount": 1500}},
        },
        {
            "event": "on_chat_model_stream",
            "data": {"content": "The invoice has been paid."},
        },
        {"event": "end"},
    ]
    for event in events:
        yield json.dumps(event) + "\n"


async def mock_malformed_stream() -> AsyncGenerator[Any, Any]:
    events = [
        {"event": "metadata", "data": {"run_id": "test-123"}},
        "malformed data",
        {"event": "end"},
    ]
    for event in events:
        if isinstance(event, dict):
            yield json.dumps(event) + "\n"
        else:
            yield str(event) + "\n"


@pytest.mark.asyncio
async def test_stream_events_success(
    test_client: TestClient,
    mock_token_verification: Any,
    valid_conversation_input: ConversationInputWrapper,
    mock_jwt_token: str,
) -> None:
    with patch(
        "backend.routes.events.stream_conversation_events",
        return_value=mock_success_stream(),
    ):
        response = test_client.post(
            "/stream_events",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
            json=valid_conversation_input.model_dump(),
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        # Remove decode() since lines are already strings
        events = [json.loads(line) for line in response.iter_lines() if line]
        assert len(events) == 3

        # Validate event structure
        assert events[0]["event"] == "metadata"
        assert "run_id" in events[0]["data"]
        assert events[-1]["event"] == "end"


@pytest.mark.asyncio
async def test_stream_events_invalid_input(
    test_client: TestClient, mock_token_verification: Any, mock_jwt_token: str
) -> None:
    invalid_input = {"invalid": "data"}

    response = test_client.post(
        "/stream_events",
        headers={"Authorization": f"Bearer {mock_jwt_token}"},
        json=invalid_input,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stream_events_error(
    test_client: TestClient,
    mock_token_verification: Any,
    valid_conversation_input: ConversationInputWrapper,
    mock_jwt_token: str,
) -> None:
    with patch(
        "backend.routes.events.stream_conversation_events",
        return_value=mock_error_stream(),
    ):
        response = test_client.post(
            "/stream_events",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
            json=valid_conversation_input.model_dump(),
        )

        assert response.status_code == 200
        # Remove decode() since lines are already strings
        events = [json.loads(line) for line in response.iter_lines() if line]
        assert len(events) == 1
        assert events[0]["event"] == "error"
        assert "message" in events[0]["data"]


@pytest.mark.asyncio
async def test_stream_events_no_auth(
    test_client: TestClient, valid_conversation_input: ConversationInputWrapper
) -> None:
    response = test_client.post(
        "/stream_events", json=valid_conversation_input.model_dump()
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stream_events_comprehensive(
    test_client: TestClient,
    mock_token_verification: Any,
    valid_conversation_input: ConversationInputWrapper,
    mock_jwt_token: str,
) -> None:
    with patch(
        "backend.routes.events.stream_conversation_events",
        return_value=mock_comprehensive_stream(),
    ):
        response = test_client.post(
            "/stream_events",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
            json=valid_conversation_input.model_dump(),
        )

        assert response.status_code == 200
        events = [json.loads(line) for line in response.iter_lines() if line]

        # Verify sequence and structure of events
        assert len(events) == 6
        assert events[0]["event"] == "metadata"
        assert events[1]["event"] == "on_tool_start"
        assert events[2]["event"] == "on_chat_model_stream"
        assert events[3]["event"] == "on_tool_end"
        assert events[4]["event"] == "on_chat_model_stream"
        assert events[5]["event"] == "end"

        # Verify tool event structure
        tool_start = events[1]
        assert "tool" in tool_start["data"]
        assert "input" in tool_start["data"]

        # Verify chat stream content
        chat_event = events[2]
        assert "content" in chat_event["data"]


@pytest.mark.asyncio
async def test_stream_events_malformed_data(
    test_client: TestClient,
    mock_token_verification: Any,
    valid_conversation_input: ConversationInputWrapper,
    mock_jwt_token: str,
) -> None:
    with patch(
        "backend.routes.events.stream_conversation_events",
        return_value=mock_malformed_stream(),
    ):
        response = test_client.post(
            "/stream_events",
            headers={"Authorization": f"Bearer {mock_jwt_token}"},
            json=valid_conversation_input.model_dump(),
        )

        assert response.status_code == 200
        events = []
        for line in response.iter_lines():
            try:
                if line:
                    events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        assert len(events) == 2
        assert events[0]["event"] == "metadata"
        assert events[1]["event"] == "end"
