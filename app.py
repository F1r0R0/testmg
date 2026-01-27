import streamlit as st
from supabase import create_client
import time

# --- ИНИЦИАЛИЗАЦИЯ ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

st.set_page_config(page_title="SkyChat Pro", layout="wide")

# --- СОСТОЯНИЕ ---
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_with_user" not in st.session_state:
    st.session_state.chat_with_user = None

# --- ПОМОЩНИКИ ---
def get_my_profile():
    try:
        res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
        return res.data[0] if res.data else None
    except:
        return None

def get_my_chat_list(my_username):
    try:
        sent = supabase.table("direct_messages").select("recipient_username").eq("sender_username", my_username).execute()
        received = supabase.table("direct_messages").select("sender_username").eq("recipient_username", my_username).execute()
        contacts = set()
        for item in sent.data: contacts.add(item['recipient_username'])
        for item in received.data: contacts.add(item['sender_username'])
        return list(contacts)
    except:
        return []

# --- АВТОРИЗАЦИЯ ---
if st.session_state.user is None:
    st.title("🔐 Вход")
    t1, t2 = st.tabs(["Вход", "Регистрация"])
    with t1:
        e = st.text_input("Email", key="auth_email")
        p = st.text_input("Пароль", type="password", key="auth_pw")
        if st.button("Войти", key="btn_login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                st.session_state.user = res.user
                st.rerun()
            except Exception as ex:
                st.error(f"Ошибка: {ex}")
    with t2:
        re = st.text_input("Email", key="reg_email")
        rp = st.text_input("Пароль", type="password", key="reg_pw")
        if st.button("Создать аккаунт", key="btn_reg"):
            try:
                supabase.auth.sign_up({"email": re, "password": rp})
                st.success("Успешно! Войдите.")
            except Exception as ex:
                st.error(ex)
    st.stop()

# --- ПРОВЕРКА ПРОФИЛЯ ---
my_profile = get_my_profile()
if not my_profile:
    st.title("📝 Создание профиля")
    new_un = st.text_input("Юзернейм", key="init_un").lower().strip()
    new_dn = st.text_input("Имя", key="init_dn")
    if st.button("Начать"):
        try:
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": new_un, "display_name": new_dn}).execute()
            st.rerun()
        except:
            st.error("Юзернейм занят!")
    st.stop()

# --- САЙДБАР ---
with st.sidebar:
    st.title("SkyChat")
    st.write(f"**{my_profile['display_name']}** (@{my_profile['username']})")
    # Используем уникальный ключ для радио-кнопки
    menu = st.radio("Меню", ["Чаты", "Поиск", "Профиль"], key="main_menu")
    if st.button("Выйти", key="btn_logout"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# --- 6. ЛОГИКА СТРАНИЦ (ЧИСТЫЙ ВАРИАНТ) ---

if menu == "Профиль":
    st.header("⚙️ Настройки профиля")
    with st.container():
        new_dn = st.text_input("Имя", value=my_profile['display_name'], key="profile_dn_input")
        new_un = st.text_input("Юзернейм", value=my_profile['username'], key="profile_un_input").lower().strip()
        
        if st.button("Сохранить изменения", key="save_profile_final"):
            try:
                supabase.table("profiles").update({
                    "display_name": new_dn,
                    "username": new_un
                }).eq("id", st.session_state.user.id).execute()
                st.success("Данные успешно обновлены!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                if "duplicate" in str(e).lower():
                    st.error("Этот юзернейм уже занят!")
                else:
                    st.error(f"Ошибка: {e}")

elif menu == "Поиск":
    st.header("🔍 Найти пользователя")
    search_q = st.text_input("Введите @юзернейм", key="search_page_input").replace("@", "").lower().strip()
    if search_q:
        res = supabase.table("profiles").select("*").eq("username", search_q).execute()
        if res.data:
            found = res.data[0]
            if found['username'] != my_profile['username']:
                st.write(f"Найдено: **{found['display_name']}** (@{found['username']})")
                if st.button(f"Начать чат", key=f"btn_start_{found['username']}"):
                    st.session_state.chat_with_user = found
                    st.success("Собеседник выбран! Перейдите во вкладку 'Чаты'")
            else:
                st.info("Это ваш профиль")
        else:
            st.error("Пользователь не найден")

elif menu == "Чаты":
    st.header("💬 Ваши диалоги")
    contacts = get_my_chat_list(my_profile['username'])
    
    col_list, col_chat = st.columns([1, 2.5])
    
    with col_list:
        st.subheader("Список")
        if not contacts:
            st.caption("У вас пока нет активных чатов")
        for c_un in contacts:
            if st.button(f"👤 @{c_un}", key=f"list_contact_{c_un}", use_container_width=True):
                # Обновляем профиль собеседника
                res = supabase.table("profiles").select("*").eq("username", c_un).execute()
                if res.data:
                    st.session_state.chat_with_user = res.data[0]
                    st.rerun()

    with col_chat:
        target = st.session_state.chat_with_user
        if target:
            st.subheader(f"Чат: {target['display_name']}")
            
            # Поле ввода
            def handle_send_msg():
                val = st.session_state.chat_input_val.strip()
                if val:
                    supabase.table("direct_messages").insert({
                        "sender_id": st.session_state.user.id,
                        "sender_username": my_profile['username'],
                        "recipient_username": target['username'],
                        "content": val
                    }).execute()
                    st.session_state.chat_input_val = ""

            st.text_input("Напишите сообщение...", key="chat_input_val", on_change=handle_send_msg)
            st.divider()

            # Вывод сообщений
            try:
                msgs = supabase.table("direct_messages").select("*").or_(
                    f"and(sender_username.eq.{my_profile['username']},recipient_username.eq.{target['username']}),"
                    f"and(sender_username.eq.{target['username']},recipient_username.eq.{my_profile['username']})"
                ).order("created_at", desc=True).limit(40).execute()

                for msg in msgs.data:
                    is_me = msg['sender_username'] == my_profile['username']
                    align = "right" if is_me else "left"
                    bg = "#DCF8C6" if is_me else "#FFFFFF"
                    st.markdown(f"""
                        <div style="text-align: {align}; margin-bottom: 8px;">
                            <div style="display: inline-block; background: {bg}; color: black; padding: 10px 14px; border-radius: 15px; border: 1px solid #ddd; max-width: 80%;">
                                {msg['content']}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            except:
                st.error("Не удалось загрузить сообщения")
        else:
            st.info("Выберите чат из списка слева, чтобы начать переписку")

# Финальный рефреш
time.sleep(5)
st.rerun()