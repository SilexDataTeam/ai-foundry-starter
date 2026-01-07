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

"""Chat persistence API routes."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_user_email
from ..database.config import get_db
from ..database.models import Chat, Message, ToolCall
from ..models.chat_schemas import (
    ChatSchema,
    ChatsInput,
    ChatsResponse,
    MessageSchema,
    ToolCallSchema,
)

# Check if auth is disabled
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"

router = APIRouter()
logger = logging.getLogger("chats_routes")


async def get_chats_impl(
    db: AsyncSession,
    user_email: str,
) -> ChatsResponse:
    """Get all chats for the authenticated user."""
    result = await db.execute(
        select(Chat)
        .where(Chat.userId == user_email)
        .options(selectinload(Chat.messages).selectinload(Message.tool_calls))
        .order_by(Chat.updatedAt.desc())
    )
    user_chats = result.scalars().all()

    chats_dict: dict[str, ChatSchema] = {}
    for chat in user_chats:
        messages = [
            MessageSchema(
                id=msg.id,
                type=msg.type,
                content=msg.content,
                name=msg.name,
                tool_call_id=msg.tool_call_id,
                additional_kwargs=msg.additional_kwargs,
                tool_calls=[
                    ToolCallSchema(id=tc.id, name=tc.name, args=tc.args)
                    for tc in msg.tool_calls
                ],
            )
            for msg in chat.messages
        ]
        chats_dict[chat.id] = ChatSchema(title=chat.title, messages=messages)

    return ChatsResponse(chats=chats_dict)


async def save_chats_impl(
    chats_input: ChatsInput,
    db: AsyncSession,
    user_email: str,
) -> dict[str, bool]:
    """Save/upsert chats for the authenticated user."""
    try:
        for chat_id, chat_data in chats_input.chats.items():
            # Check if chat exists
            result = await db.execute(select(Chat).where(Chat.id == chat_id))
            existing_chat = result.scalar_one_or_none()

            if existing_chat:
                existing_chat.title = chat_data.title or "Untitled Chat"
                existing_chat.userId = user_email
                existing_chat.updatedAt = datetime.now(timezone.utc)
            else:
                new_chat = Chat(
                    id=chat_id,
                    title=chat_data.title or "Untitled Chat",
                    userId=user_email,
                )
                db.add(new_chat)

            # Upsert messages
            for msg_data in chat_data.messages:
                result = await db.execute(
                    select(Message).where(Message.id == msg_data.id)
                )
                existing_msg = result.scalar_one_or_none()

                if existing_msg:
                    existing_msg.type = msg_data.type
                    existing_msg.content = msg_data.content
                    existing_msg.name = msg_data.name
                    existing_msg.tool_call_id = msg_data.tool_call_id
                    existing_msg.additional_kwargs = msg_data.additional_kwargs
                    existing_msg.updatedAt = datetime.now(timezone.utc)
                else:
                    new_msg = Message(
                        id=msg_data.id,
                        type=msg_data.type,
                        content=msg_data.content,
                        name=msg_data.name,
                        tool_call_id=msg_data.tool_call_id,
                        additional_kwargs=msg_data.additional_kwargs,
                        chatId=chat_id,
                    )
                    db.add(new_msg)

                # Upsert tool calls
                for tc_data in msg_data.tool_calls:
                    result = await db.execute(
                        select(ToolCall).where(ToolCall.id == tc_data.id)
                    )
                    existing_tc = result.scalar_one_or_none()

                    if existing_tc:
                        existing_tc.name = tc_data.name
                        existing_tc.args = tc_data.args
                        existing_tc.updatedAt = datetime.now(timezone.utc)
                    else:
                        new_tc = ToolCall(
                            id=tc_data.id,
                            name=tc_data.name,
                            args=tc_data.args,
                            messageId=msg_data.id,
                        )
                        db.add(new_tc)

        await db.commit()
        return {"success": True}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error saving chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save chats.",
        )


async def delete_chat_impl(
    chat_id: str,
    db: AsyncSession,
    user_email: str,
) -> dict[str, bool]:
    """Delete a chat and all related messages/tool_calls."""
    # Find the chat
    result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    if chat.userId != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    try:
        # Delete in order: tool_calls -> messages -> chat
        # First get all message IDs for this chat
        messages_result = await db.execute(
            select(Message.id).where(Message.chatId == chat_id)
        )
        message_ids = [row[0] for row in messages_result.all()]

        # Delete tool calls for these messages
        if message_ids:
            await db.execute(
                delete(ToolCall).where(ToolCall.messageId.in_(message_ids))
            )

        # Delete messages
        await db.execute(delete(Message).where(Message.chatId == chat_id))

        # Delete chat
        await db.execute(delete(Chat).where(Chat.id == chat_id))

        await db.commit()
        return {"success": True}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat.",
        )


# Token verification dependency - will be set by main.py
# This allows the routes to be registered with or without auth
_verify_token_dep: Optional[Callable] = None


def set_verify_token_dependency(dep: Optional[Callable]) -> None:
    """Set the token verification dependency from main.py."""
    global _verify_token_dep
    _verify_token_dep = dep


async def get_token_payload(request: Request) -> dict[str, Any]:
    """Get token payload, using the configured dependency or returning anonymous."""
    if DISABLE_AUTH or _verify_token_dep is None:
        return {"email": "anonymous@example.com", "preferred_username": "anonymous"}

    # Get the Authorization header and extract token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = auth_header.split(" ")[1]
    return await _verify_token_dep(token)


@router.get("/chats", response_model=ChatsResponse)
async def get_chats(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChatsResponse:
    """Get all chats for the authenticated user."""
    token_payload = await get_token_payload(request)
    user_email = get_user_email(token_payload)
    return await get_chats_impl(db, user_email)


@router.post("/chats")
async def save_chats(
    chats_input: ChatsInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Save/upsert chats for the authenticated user."""
    token_payload = await get_token_payload(request)
    user_email = get_user_email(token_payload)
    return await save_chats_impl(chats_input, db, user_email)


@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Delete a chat and all related messages/tool_calls."""
    token_payload = await get_token_payload(request)
    user_email = get_user_email(token_payload)
    return await delete_chat_impl(chat_id, db, user_email)
