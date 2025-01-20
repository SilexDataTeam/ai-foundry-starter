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

import uuid
from typing import Any, Literal

from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel, Field


class BaseStreamingEvent(BaseModel):
    """
    Base class for streaming events.
    """

    class Config:
        extra = "allow"


class StartToolEvent(BaseStreamingEvent):
    """
    Event to signal the start of a tool.
    """

    event: Literal["on_tool_start"] = "on_tool_start"
    input: dict[str, Any] = {}
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class CompleteToolEvent(BaseStreamingEvent):
    """
    Event to signal the completion of a tool.
    """

    event: Literal["on_tool_end"] = "on_tool_end"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: dict[str, Any]


class ChatStreamEvent(BaseStreamingEvent):
    """
    Event to stream a chat message.
    """

    event: Literal["on_chat_model_stream"] = "on_chat_model_stream"
    data: dict[str, AIMessageChunk]


class GenericEvent(BaseModel):
    """
    A generic event.
    """

    event: str = "data"
    data: dict[str, Any]


class EndOfStreamEvent(BaseModel):
    """
    Event to signal the end of the event stream.
    """

    event: Literal["end"] = "end"
