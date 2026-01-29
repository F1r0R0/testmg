# src/views/login_view.py
import flet as ft
from src.database import auth_login, auth_register

def LoginView(page: ft.Page, on_login_success):
    # Поля ввода
    email_field = ft.TextField(label="Email", border_radius=10)
    password_field = ft.TextField(label="Пароль", password=True, can_reveal_password=True, border_radius=10)
    error_text = ft.Text(color="red", size=12)

    def login_click(e):
        user, err = auth_login(email_field.value, password_field.value)
        if user:
            on_login_success(user) # Вызываем функцию перехода в чат
        else:
            error_text.value = f"Ошибка: {err}"
            page.update()

    # Кнопка входа
    login_btn = ft.ElevatedButton(
        "Войти", 
        on_click=login_click, 
        width=200,
        style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE)
    )

    # Собираем контейнер по центру
    return ft.Container(
        content=ft.Column([
            ft.Icon(ft.icons.LOCK_PERSON_ROUNDED, size=50, color=ft.colors.BLUE_400),
            ft.Text("Добро пожаловать", size=24, weight="bold"),
            email_field,
            password_field,
            error_text,
            login_btn,
            ft.TextButton("Нет аккаунта? Зарегистрироваться (скоро)")
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
        padding=40,
        alignment=ft.alignment.center
    )