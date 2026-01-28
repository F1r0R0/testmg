# src/database.py
import streamlit as st
from supabase import create_client
from collections import Counter

# Инициализация Supabase
@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        st.error("Ошибка секретов .streamlit/secrets.toml")
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
    try:
        sent = supabase.table("direct_messages").select("recipient_id").eq("sender_id", my_id).execute()
        received = supabase.table("direct_messages").select("sender_id").eq("recipient_id", my_id).execute()
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
        res = supabase.table("direct_messages").select("sender_id").eq("recipient_id", my_id).eq("is_read", False).execute()
        if res.data: return Counter([msg['sender_id'] for msg in res.data])
        return {}
    except: return {}