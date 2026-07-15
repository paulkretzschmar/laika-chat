from nicegui import ui
from ..utility.api_urls import http_url
from ..utility.authentification import check_login_status, logout, user_deleted
from ..utility.navigation import go_to_login, go_to_home
from ..utility.styles import *
import httpx

async def get_user(user_id: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            response = await client.get(f"{http_url}/user/{user_id}", headers=auth_header)
            if response.status_code == 200:
                return response.json()
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
                return None
    except Exception as e:
        ui.notify(f"error: {e}")
        return None

async def delete_user(user_id: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            auth_header = {
                "Authorization": f"Bearer {token}"
            }
            response = await client.delete(f"{http_url}/user/{user_id}", headers=auth_header)
            if response.status_code == 200:
                await user_deleted()
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
    except Exception as e:
        ui.notify(f"error: {e}")

@ui.page("/profile")
async def profile_page():
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
            user = await get_user(user_id, token)
            username = user["username"] if user else "unknown user"
            content.clear()
            # build
            with content.classes(sub_container):
                # titel
                ui.label("your profile").classes(title)
                ui.separator()
                # username
                ui.label(f"username: {username}").classes(body_text)
                ui.separator()
                # logout
                ui.button(
                    "logout",
                    on_click=logout
                ).classes(button)
                ui.separator()
                # account löschen
                ui.button(
                    "delete account",
                    on_click=lambda: delete_user(user_id, token)
                ).classes(button)
                ui.label(
                    "this action will delete your account and all related data, and is irreversible"
                ).classes(body_text)
        # localStorage ist nicht direkt erreichbar
        ui.timer(0.2, check_and_redirect, once=True)
