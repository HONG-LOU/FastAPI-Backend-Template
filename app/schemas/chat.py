from datetime import datetime


from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}


class RoomCreateDirect(BaseModel):
    user_id: int


class RoomOut(BaseModel):
    id: int
    type: str
    created_at: datetime

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


class MarkReadIn(BaseModel):
    last_read_message_id: int


class UnreadCountOut(BaseModel):
    count: int
