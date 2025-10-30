from datetime import datetime


from pydantic import BaseModel, Field, ConfigDict, EmailStr, model_validator


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
    user_id: int | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def _check_target(self) -> "RoomCreateDirect":
        if (self.user_id is None) and (self.email is None):
            raise ValueError("either user_id or email is required")
        if (self.user_id is not None) and (self.email is not None):
            raise ValueError("provide only one of user_id or email")
        return self


class RoomOut(BaseModel):
    id: int
    type: str
    name: str | None = None
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
    name: str | None = None
    peer: PeerOut | None = None
    last_message: MessageOut | None = None
    unread_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoomCreateGroup(BaseModel):
    user_ids: list[int] | None = None
    emails: list[EmailStr] | None = None
    name: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _check_targets(self) -> "RoomCreateGroup":
        if not self.user_ids and not self.emails:
            raise ValueError("user_ids or emails is required")
        return self


class ParticipantsChangeIn(BaseModel):
    user_ids: list[int] | None = None
    emails: list[EmailStr] | None = None