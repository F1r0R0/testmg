import streamlit as st
from supabase import create_client

# Настройки подключения (возьми их в панели управления Supabase)
URL = "https://hwfsggjzsujuhlcbvlzr.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh3ZnNnZ2p6c3VqdWhsY2J2bHpyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NDkwODIsImV4cCI6MjA4NTAyNTA4Mn0.2q6_hiXsJitgVWCNkQAszyY0pnOIG_0svxcXlMV3Ey0"
supabase = create_client(URL, KEY)

st.title("💬 Супер-простой чат")

# 1. Инициализация имени в сессии
if "username" not in st.session_state:
    st.session_state.username = ""

# 2. Если имя еще не введено — показываем только поле для ввода имени
if not st.session_state.username:
    name_input = st.text_input("Как тебя зовут?", key="temp_name")
    if st.button("Войти в чат"):
        if name_input:
            st.session_state.username = name_input
            st.rerun() # Перезагружаем, чтобы интерфейс обновился
        else:
            st.warning("Введи хоть что-нибудь!")
    st.stop() # Останавливаем выполнение кода здесь, пока нет имени

# 3. Если имя есть — показываем чат
st.write(f"Ты зашел как: **{st.session_state.username}**")
if st.button("Сменить имя"):
    st.session_state.username = ""
    st.rerun()

def send_message():
    msg = st.session_state.new_message
    if msg:
        # Теперь мы точно берем имя из session_state
        supabase.table("messages").insert({
            "username": st.session_state.username, 
            "content": msg
        }).execute()
        st.session_state.new_message = ""

st.text_input("Напиши сообщение...", key="new_message", on_change=send_message)

# --- Отображение сообщений ---
res = supabase.table("messages").select("*").order("created_at", desc=True).limit(20).execute()
for m in res.data:
    st.markdown(f"**{m['username']}**: {m['content']}")