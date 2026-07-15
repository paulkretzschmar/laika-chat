from nicegui import ui
from ..utility.api_urls import http_url
from ..utility.authentification import check_login_status
from ..utility.navigation import go_to_login, go_to_home, go_to_chat, go_to_profile
from ..utility.styles import *
import httpx

async def get_chats(user_id: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            response = await client.get(f"{http_url}/user/{user_id}/chats", headers=auth_header)
            if response.status_code == 200:
                data = response.json()
                if data and "chats" in data:
                    return data["chats"]
                else:
                    ui.notify("no json or 'chats' key in response")
                    return []
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
                return []
    except Exception as e:
        ui.notify(f"error: {e}")
        return []

async def try_join_chat(invite_code: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            body = {
                "invite_code": invite_code
            }
            response = await client.patch(f"{http_url}/chat/join", json=body, headers=auth_header)
            if response.status_code == 200:
                await go_to_home()
                ui.notify(response.json()["message"])
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
    except Exception as e:
        ui.notify(f"error: {e}")

async def try_create_chat(chat_name: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            body = {
                "chat_name": chat_name
            }
            response = await client.post(f"{http_url}/chat", json=body, headers=auth_header)
            if response.status_code == 200:
                await go_to_home()
                ui.notify("chat created successfully")
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
    except Exception as e:
        ui.notify(f"error: {e}")

@ui.page("/")
async def home_page():
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
            chats = await get_chats(user_id, token)
            content.clear()
            # build
            with content.classes(sub_container):
                # titel
                ui.label("your chats").classes(title)
                ui.separator()
                # chat-übersicht
                if not chats:
                    ui.label("no chats").classes(subtitle)
                else:
                    for chat in chats:
                        card = ui.card().classes(clickable_card)
                        with card:
                            ui.label(chat["name"]).classes(subtitle)
                        card.on("click", lambda c_id=chat["_id"]: go_to_chat(c_id))
                # pop-up für chat-erstellung
                with ui.dialog() as dialog, ui.card():
                    ui.label("create new chat").classes(subtitle)
                    chat_name_input = ui.input("chat name").classes(text_input)
                    with ui.row().classes(button_row):
                        ui.button("cancel", on_click=dialog.close)
                        async def create_and_close():
                            await try_create_chat(chat_name_input.value, token)
                            dialog.close()
                        ui.button("create", on_click=create_and_close)
                # card für chat-erstellung
                ui.button(
                    "create new chat",
                    on_click=dialog.open
                ).classes(button)
                ui.separator()
                # beitreten
                invite_code = ui.input("invite code").classes(text_input)
                ui.button(
                    "join chat",
                    on_click=lambda: try_join_chat(invite_code.value, token)
                ).classes(button)
                ui.separator()
                # profil aufrufen
                ui.button(
                    "view profile",
                    on_click=go_to_profile
                ).classes(button)
    # localStorage ist nicht direkt erreichbar
    ui.timer(0.2, check_and_redirect, once=True)
