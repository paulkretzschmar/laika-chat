from fastapi import APIRouter, Request, Depends, HTTPException, status
from ..db import repository as repo
from .auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------------------------------------
# testen
# ---------------------------------------------------------------------------------------------------------
@router.get("/test")
async def test():
    return {"message": "api ist erreichbar"}

# ---------------------------------------------------------------------------------------------------------
# login und register
# ---------------------------------------------------------------------------------------------------------
class AuthData(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: Request, login_data: AuthData):
    return await repo.login(request.app.database, login_data.username, login_data.password)

@router.post("/register")
async def register(request: Request, register_data: AuthData):
    return await repo.register(request.app.database, register_data.username, register_data.password)

# ---------------------------------------------------------------------------------------------------------
# profil und home
# ---------------------------------------------------------------------------------------------------------
@router.get("/user/{user_id}")
async def get_user(
        request: Request, user_id: str,
        current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.get_user(request.app.database, user_id)

@router.delete("/user/{user_id}")
async def delete_user(
        request: Request, user_id: str,
        current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.delete_user(request.app.database, user_id)

@router.get("/user/{user_id}/chats")
async def get_user_chats(
        request: Request, user_id: str,
        current_user_id: str = Depends(get_current_user)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.get_user_chats(request.app.database, user_id)

# ---------------------------------------------------------------------------------------------------------
# chatverwaltung
# ---------------------------------------------------------------------------------------------------------
@router.get("/chat/{chat_id}")
async def get_chat(
        request: Request, chat_id: str,
        current_user_id: str = Depends(get_current_user)
):
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.get_chat(request.app.database, chat_id)

class NewChat(BaseModel):
    chat_name: str

@router.post("/chat")
async def create_chat(
        request: Request, new_chat: NewChat,
        current_user_id: str = Depends(get_current_user)
):
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.create_chat(request.app.database, new_chat.chat_name, current_user_id)

class UserJoin(BaseModel):
    invite_code: str

@router.patch("/chat/join")
async def join_chat(
        request: Request, user_join: UserJoin,
        current_user_id: str = Depends(get_current_user)
):
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.join_chat(request.app.database, current_user_id, user_join.invite_code)

@router.patch("/chat/{chat_id}/leave")
async def leave_chat(
        request: Request, chat_id: str,
        current_user_id: str = Depends(get_current_user)
):
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.leave_chat(request.app.database, current_user_id, chat_id)

@router.get("/chat/{chat_id}/user/usernames")
async def get_chat_usernames(
        request: Request, chat_id: str,
        current_user_id: str = Depends(get_current_user)
):
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.get_chat_usernames(request.app.database, chat_id)
# ---------------------------------------------------------------------------------------------------------
# chatten
# ---------------------------------------------------------------------------------------------------------
@router.get("/chat/{chat_id}/messages")
async def get_chat_messages(
        request: Request, chat_id: str,
        current_user_id: str = Depends(get_current_user)
):
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.get_chat_messages(request.app.database, chat_id)

class NewMessage(BaseModel):
    content: str

@router.post("/chat/{chat_id}/message")
async def create_message(
        request: Request, chat_id: str, new_message: NewMessage,
        current_user_id: str = Depends(get_current_user)
):
    if not current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")
    return await repo.check_message(request.app.database, chat_id, current_user_id, new_message.content)
