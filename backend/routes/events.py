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

import importlib
import json
import logging
import os
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from traceloop.sdk import Traceloop

from backend.common.serialization import custom_default
from backend.models.requests import ConversationInputWrapper

router = APIRouter()

logger = logging.getLogger("events_routes")

chain_map = {
    "invoice_agent": "backend.patterns.invoice_agent.chain",
    "basic_rag_qa": "backend.patterns.basic_rag_qa.chain",
    "advanced_rag_qa": "backend.patterns.advanced_rag_qa.chain",
    "agentic_rag": "backend.patterns.agentic_rag.chain",
}

USE_CHAIN = os.getenv("USE_CHAIN")

if not USE_CHAIN:
    logger.error("USE_CHAIN is not set")
    raise Exception("USE_CHAIN is not set")

if USE_CHAIN not in chain_map:
    logger.error(f"Invalid chain: {USE_CHAIN}")
    raise Exception(f"Invalid chain: {USE_CHAIN}")

chain_module_name = chain_map[USE_CHAIN]
chain = importlib.import_module(chain_module_name).chain

EVENTS = [
    "on_tool_start",
    "on_tool_end",
    "on_retriever_start",
    "on_retriever_end",
    "on_chat_model_stream",
]


async def stream_conversation_events(
    input_data: dict[str, str],
) -> AsyncGenerator[str, None]:
    """
    This async generator streams conversation-related events one at a time.
    """

    session_identifier = str(uuid.uuid4())

    # Attach metadata to the tracing session
    Traceloop.set_association_properties(
        {
            "run_id": session_identifier,
            "user_id": input_data.get("user_id", ""),
            "session_id": input_data.get("session_id", ""),
            "revision_id": os.getenv("COMMIT_SHA", "None"),
            "log_type": "tracing",
        }
    )

    # Yield initial metadata event
    initial_event = {"event": "metadata", "data": {"run_id": session_identifier}}
    logger.debug(f"Starting event stream for session {session_identifier}")
    yield json.dumps(initial_event, default=custom_default) + "\n"

    # Stream events from the chain but only stream events that are tagged.
    # The chain, itself, must specify which events should be streamed by tagging.
    # This allows intermediate messages to be hidden from the user if desired.
    async for event in chain.astream_events(
        input_data, version="v2", include_tags=["include"]
    ):
        if event["event"] in EVENTS:
            logger.debug(
                f"Event: {json.dumps(event, default=custom_default, indent=2)}"
            )
            yield json.dumps(event, default=custom_default) + "\n"

    # Final "end" event
    logger.debug(f"Ending event stream for session {session_identifier}")
    yield json.dumps({"event": "end"}, default=custom_default) + "\n"


@router.post("/stream_events")
async def initiate_stream(req_payload: ConversationInputWrapper) -> StreamingResponse:
    """
    Initiate a streaming response of events for a given conversation input.
    """
    try:
        logger.debug(
            f"Received conversation input: {json.dumps(req_payload, default=custom_default, indent=2)}"
        )
        return StreamingResponse(
            stream_conversation_events(req_payload.input_data.model_dump()),
            media_type="text/event-stream",
        )
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise
