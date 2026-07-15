from nicegui import ui
from ..utility.api_urls import http_url
from ..utility.authentification import login_success, register_success, check_login_status
from ..utility.navigation import go_to_home
from ..utility.styles import *
import httpx
import re

async def try_login(username:str, password:str):
    try:
        async with httpx.AsyncClient() as client:
            data = {
                "username": username,
                "password": password
            }
            response = await client.post(f"{http_url}/login", json=data)
            if response.status_code == 200:
                await login_success(response.json()["id"], response.json()["access_token"])
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
    except Exception as e:
        ui.notify(f"error: {e}")

async def try_register(username:str, password:str):
    if not re.match(r'^[A-Za-z0-9]{1,15}$', username):
        ui.notify("username must be between 1 and 15 characters long and only contain letters and numbers")
        return
    if len(password) < 8:
        ui.notify("password must be at least 8 characters long")
        return
    if not re.search(r'[A-Za-z]', password):
        ui.notify("password must contain at least 1 letter")
        return
    if not re.search(r'[0-9]', password):
        ui.notify("password must contain at least 1 number")
        return
    if not re.search(r'[^A-Za-z0-9]', password):
        ui.notify("password must contain at least 1 special character")
        return
    try:
        async with httpx.AsyncClient() as client:
            data = {
                "username": username,
                "password": password
            }
            response = await client.post(f"{http_url}/register", json=data)
            if response.status_code == 200:
                await register_success(response.json()["id"], response.json()["access_token"])
            else:
                error_detail = response.json().get("detail", "unknown")
                ui.notify(f"error {response.status_code}: {error_detail}")
    except Exception as e:
        ui.notify(f"error: {e}")

@ui.page("/login")
async def login_page():
    with ui.column().classes(main_container):
        # temporärer platzhalter
        with ui.column() as content:
            # ladeanzeige während token-überprüfung
            ui.spinner(size="lg")

        async def check_and_redirect():
            # token-überprüfung im browser-storage
            user_id, token = await check_login_status()
            if user_id and token:
                ui.notify("already logged in")
                await go_to_home()
            # pre-build
            content.clear()
            # build
            with content.classes(sub_container):
                # titel
                ui.label("welcome to laika").classes(title)
                ui.separator()
                # login
                ui.label("login").classes(subtitle)
                ui.label("use this, if you already have an account").classes(body_text)
                login_username = ui.input("username").classes(text_input)
                login_password = ui.input("password", password=True).classes(text_input)
                ui.button(
                    "login",
                    on_click=lambda: try_login(login_username.value, login_password.value)
                ).classes(button)
                ui.separator()
                # register
                ui.label("register").classes(subtitle)
                ui.label("use this, if you don't have an account yet").classes(body_text)
                register_username = ui.input("username").classes(text_input)
                register_password = ui.input("password", password=True).classes(text_input)
                ui.button(
                    "register",
                    on_click=lambda: try_register(register_username.value, register_password.value)
                ).classes(button)
    # localStorage ist nicht direkt erreichbar
    ui.timer(0.2, check_and_redirect, once=True)
