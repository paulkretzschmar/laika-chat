from nicegui import ui

# Seiten importieren (ist nicht unused)
from .pages import home, login, profile, chat

# App starten
if __name__ in {"__main__", "__mp_main__"}:
    ui.run()
