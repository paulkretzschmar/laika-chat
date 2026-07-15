from passlib.context import CryptContext
from fastapi import HTTPException, status
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel
from .models import User, Chat, Message
from ..api.auth import create_access_token
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone
from openai import OpenAI
from typing import cast
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import string
import random
import httpx

# ---------------------------------------------------------------------------------------------------------
# login und register
# ---------------------------------------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def login(db, username, password):
    users = db["users"]
    user = await users.find_one({"username": username})
    if not user or not pwd_context.verify(password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid username or password"
        )
    token = create_access_token({"sub": str(user["_id"])})
    return {"id": str(user["_id"]), "access_token": token}

async def register(db, username, password):
    users = db["users"]
    existing_user = await users.find_one({"username": username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username already exists"
        )
    hashed = pwd_context.hash(password)
    user = User(
        _id=None,
        username=username,
        password=hashed,
        chat_ids=[]
    )
    try:
        user_data = user.model_dump(by_alias=True)
        user_data.pop('_id', None)
        result = await users.insert_one(user_data)
    except DuplicateKeyError:
        # sollte nicht erreichbar sein (nur debugging)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate username"
        )
    user_id = result.inserted_id
    token = create_access_token({"sub": str(user_id)})
    return {"id": str(user_id), "access_token": token}

# ---------------------------------------------------------------------------------------------------------
# profil und home
# ---------------------------------------------------------------------------------------------------------
async def get_user(db, user_id):
    users = db["users"]
    try:
        user = await users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user not found"
            )
        user["_id"] = str(user["_id"])
        return User(**user).model_dump(by_alias=True)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid user_id format"
        )

async def delete_user(db, user_id):
    users = db["users"]
    chats = db["chats"]
    messages = db["messages"]
    try:
        obj_id = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid user_id format"
        )
    await users.delete_one({"_id": obj_id})
    deleted_messages = await messages.find({"sender_id": user_id}).to_list(None)
    deleted_message_ids = [str(msg["_id"]) for msg in deleted_messages]
    await messages.delete_many({"sender_id": user_id})
    user_chats = await chats.find({"member_ids": user_id}).to_list(None)
    for chat in user_chats:
        updated_member_ids = [mid for mid in chat["member_ids"] if mid != user_id]
        updated_message_ids = [
            msg_id for msg_id in chat.get("message_ids", []) if msg_id not in deleted_message_ids
        ]
        if not updated_member_ids:
            await chats.delete_one({"_id": chat["_id"]})
            await messages.delete_many({"chat_id": str(chat["_id"])})
        else:
            await chats.update_one(
                {"_id": chat["_id"]},
                {"$set": {
                    "member_ids": updated_member_ids,
                    "message_ids": updated_message_ids
                }}
            )
    return {"message": "user and all related data deleted"}

class UserChats(BaseModel):
    chats: list[Chat]

async def get_user_chats(db, user_id):
    try:
        chats = db["chats"]
        user = await get_user(db, user_id)
        chat_object_ids = [ObjectId(chat_id) for chat_id in user["chat_ids"]]
        if not chat_object_ids:
            return UserChats(chats=[])
        user_chats = await chats.find(
            {"_id": {"$in": chat_object_ids}}
        ).to_list(None)
        chat_models =[]
        for chat in user_chats:
            chat["_id"] = str(chat["_id"])
            chat_models.append(Chat(**chat).model_dump(by_alias=True))
        return UserChats(chats=chat_models)
    except Exception as e:
        print(f"Error in get_user_chats: {e}")
        return UserChats(chats=[])

# ---------------------------------------------------------------------------------------------------------
# chatverwaltung
# ---------------------------------------------------------------------------------------------------------
async def get_chat(db, chat_id):
    chats = db["chats"]
    chat = await chats.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat not found"
        )
    chat["_id"] = str(chat["_id"])
    return Chat(**chat).model_dump(by_alias=True)

def generate_invite_code(length=8):
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choices(characters, k=length))

async def create_chat(db, chat_name, user_id, max_tries=42):
    chats = db["chats"]
    users = db["users"]
    for _ in range(max_tries):
        chat = Chat(
            _id=None,
            name=chat_name,
            invite_code=generate_invite_code(),
            member_ids=[user_id],
            message_ids=[]
        )
        chat_data = chat.model_dump(by_alias=True)
        chat_data.pop('_id', None)
        try:
            result = await chats.insert_one(chat_data)
            chat_id = str(result.inserted_id)
            await users.update_one(
                {"_id": ObjectId(user_id)},
                {"$push": {"chat_ids": chat_id}}
            )
            return await get_chat(db, chat_id)
        except DuplicateKeyError:
            continue
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="could not generate unique invite code"
    )

async def join_chat(db, user_id, invite_code):
    chats = db["chats"]
    users = db["users"]
    chat = await chats.find_one({"invite_code": invite_code})
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid invite code"
        )
    if user_id in chat["member_ids"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user is already a member of this chat"
        )
    await chats.update_one(
        {"_id": chat["_id"]},
        {"$addToSet": {"member_ids": user_id}}
    )
    await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$addToSet": {"chat_ids": str(chat["_id"])}}
    )
    return {"message": "joined chat successfully"}

async def leave_chat(db, user_id, chat_id):
    chats = db["chats"]
    users = db["users"]
    messages = db["messages"]
    chat = await chats.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat not found"
        )
    if user_id not in chat["member_ids"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user is not a member of this chat"
        )
    user_messages = await messages.find({
        "chat_id": chat_id,
        "sender_id": user_id
    }).to_list(None)
    deleted_message_ids = [str(msg["_id"]) for msg in user_messages]
    await messages.delete_many({
        "chat_id": chat_id,
        "sender_id": user_id
    })
    updated_message_ids = [
        mid for mid in chat.get("message_ids", []) if mid not in deleted_message_ids
    ]
    await chats.update_one(
        {"_id": chat["_id"]},
        {"$set": {
            "member_ids": [uid for uid in chat["member_ids"] if uid != user_id],
            "message_ids": updated_message_ids
        }}
    )
    await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"chat_ids": str(chat["_id"])}}
    )
    return {"message": "left chat successfully"}

