import flet as ft
from supabase import create_client, Client
import os
import shutil
import tempfile
import time

# --- НАСТРОЙКА КЛЮЧЕЙ (УНИВЕРСАЛЬНАЯ) ---
# 1. Сначала пробуем взять из переменных окружения (для Render)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# 2. Если их нет, пробуем найти файл keys.toml (для локального запуска)
if not SUPABASE_URL:
    try:
        import tomli
        with open("keys.toml", "rb") as f:
            config = tomli.load(f)
        SUPABASE_URL = config["supabase"]["url"]
        SUPABASE_KEY = config["supabase"]["key"]
    except Exception:
        pass

# 3. Если ключей всё равно нет — ошибка
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Не найдены ключи Supabase! Настройте Environment Variables или файл keys.toml")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

AVATAR_COLORS = ["red", "blue", "green", "orange", "purple", "brown", "teal"]

def main(page: ft.Page):
    page.title = "Flet Messenger"
    page.theme_mode = ft.ThemeMode.DARK
    
    # --- НАСТРОЙКА ПАПКИ ЗАГРУЗОК ---
    # Создаем временную папку в системе (/tmp/...), куда Flet будет складывать файлы
    temp_upload_dir = tempfile.mkdtemp(prefix="flet_upload_")
    page.upload_dir = temp_upload_dir

    # --- УТИЛИТЫ ---
    def show_snack(message, color="red"):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    def get_avatar_control(url, name, radius=20):
        if url:
            return ft.CircleAvatar(radius=radius, foreground_image_src=url, content=None)
        else:
            color_index = len(name) % len(AVATAR_COLORS)
            return ft.CircleAvatar(radius=radius, bgcolor=AVATAR_COLORS[color_index], 
                                   content=ft.Text(name[0].upper() if name else "?", size=radius, weight="bold", color="white"))

    # --- ВХОД ---
    def show_login_screen():
        page.clean()
        email_input = ft.TextField(label="Email", width=300)
        pass_input = ft.TextField(label="Пароль", width=300, password=True)
        
        def handle_auth(e):
            if not email_input.value or not pass_input.value: return
            try:
                r = supabase.auth.sign_in_with_password({"email": email_input.value, "password": pass_input.value})
                go_to_app_screen(r.user.id)
            except Exception as ex:
                show_snack(f"Ошибка: {ex}")

        page.add(ft.Column([ft.Text("Вход", size=30), email_input, pass_input, ft.ElevatedButton("Войти", on_click=handle_auth)], alignment="center", horizontal_alignment="center"))

    # --- ГЛАВНЫЙ ЭКРАН ---
    def go_to_app_screen(user_id):
        page.clean()

        # --- ОТПРАВКА В БАЗУ ---
        def send_to_db(filepath, original_name):
            try:
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                
                ext = original_name.split('.')[-1]
                safe_name = f"avatar_{int(time.time())}.{ext}"
                storage_path = f"{user_id}/{safe_name}"

                supabase.storage.from_("avatars").upload(
                    path=storage_path, 
                    file=file_bytes, 
                    file_options={"upsert": "true", "content-type": f"image/{ext}"}
                )

                public_url = supabase.storage.from_("avatars").get_public_url(storage_path)
                supabase.table("profiles").update({"avatar_url": public_url}).eq("id", user_id).execute()
                
                show_snack("✅ Аватар обновлен!", "green")
                
                # Удаляем файл
                try: os.remove(filepath)
                except: pass
                
                navigate_to_profile()

            except Exception as e:
                show_snack(f"Ошибка: {e}")

        # --- ОБРАБОТЧИК ЗАГРУЗКИ ---
        def on_upload_complete(e: ft.FilePickerUploadEvent):
            # Ищем файл в нашей временной папке
            target_path = os.path.join(temp_upload_dir, e.file_name)
            
            if os.path.exists(target_path):
                send_to_db(target_path, e.file_name)
            else:
                # Если имя исказилось, ищем любой файл в папке
                files = os.listdir(temp_upload_dir)
                if files:
                    found_path = os.path.join(temp_upload_dir, files[0])
                    send_to_db(found_path, e.file_name)
                else:
                    show_snack("Ошибка загрузки файла", "red")

        def on_file_picked(e: ft.FilePickerResultEvent):
            if e.files:
                file_obj = e.files[0]
                # В веб-версии path всегда None, поэтому всегда вызываем upload
                if file_obj.path:
                    send_to_db(file_obj.path, file_obj.name)
                else:
                    file_picker.upload(e.files)

        file_picker = ft.FilePicker(on_result=on_file_picked, on_upload=on_upload_complete)
        page.overlay.append(file_picker)
        page.update()

        # --- ИНТЕРФЕЙС ПРОФИЛЯ ---
        profile_col = ft.Column(horizontal_alignment="center")

        def navigate_to_profile():
            profile_col.controls.clear()
            try:
                user = supabase.table("profiles").select("*").eq("id", user_id).single().execute().data
                raw_url = user.get("avatar_url", "")
                url = f"{raw_url}?v={int(time.time())}" if raw_url else ""
                name = user.get("display_name", "User")
                
                profile_col.controls.append(ft.Container(height=20))
                profile_col.controls.append(get_avatar_control(url, name, radius=80))
                profile_col.controls.append(ft.Container(height=20))
                profile_col.controls.append(ft.Text(name, size=20, weight="bold"))
                profile_col.controls.append(ft.Container(height=20))
                
                btn = ft.ElevatedButton("Загрузить фото", icon="upload", 
                                      on_click=lambda _: file_picker.pick_files(allow_multiple=False))
                profile_col.controls.append(btn)
                page.update()
            except Exception as e:
                profile_col.controls.append(ft.Text(f"Error: {e}"))
                page.update()

        page.add(ft.AppBar(title=ft.Text("Мой Мессенджер"), bgcolor="#202020"), profile_col)
        navigate_to_profile()
        
    # Очистка при выходе
    import atexit
    atexit.register(lambda: shutil.rmtree(temp_upload_dir, ignore_errors=True))

    if __name__ == "__main__":
    # Получаем порт, который выдал Render (или 8000 для теста на ПК)
     port = int(os.environ.get("PORT", 8000))
    
    # Запускаем приложение напрямую
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER, # Говорим, что это Веб
        port=port,                   # Порт от Render
        host="0.0.0.0"               # Слушаем все IP (обязательно для Render)
    )

ft.app(target=main)