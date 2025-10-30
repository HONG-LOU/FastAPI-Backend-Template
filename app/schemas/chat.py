from datetime import datetime


from pydantic import BaseModel, Field, ConfigDict


class WSMessage(BaseModel):
    type: str


class WSPresence(WSMessage):
    room_id: int
    user_id: int
    status: str


class WSChatMessage(WSMessage):
    id: int
    room_id: int
    sender_id: int
    content: str
    created_at: datetime


class MessageCreate(BaseModel):
    room_id: int
    content: str | None = Field(default=None, max_length=5000)


class MessageOut(BaseModel):
    id: int
    room_id: int
    sender_id: int
    kind: str
    content: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoomCreateDirect(BaseModel):
    user_id: int


class RoomOut(BaseModel):
    id: int
    type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentInitIn(BaseModel):
    filename: str
    content_type: str
    size: int


class AttachmentInitOut(BaseModel):
    attachment_id: int
    upload_url: str


class AttachmentOut(BaseModel):
    id: int
    message_id: int
    filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkReadIn(BaseModel):
    last_read_message_id: int


class UnreadCountOut(BaseModel):
    count: int


class PeerOut(BaseModel):
    id: int
    email: str
    name: str | None = None
    avatar_url: str | None = None


class RoomSummaryOut(BaseModel):
    id: int
    type: str
    peer: PeerOut | None = None
    last_message: MessageOut | None = None
    unread_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)