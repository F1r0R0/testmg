import streamlit as st
from supabase import create_client
import time

# --- 1. ЗАГРУЗКА СЕКРЕТОВ ---
# Streamlit автоматически подтянет их из .streamlit/secrets.toml (локально)
# или из настроек "Secrets" (в облаке)
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

# --- 2. НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Python Messenger", page_icon="💬")
st.title("🔐 Чат с регистрацией")

if "user" not in st.session_state:
    st.session_state.user = None

# --- 3. БЛОК АВТОРИЗАЦИИ ---
if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        pw = st.text_input("Пароль", type="password", key="login_pw")
        if st.button("Войти", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                st.success("Успешный вход!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка входа: {e}")

    with tab2:
        reg_email = st.text_input("Email", key="reg_email")
        reg_pw = st.text_input("Пароль", type="password", key="reg_pw")
        if st.button("Создать аккаунт", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": reg_email, "password": reg_pw})
                st.success("Регистрация успешна! Можно входить.")
            except Exception as e:
                st.error(f"Ошибка регистрации: {e}")
    st.stop() 

# --- 4. ИНТЕРФЕЙС ЧАТА ---
st.sidebar.write(f"Вы вошли как: \n**{st.session_state.user.email}**")
if st.sidebar.button("Выйти"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

def send_message():
    msg_text = st.session_state.new_message_input
    if msg_text.strip():
        supabase.table("messages").insert({
            "username": st.session_state.user.email,
            "content": msg_text
        }).execute()
        st.session_state.new_message_input = ""

st.text_input("Напишите сообщение...", key="new_message_input", on_change=send_message)
st.divider()

# --- 5. ВЫВОД СООБЩЕНИЙ ---
try:
    res = supabase.table("messages").select("*").order("created_at", desc=True).limit(20).execute()
    for m in res.data:
        # Улучшенное отображение: Бабблы
        is_me = m['username'] == st.session_state.user.email
        align = "right" if is_me else "left"
        color = "#e1f5fe" if is_me else "#f0f0f0"
        
        st.markdown(f"""
            <div style="text-align: {align}; margin-bottom: 10px;">
                <div style="display: inline-block; background: {color}; padding: 10px; border-radius: 15px; max-width: 80%; text-align: left;">
                    <small style="color: gray;">{m['username']}</small><br>
                    {m['content']}
                </div>
            </div>
        """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Ошибка: {e}")

# Автообновление
time.sleep(5)
st.rerun()