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

import logging
import os

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("chat_title")

# Initalize model information
MODEL_GATEWAY_BASE_URL = os.getenv("MODEL_GATEWAY_BASE_URL", None)
MODEL_GATEWAY_MODEL_ID = os.getenv("MODEL_GATEWAY_MODEL_ID", None)

if MODEL_GATEWAY_MODEL_ID is None:
    logger.error("MODEL_GATEWAY_MODEL_ID is not set")
    raise Exception("MODEL_GATEWAY_MODEL_ID is not set")

router = APIRouter()

llm = ChatOpenAI(
    model=MODEL_GATEWAY_MODEL_ID,
    base_url=MODEL_GATEWAY_BASE_URL,
    temperature=0.7,
    max_completion_tokens=100,
)
system_prompt = """Generate a short, descriptive title for a chat based on the initial message.
Do not add quotes."""
system_message = SystemMessage(system_prompt)


class ChatTitleRequest(BaseModel):
    initial_message: str = Field(min_length=1)


@router.post("/generate_chat_title")
async def generate_chat_title(request: ChatTitleRequest) -> dict[str, str]:
    logger.info(f"Generating chat title for: {request.initial_message}")
    messages = [system_message, HumanMessage(request.initial_message)]
    try:
        response = str(llm.invoke(messages).content)
    except Exception as e:
        logger.error(f"Error generating chat title: {e}")
        # Raise an HTTP 500 if something goes wrong with the LLM
        raise HTTPException(status_code=500, detail="error")

    logging.info(f'Generated chat title: "{response}" for "{request.initial_message}"')
    return {"title": response}
