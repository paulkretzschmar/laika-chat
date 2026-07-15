from nicegui import ui
from .navigation import go_to_home, go_to_login

async def set_items(user_id: str, token: str):
    await ui.run_javascript(f'localStorage.setItem("access_token", "{token}")')
    await ui.run_javascript(f'localStorage.setItem("user_id", "{user_id}")')

async def remove_items():
    await ui.run_javascript('localStorage.removeItem("access_token")')
    await ui.run_javascript('localStorage.removeItem("user_id")')

async def login_success(user_id: str, token: str):
    await set_items(user_id, token)
    ui.notify("login successful")
    await go_to_home()

async def register_success(user_id: str, token: str):
    await set_items(user_id, token)
    ui.notify("register successful")
    await go_to_home()

async def logout():
    await remove_items()
    ui.notify("logged out")
    await go_to_login()

async def user_deleted():
    await remove_items()
    ui.notify("account deleted")
    await go_to_login()

async def get_user_id():
    user_id = await ui.run_javascript('localStorage.getItem("user_id")')
    return user_id if user_id else None

async def get_token():
    token = await ui.run_javascript('localStorage.getItem("access_token")')
    return token if token else None

async def check_login_status():
    user_id = await get_user_id()
    token = await get_token()
    return user_id, token
