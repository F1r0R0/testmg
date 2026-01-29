# src/database.py
import os
from supabase import create_client, Client

# --- 1. ЧТЕНИЕ КОНФИГА (TOML) ---
try:
    import tomllib  # Для Python 3.11+
except ImportError:
    import tomli as tomllib  # Для старых версий (pip install tomli)

# Проверяем, существует ли файл
if not os.path.exists("keys.toml"):
    raise FileNotFoundError("Файл keys.toml не найден! Создайте его и добавьте туда url и key.")

with open("keys.toml", "rb") as f:
    config = tomllib.load(f)
    
SUPABASE_URL = config["supabase"]["url"]
SUPABASE_KEY = config["supabase"]["key"]

# --- 2. ИНИЦИАЛИЗАЦИЯ SUPABASE ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 3. ФУНКЦИИ (Очищенные от Streamlit) ---

def get_chat_list_by_id(user_id):
    """Получает список пользователей, с кем есть диалог"""
    try:
        # Находим уникальных собеседников в direct_messages
        # (Эта логика упрощена, в идеале нужен отдельный запрос или view)
        res = supabase.table("direct_messages").select("sender_id, recipient_id")\
            .or_(f"sender_id.eq.{user_id},recipient_id.eq.{user_id}").execute()
        
        ids = set()
        for row in res.data:
            if row['sender_id'] != user_id: ids.add(row['sender_id'])
            if row['recipient_id'] != user_id: ids.add(row['recipient_id'])
            
        if not ids: return []
        
        # Получаем профили этих людей
        users_res = supabase.table("profiles").select("*").in_("id", list(ids)).execute()
        return users_res.data
    except Exception as e:
        print(f"Error getting chats: {e}")
        return []

def toggle_reaction(table_name, msg_id, user_id, emoji):
    """Ставит/убирает реакцию"""
    try:
        res = supabase.table(table_name).select("reactions").eq("id", msg_id).execute()
        if not res.data: return
        
        current_reactions = res.data[0].get('reactions') or {}
        users_list = current_reactions.get(emoji, [])
        
        if user_id in users_list:
            users_list.remove(user_id)
        else:
            users_list.append(user_id)
            
        if not users_list:
            if emoji in current_reactions: del current_reactions[emoji]
        else:
            current_reactions[emoji] = users_list
            
        supabase.table(table_name).update({"reactions": current_reactions}).eq("id", msg_id).execute()
        return True
    except Exception as e:
        print(f"Error reaction: {e}")
        return False

def auth_login(email, password):
    """Вход пользователя"""
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res.user, None
    except Exception as e:
        return None, str(e)

def auth_register(email, password, username, display_name):
    """Регистрация + создание профиля в таблице profiles"""
    try:
        # 1. Регистрация в Auth
        res = supabase.auth.sign_up({"email": email, "password": password})
        user = res.user
        if user:
            # 2. Создаем запись в таблице profiles
            supabase.table("profiles").insert({
                "id": user.id,
                "username": username,
                "display_name": display_name
            }).execute()
        return user, None
    except Exception as e:
        return None, str(e)