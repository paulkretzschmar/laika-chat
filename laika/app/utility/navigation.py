from nicegui import ui

async def go_to_home():
    await ui.run_javascript('window.location.href = "/";')

async def go_to_login():
    await ui.run_javascript('window.location.href = "/login";')

async def go_to_profile():
    await ui.run_javascript('window.location.href = "/profile";')

async def go_to_chat(chat_id: str):
    await ui.run_javascript(f'window.location.href = "/chat/{chat_id}";')
