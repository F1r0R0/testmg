import streamlit as st
from supabase import create_client
import time

# --- 1. ИНИЦИАЛИЗАЦИЯ И СЕКРЕТЫ ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

st.set_page_config(page_title="SkyChat Pro", layout="wide", page_icon="💬")

if "user" not in st.session_state:
    st.session_state.user = None
if "chat_with_user" not in st.session_state:
    st.session_state.chat_with_user = None

# --- 2. ФУНКЦИИ-ПОМОЩНИКИ (Вынесены вверх) ---

def get_my_profile():
    try:
        res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
        return res.data[0] if res.data else None
    except:
        return None

def get_my_chat_list(my_username):
    try:
        # Находим всех, кому мы писали
        sent = supabase.table("direct_messages").select("recipient_username").eq("sender_username", my_username).execute()
        # Находим всех, кто писал нам
        received = supabase.table("direct_messages").select("sender_username").eq("recipient_username", my_username).execute()
        
        contacts = set()
        if sent.data:
            for item in sent.data: contacts.add(item['recipient_username'])
        if received.data:
            for item in received.data: contacts.add(item['sender_username'])
        
        return list(contacts)
    except Exception as e:
        # Если базы нет или она пуста — просто возвращаем пустой список
        return []

# --- 3. БЛОК АВТОРИЗАЦИИ ---
if st.session_state.user is None:
    st.title("💬 SkyChat: Вход в систему")
    t1, t2 = st.tabs(["Вход", "Регистрация"])
    with t1:
        e = st.text_input("Email", key="l_e")
        p = st.text_input("Пароль", type="password", key="l_p")
        if st.button("Войти", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                st.session_state.user = res.user
                st.rerun()
            except Exception as ex:
                st.error(f"Ошибка: {ex}")
    with t2:
        re = st.text_input("Email", key="r_e")
        rp = st.text_input("Пароль", type="password", key="r_p")
        if st.button("Создать аккаунт", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": re, "password": rp})
                st.success("Регистрация прошла! Теперь войдите во вкладке 'Вход'")
            except Exception as ex:
                st.error(f"Ошибка: {ex}")
    st.stop()

# --- 4. ПРОВЕРКА ПРОФИЛЯ ---
my_profile = get_my_profile()

if not my_profile:
    st.title("📝 Создание профиля")
    new_un = st.text_input("Юзернейм (без @)").lower().strip()
    new_dn = st.text_input("Ваше отображаемое имя")
    if st.button("Сохранить и войти"):
        try:
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": new_un, "display_name": new_dn}).execute()
            st.rerun()
        except:
            st.error("Этот юзернейм уже занят!")
    st.stop()

# --- 5. САЙДБАР ---
with st.sidebar:
    st.title("SkyChat")
    st.subheader(f"👋 {my_profile['display_name']}")
    st.caption(f"@{my_profile['username']}")
    menu = st.radio("Навигация", ["💬 Мои чаты", "🔍 Поиск людей", "⚙️ Профиль"])
    if st.button("Выйти"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.chat_with_user = None
        st.rerun()

# --- 6. ЛОГИКА СТРАНИЦ ---

if menu == "⚙️ Профиль":
    st.header("Настройки профиля")
    new_name = st.text_input("Изменить имя", value=my_profile['display_name'])
    if st.button("Обновить"):
        supabase.table("profiles").update({"display_name": new_name}).eq("id", st.session_state.user.id).execute()
        st.rerun()

elif menu == "🔍 Поиск людей":
    st.header("Найти друга")
    search = st.text_input("Введите @юзернейм").lower().strip().replace("@", "")
    if search:
        res = supabase.table("profiles").select("*").eq("username", search).execute()
        if res.data:
            found = res.data[0]
            st.write(f"### Найдено: {found['display_name']}")
            if st.button(f"Написать @{found['username']}"):
                st.session_state.chat_with_user = found
                st.success("Перейдите в 'Мои чаты'")
        else:
            st.error("Пользователь не найден")

elif menu == "💬 Мои чаты":
    # ВЫЗОВ ФУНКЦИИ
    contacts = get_my_chat_list(my_profile['username'])
    
    col_list, col_chat = st.columns([1, 3])
    
    with col_list:
        st.write("### Чаты")
        if not contacts:
            st.info("Списк пуст")
        for contact_un in contacts:
            if st.button(f"👤 @{contact_un}", key=f"chat_{contact_un}", use_container_width=True):
                res = supabase.table("profiles").select("*").eq("username", contact_un).execute()
                if res.data:
                    st.session_state.chat_with_user = res.data[0]
                    st.rerun()
    
    with col_chat:
        target = st.session_state.chat_with_user
        if not target:
            st.info("Выберите чат")
        else:
            st.write(f"### {target['display_name']}")
            
            def handle_send():
                txt = st.session_state.new_msg.strip()
                if txt:
                    supabase.table("direct_messages").insert({
                        "sender_id": st.session_state.user.id,
                        "sender_username": my_profile['username'],
                        "recipient_username": target['username'],
                        "content": txt
                    }).execute()
                    st.session_state.new_msg = ""

            st.text_input("Сообщение...", key="new_msg", on_change=handle_send)
            
            msgs = supabase.table("direct_messages").select("*")\
                .or_(f"and(sender_username.eq.{my_profile['username']},recipient_username.eq.{target['username']}),and(sender_username.eq.{target['username']},recipient_username.eq.{my_profile['username']})")\
                .order("created_at", desc=True).limit(40).execute()

            for m in msgs.data:
                is_me = m['sender_username'] == my_profile['username']
                align = "right" if is_me else "left"
                bg = "#DCF8C6" if is_me else "#FFFFFF"
                st.markdown(f"""
                    <div style="text-align: {align}; margin-bottom: 8px;">
                        <div style="display: inline-block; background: {bg}; color: black; padding: 10px 14px; border-radius: 15px; border: 1px solid #ddd; max-width: 70%;">
                            {m['content']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

# Автообновление
time.sleep(4)
st.rerun()