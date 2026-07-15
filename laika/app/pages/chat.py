from nicegui import ui
from ..utility.authentification import check_login_status
from ..utility.navigation import go_to_login, go_to_home
from ..utility.api_urls import http_url, ws_url
from ..utility.styles import *
from datetime import datetime
from openai import OpenAI
import asyncio
import websockets
import httpx
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

active_websockets = {}

async def get_chat(chat_id: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            response = await client.get(f"{http_url}/chat/{chat_id}", headers=auth_header)
            if response.status_code == 200:
                return response.json()
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
                return None
    except Exception as e:
        ui.notify(f"error: {e}")
        return None

async def get_chat_messages(chat_id: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            response = await client.get(f"{http_url}/chat/{chat_id}/messages", headers=auth_header)
            if response.status_code == 200:
                data = response.json()
                if data and "messages" in data:
                    return data["messages"]
                else:
                    ui.notify("no json or 'messages' key in response")
                    return []
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
                return []
    except Exception as e:
        ui.notify(f"error: {e}")
        return []

async def get_chat_usernames(chat_id: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            response = await client.get(f"{http_url}/chat/{chat_id}/user/usernames", headers=auth_header)
            if response.status_code == 200:
                data = response.json()
                if data and "members" in data:
                    return data["members"]
                else:
                    ui.notify("no json or 'members' key in response")
                    return []
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
                return []
    except Exception as e:
        ui.notify(f"error: {e}")
        return []

async def try_leave_chat(chat_id: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            response = await client.patch(f"{http_url}/chat/{chat_id}/leave", headers=auth_header)
            if response.status_code == 200:
                if chat_id in active_websockets:
                    try:
                        await active_websockets[chat_id].close()
                    except Exception as e:
                        logger.warning(f"Error closing websocket for chat {chat_id}: {e}")
                    del active_websockets[chat_id]
                await go_to_home()
                ui.notify(response.json()["message"])
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
    except Exception as e:
        ui.notify(f"error: {e}")

async def send_message(websocket, message_input: ui.input):
    try:
        content = message_input.value.strip()
        if not content:
            return
        if len(content) > 250:
            ui.notify("message too long (max 250 characters)")
            return
        client = OpenAI(
            base_url="https://models.mylab.th-luebeck.dev/v1",
            api_key="-"
        )
        chat_moderation = await asyncio.to_thread(
            client.moderations.create,
            model="omni-moderation-latest",
            input=content
        )
        if chat_moderation.results and chat_moderation.results[0].flagged:
            ui.notify("your message has been rejected because it contains inappropriate content")
            return
        payload = {"content": content}
        await websocket.send(json.dumps(payload))
        message_input.value = ""
    except Exception as e:
        ui.notify(f"error: {e}")

def show_message(msg: dict, user_id: str, container: ui.column):
    sender_id = msg["sender_id"]
    with container:
        if sender_id == "1":
            with ui.row().classes(message_center):
                with ui.column().classes(message_card):
                    ui.label(msg["sender_username"]).classes(sender_text)
                    ui.label(msg["content"]).classes(body_text)
        elif sender_id == user_id:
            with ui.row().classes(message_right):
                with ui.column().classes(message_card):
                    ui.label("you").classes(sender_text)
                    ui.label(msg["content"]).classes(body_text)
        else:
            with ui.row().classes(message_left):
                with ui.column().classes(message_card):
                    ui.label(msg["sender_username"]).classes(sender_text)
                    ui.label(msg["content"]).classes(body_text)

async def websocket_client(chat_id: str, user_id: str, token: str, messages_container: ui.column):
    logger.info(f"ws_url: {ws_url}")
    url = f"{ws_url}/chat/{chat_id}?token={token}"
    try:
        websocket = await websockets.connect(url)
        logger.info(f"websocket connected to {ws_url}")

        async def receive_messages():
            async for message in websocket:
                data = json.loads(message)
                with messages_container:
                    show_message(data, user_id, messages_container)
                    await ui.run_javascript("""
                        const container = document.querySelector('.scroll-container');
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                        }
                    """)
                logger.info(
                    f"received message from {data['sender_username']} ({data['sender_id']}): {data['content']}"
                )

        asyncio.create_task(receive_messages())
        return websocket
    except Exception as e:
        logger.error(f"webSocket connection error: {e}")
        ui.notify("couldn't connect websocket")

async def close_websocket(chat_id: str):
    if chat_id in active_websockets:
        try:
            await active_websockets[chat_id].close()
            del active_websockets[chat_id]
            logger.info(f"websocket closed for chat {chat_id}")
        except Exception as e:
            logger.warning(f"error closing websocket for chat {chat_id}: {e}")

@ui.page("/chat/{chat_id}")
async def chat_page(chat_id: str):
    with (ui.column().classes(main_container)):
        # temporärer platzhalter
        with ui.column() as content:
            # ladeanzeige während token-überprüfung
            ui.spinner(size="lg")

        async def check_and_redirect():
            # token-überprüfung im browser-storage
            user_id, token = await check_login_status()
            if not user_id or not token:
                await go_to_login()
                return
            # pre-build
            chat = await get_chat(chat_id, token)
            usernames = await get_chat_usernames(chat_id, token)
            messages = await get_chat_messages(chat_id, token)
            logger.info(f"{len(messages)} messages")
            messages = sorted(messages, key=lambda m: datetime.fromisoformat(m["timestamp"]))
            content.clear()
            # build
            with content.classes(sub_container):
                # titel
                ui.label(chat["name"]).classes(title)
                ui.separator()
                # pop-up für chat-member
                with ui.dialog() as member_dialog, ui.card():
                    ui.label("chat-members").classes(subtitle)
                    for username in usernames:
                        ui.label(username).classes(body_text)
                    ui.button("close", on_click=member_dialog.close).classes(button)
                # pop-up für invite code
                with ui.dialog() as invite_dialog, ui.card():
                    ui.label("invite code").classes(body_text)
                    ui.label(chat['invite_code']).classes(subtitle)
                    ui.button("close", on_click=invite_dialog.close).classes(button)
                # pop-up für commands
                with ui.dialog() as command_dialog, ui.card():
                    ui.label("commands").classes(subtitle)
                    ui.label(
                        "!laika + your message (your message will answered by our ai-agent)"
                    ).classes(body_text)
                    ui.label(
                        "!joke (a random joke will be posted into the chat)"
                    ).classes(body_text)
                    ui.label(
                        "!joke + specification (posts a joke according to your specification)"
                    ).classes(body_text)
                    ui.button("close", on_click=command_dialog.close).classes(button)
                # chat-verwaltung
                with ui.row().classes(button_row):
                    ui.button(
                        "show members",
                        on_click=member_dialog.open
                    )
                    ui.button(
                        "show invite code",
                        on_click=invite_dialog.open
                    )
                    ui.button(
                        "show commands",
                        on_click=command_dialog.open
                    )
                    ui.button(
                        "leave chat",
                        on_click=lambda: try_leave_chat(chat_id, token)
                    )
                ui.separator()
                # scroll-bereich
                with ui.column().classes(scroll_container) as messages_container:
                    for message in messages:
                        show_message(message, user_id, messages_container)
                    websocket = await websocket_client(chat_id, user_id, token, messages_container)
                    active_websockets[chat_id] = websocket
                ui.separator()
                # container nach unten scrollen
                await ui.run_javascript("""
                    const container = document.querySelector('.scroll-container');
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                """)
                # schreiben
                with ui.row().classes(button_row):
                    message_input = ui.input("type a message...").classes(text_input)
                    ui.button(
                        "send",
                        on_click=lambda: send_message(websocket, message_input)
                    ).classes(button)
    # localStorage ist nicht direkt erreichbar
    ui.timer(0.2, check_and_redirect, once=True)
    ui.context.client.on_disconnect(lambda: asyncio.create_task(close_websocket(chat_id)))