class ChatMembersNames(BaseModel):
    members: list[str]

async def get_chat_usernames(db, chat_id):
    try:
        users = db["users"]
        chat = await get_chat(db, chat_id)
        member_object_ids = [ObjectId(user_id) for user_id in chat["member_ids"]]
        if not member_object_ids:
            return ChatMembersNames(members=[])
        members = await users.find(
            {"_id": {"$in": member_object_ids}}
        ).to_list(None)
        usernames = [user["username"] for user in members]
        return ChatMembersNames(members=usernames)
    except Exception as e:
        print(f"Error in get_chat_usernames: {e}")
        return ChatMembersNames(members=[])

# ---------------------------------------------------------------------------------------------------------
# chatten
# ---------------------------------------------------------------------------------------------------------
class ChatMessages(BaseModel):
    messages: list[Message]

async def get_chat_messages(db, chat_id):
    try:
        await get_chat(db, chat_id)
        messages = db["messages"]
        messages_list = await messages.find(
            {"chat_id": chat_id}
        ).to_list(None)
        message_models = []
        for msg in messages_list:
            msg["_id"] = str(msg["_id"])
            message_models.append(Message(**msg).model_dump(by_alias=True))
        return ChatMessages(messages=message_models)
    except Exception as e:
        print(f"Error in get_chat_messages: {e}")
        return ChatMessages(messages=[])

async def get_message(db, message_id):
    messages = db["messages"]
    message = await messages.find_one({"_id": ObjectId(message_id)})
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="message not found"
        )
    message["_id"] = str(message["_id"])
    return Message(**message).model_dump(by_alias=True)

async def create_message(db, chat_id, user_id, content):
    chats = db["chats"]
    messages = db["messages"]
    user = await get_user(db, user_id)
    username = user["username"] if user else "unknown"
    message = Message(
        _id=None,
        chat_id=chat_id,
        sender_id=user_id,
        sender_username=username,
        content=content,
        timestamp=datetime.now(tz=timezone.utc).isoformat()
    )
    message_data = message.model_dump(by_alias=True)
    message_data.pop('_id', None)
    result = await messages.insert_one(message_data)
    message_id = str(result.inserted_id)
    await chats.update_one(
        {"_id": ObjectId(chat_id)},
        {"$push": {"message_ids": message_id}}
    )
    return await get_message(db, message_id)

async def create_laika_message(db, chat_id, content):
    chats = db["chats"]
    messages = db["messages"]
    message = Message(
        _id=None,
        chat_id=chat_id,
        sender_id="1",
        sender_username="laika",
        content=content,
        timestamp=datetime.now(tz=timezone.utc).isoformat()
    )
    message_data = message.model_dump(by_alias=True)
    message_data.pop('_id', None)
    result = await messages.insert_one(message_data)
    message_id = str(result.inserted_id)
    await chats.update_one(
        {"_id": ObjectId(chat_id)},
        {"$push": {"message_ids": message_id}}
    )
    return await get_message(db, message_id)

async def get_random_joke(db, chat_id):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://icanhazdadjoke.com/",
                headers={"Accept": "application/json"}
            )
            if response.status_code == 200:
                joke = response.json().get("joke", "no joke available")
            else:
                joke = "error when fetching joke"
    except Exception as e:
        joke = f"error: {e}"
    return await create_laika_message(db, chat_id, joke)

async def get_specific_joke(db, chat_id, specs):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://icanhazdadjoke.com/search",
                headers={"Accept": "application/json"},
                params={"term": specs},
            )
            if response.status_code == 200:
                data = response.json()
                jokes = data.get("results", [])
                if jokes:
                    joke = jokes[0].get("joke", "no joke available")
                else:
                    joke = f"no joke found for specs: '{specs}'"
            else:
                joke = "error when fetching joke"
    except Exception as e:
        joke = f"error: {e}"
    return await create_laika_message(db, chat_id, joke)

client = OpenAI(
    base_url="https://models.mylab.th-luebeck.dev/v1",
    api_key="-"
)

async def get_ai_answer(db, chat_id, specs):
    try:
        messages = cast(
            list[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam],
            [
                {"role": "system", "content": "Du bist ein hilfreicher Assistent in einem Gruppenchat."},
                {"role": "user", "content": specs},
            ]
        )
        completion = client.chat.completions.create(
            model="llama-3.3-70b",
            messages=messages,
            max_tokens=512,
        )
        ai_text = completion.choices[0].message.content
    except Exception as e:
        ai_text = f"error: {e}"
    return await create_laika_message(db, chat_id, ai_text)

async def check_message(db, chat_id, user_id, message_content):
    messages = []
    user_message = await create_message(db, chat_id, user_id, message_content)
    messages.append(user_message)
    content_lower = message_content.lower().strip()
    if "!" in content_lower:
        if "!laika" in content_lower:
            specs = content_lower.replace("!laika", "").strip()
            ai_message = await get_ai_answer(db, chat_id, specs)
            messages.append(ai_message)
        elif "!joke" in content_lower:
            if len(content_lower) <= 5:
                joke_message = await get_random_joke(db, chat_id)
                messages.append(joke_message)
            else:
                specs = content_lower.replace("!joke", "").strip()
                joke_message = await get_specific_joke(db, chat_id, specs)
                messages.append(joke_message)
    return messages
