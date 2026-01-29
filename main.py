import flet as ft
from src.views.login_view import LoginView
from src.views.chat_view import ChatListView

def main(page: ft.Page):
    page.title = "Chat App"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 800

    # Инициализируем сессию как словарь
    page.session["user"] = None

    def on_chat_selected(target_user):
        print(f"Выбран чат с: {target_user['display_name']}")

    def on_login_success(user):
        # Сохраняем пользователя в сессию
        page.session["user"] = user
        show_chat_screen()

    def show_login_screen():
        page.clean()
        page.add(LoginView(page, on_login_success))
        page.update()

    def show_chat_screen():
        # Достаем пользователя из сессии
        user = page.session["user"]
        page.clean()
        
        page.appbar = ft.AppBar(
            title=ft.Text("Messenger"),
            center_title=False,
            bgcolor=ft.colors.SURFACE_VARIANT,
            actions=[ft.IconButton(ft.icons.LOGOUT, on_click=lambda _: show_login_screen())]
        )
        
        page.add(ChatListView(page, user.id, on_chat_selected))
        page.update()

    show_login_screen()

ft.app(target=main)