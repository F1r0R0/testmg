# src/views/chat_view.py
import flet as ft
from src.database import get_chat_list_by_id

def ChatListView(page: ft.Page, my_id, on_chat_selected):
    # 1. Получаем данные из базы
    chats = get_chat_list_by_id(my_id)
    
    # 2. Функция для создания строки чата (нативного элемента)
    def create_chat_item(chat_user):
        # Генерируем цвет для аватарки (как делали раньше)
        name = chat_user.get('display_name', 'User')
        
        return ft.ListTile(
            leading=ft.CircleAvatar(
                content=ft.Text(name[0].upper()),
                # Если будет URL аватарки, добавим: foreground_image_url=chat_user.get('avatar_url')
            ),
            title=ft.Text(name),
            subtitle=ft.Text(f"@{chat_user.get('username', 'id')}", size=12, color=ft.colors.WHITE54),
            on_click=lambda _: on_chat_selected(chat_user)
        )

    # 3. Список (ListView)
    list_items = []
    if not chats:
        list_items = [ft.Text("У вас пока нет активных диалогов", text_align="center")]
    else:
        for u in chats:
            list_items.append(create_chat_item(u))

    return ft.Column([
        ft.Padding(content=ft.Text("Сообщения", size=20, weight="bold"), padding=ft.padding.only(left=10, top=10)),
        ft.Divider(),
        ft.ListView(
            controls=list_items,
            expand=True,
            spacing=5
        )
    ], expand=True)