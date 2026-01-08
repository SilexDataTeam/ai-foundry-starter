"""SQLAlchemy models matching the existing Prisma schema."""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import Base


class Chat(Base):
    """Chat model matching Prisma schema."""

    __tablename__ = "Chat"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(255))
    userId: Mapped[str] = mapped_column(String(255), index=True)
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Message(Base):
    """Message model matching Prisma schema."""

    __tablename__ = "Message"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    additional_kwargs: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    chatId: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("Chat.id", ondelete="CASCADE"),
    )
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        "ToolCall",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ToolCall(Base):
    """ToolCall model matching Prisma schema."""

    __tablename__ = "ToolCall"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    args: Mapped[dict[str, Any]] = mapped_column(JSON)
    messageId: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("Message.id", ondelete="CASCADE"),
    )
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    message: Mapped["Message"] = relationship("Message", back_populates="tool_calls")
