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

from typing import Annotated, List, Literal, Optional, Union

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field


class UserChatMessage(BaseModel):
    """
    A structure for capturing user chat input.
    """

    messages: List[
        Annotated[
            Union[HumanMessage, AIMessage, ToolMessage], Field(discriminator="type")
        ]
    ] = Field(..., description="Sequence of human/AI/tool messages.")
    user_id: str = ""
    session_id: str = ""


class ConversationInputWrapper(BaseModel):
    """
    A container for user chat input.
    """

    input_data: UserChatMessage


class UserFeedback(BaseModel):
    """
    A structure for capturing user feedback about the conversation.
    """

    score: Union[int] = Field(..., ge=0, le=1, description="Feedback score (0-1)")
    text: Optional[str] = ""
    run_id: str
    log_type: Literal["feedback"] = Field("feedback", pattern="^feedback$")
