from pydantic import BaseModel, Field
from typing import Optional, List

class Message(BaseModel):
    id: Optional[str] = Field(alias="_id")
    chat_id: str
    sender_id: str
    sender_username: str
    content: str
    timestamp: str

class User(BaseModel):
    id: Optional[str] = Field(alias="_id")
    username: str
    password: str
    chat_ids: List[str] = Field(default_factory=list)

class Chat(BaseModel):
    id: Optional[str] = Field(alias="_id")
    name: str
    invite_code: str
    member_ids: List[str] = Field(default_factory=list)
    message_ids: List[str] = Field(default_factory=list)
