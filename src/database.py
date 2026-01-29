# src/database.py
import streamlit as st
from supabase import create_client
from collections import Counter

@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Настройте .streamlit/secrets.toml")
        st.stop()

supabase = get_supabase()

# --- ФУНКЦИИ ---

@st.cache_data(ttl=60)
def get_profile_cached(user_id):
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None
    except: return None

def update_heartbeat(user_id):
    try: supabase.table("profiles").update({"last_seen": "now()"}).eq("id", user_id).execute()
    except: pass

def get_chat_list_by_id(my_id):
    """
    Загружает список чатов, исключая те, которые пользователь удалил.
    """
    try:
        # Ищем сообщения, где я отправитель И они мне видны
        sent = supabase.table("direct_messages").select("recipient_id")\
            .eq("sender_id", my_id).eq("visible_to_sender", True).execute()
            
        # Ищем сообщения, где я получатель И они мне видны
        received = supabase.table("direct_messages").select("sender_id")\
            .eq("recipient_id", my_id).eq("visible_to_recipient", True).execute()
            
        ids = set()
        for x in sent.data: 
            if x['recipient_id']: ids.add(x['recipient_id'])
        for x in received.data: 
            if x['sender_id']: ids.add(x['sender_id'])
            
        if not ids: return []
        profiles = supabase.table("profiles").select("*").in_("id", list(ids)).execute()
        return profiles.data
    except: return []

def get_groups_by_id(my_id):
    try:
        m = supabase.table("group_members").select("group_id").eq("user_id", my_id).execute()
        if not m.data: return []
        ids = [x['group_id'] for x in m.data]
        return supabase.table("groups").select("*").in_("id", ids).execute().data
    except: return []

def get_unread_counts(my_id):
    try:
        # Считаем только видимые непрочитанные
        res = supabase.table("direct_messages").select("sender_id")\
            .eq("recipient_id", my_id)\
            .eq("is_read", False)\
            .eq("visible_to_recipient", True).execute() # Важно: только если сообщение не удалено
        if res.data: return Counter([msg['sender_id'] for msg in res.data])
        return {}
    except: return {}
    # ... (предыдущий код в src/database.py) ...

def toggle_reaction(table_name, msg_id, user_id, emoji):
    """
    Ставит или снимает реакцию.
    Логика: Если этот юзер уже ставил этот смайл -> убрать. Если нет -> добавить.
    """
    try:
        # 1. Получаем текущие реакции
        res = supabase.table(table_name).select("reactions").eq("id", msg_id).execute()
        if not res.data: return
        
        current_reactions = res.data[0].get('reactions') or {}
        
        # 2. Обновляем список пользователей для этого смайла
        users_list = current_reactions.get(emoji, [])
        
        if user_id in users_list:
            users_list.remove(user_id) # Убираем лайк
        else:
            users_list.append(user_id) # Ставим лайк
            
        # Если список пуст, удаляем ключ смайла, иначе сохраняем
        if not users_list:
            if emoji in current_reactions:
                del current_reactions[emoji]
        else:
            current_reactions[emoji] = users_list
            
        # 3. Записываем обратно в базу
        supabase.table(table_name).update({"reactions": current_reactions}).eq("id", msg_id).execute()
        return True
    except Exception as e:
        print(f"Error reaction: {e}")
        return False