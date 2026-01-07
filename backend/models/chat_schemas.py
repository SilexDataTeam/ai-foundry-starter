"""Pydantic schemas for chat persistence endpoints."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolCallSchema(BaseModel):
    """Schema for tool call data."""

    id: str
    name: str
    args: dict[str, Any]

    class Config:
        from_attributes = True


class MessageSchema(BaseModel):
    """Schema for message data in responses."""

    id: str
    type: str
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    additional_kwargs: Optional[dict[str, Any]] = None
    tool_calls: list[ToolCallSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ChatSchema(BaseModel):
    """Schema for individual chat in response."""

    title: str
    messages: list[MessageSchema]

    class Config:
        from_attributes = True


class ChatsResponse(BaseModel):
    """Response schema for GET /chats."""

    chats: dict[str, ChatSchema]


class ToolCallInput(BaseModel):
    """Input schema for tool call in POST request."""

    id: str
    name: str
    args: dict[str, Any]


class MessageInput(BaseModel):
    """Input schema for message in POST request."""

    id: str
    type: str
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    additional_kwargs: Optional[dict[str, Any]] = None
    tool_calls: list[ToolCallInput] = Field(default_factory=list)


class ChatInput(BaseModel):
    """Input schema for individual chat in POST request."""

    title: str
    messages: list[MessageInput]


class ChatsInput(BaseModel):
    """Request schema for POST /chats."""

    chats: dict[str, ChatInput]


class ConfigResponse(BaseModel):
    """Response schema for GET /config."""

    serviceUrl: str
