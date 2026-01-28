# main.py
import streamlit as st
# Импортируем наши модули
from src.database import supabase, update_heartbeat, get_profile_cached
from src.styles import inject_custom_css
from src.views import page_chats, page_search, page_profile, page_settings

# Настройка страницы
st.set_page_config(page_title="SkyChat", layout="wide", page_icon="✈️", initial_sidebar_state="expanded")

# Инициализация состояния
if "user" not in st.session_state: st.session_state.user = None
if "chat_with_user" not in st.session_state: st.session_state.chat_with_user = None
if "chat_with_group" not in st.session_state: st.session_state.chat_with_group = None
if "edit_msg_id" not in st.session_state: st.session_state.edit_msg_id = None
if "theme" not in st.session_state: st.session_state.theme = "Midnight Blue"
if "search_res" not in st.session_state: st.session_state.search_res = None

# Загрузка CSS
inject_custom_css()

# Логика входа
if not st.session_state.user:
    st.title("✈️ SkyChat")
    t1, t2 = st.tabs(["Вход", "Регистрация"])
    with t1:
        e = st.text_input("Email")
        p = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            try:
                st.session_state.user = supabase.auth.sign_in_with_password({"email": e, "password": p}).user
                st.rerun()
            except Exception as ex: st.error(ex)
    with t2:
        re = st.text_input("Reg Email")
        rp = st.text_input("Reg Pass", type="password")
        if st.button("Создать"):
            try: supabase.auth.sign_up({"email": re, "password": rp}); st.success("Ок! Теперь войдите.")
            except: pass
    st.stop()

# Логика авторизованного пользователя
update_heartbeat(st.session_state.user.id)
my_profile = get_profile_cached(st.session_state.user.id)

if not my_profile:
    st.title("Регистрация")
    with st.form("init"):
        u = st.text_input("Никнейм (англ)").lower().strip()
        n = st.text_input("Имя")
        if st.form_submit_button("Готово"):
            try:
                supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u, "display_name": n}).execute()
                get_profile_cached.clear()
                st.rerun()
            except: st.error("Этот никнейм уже занят!")
    st.stop()

# Сайдбар
with st.sidebar:
    st.header("SkyChat")
    st.write(f"Привет, **{my_profile['display_name']}**")
    menu = st.radio("Навигация", ["Чаты", "Поиск", "Профиль", "Настройки"], label_visibility="collapsed")
    st.divider()
    if st.button("Выйти", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# Роутинг
if menu == "Чаты": page_chats(my_profile)
elif menu == "Поиск": page_search(my_profile)
elif menu == "Профиль": page_profile(my_profile)
elif menu == "Настройки": page_settings(my_profile)