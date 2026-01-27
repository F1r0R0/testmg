import streamlit as st
from supabase import create_client
import time

# --- 1. НАСТРОЙКИ ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Не настроены секреты (.streamlit/secrets.toml)")
    st.stop()

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

st.set_page_config(page_title="SkyChat Pro", layout="wide", page_icon="💬")

# --- 2. ПЕРЕМЕННЫЕ (SESSION STATE) ---
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_with_user" not in st.session_state:
    st.session_state.chat_with_user = None

# --- 3. ФУНКЦИИ ---
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
        
        if st.session_state.chat_with_user:
             contacts.add(st.session_state.chat_with_user['username'])
             
        return list(contacts)
    except:
        return []

# ==========================================
# ЧАСТЬ 1: ВХОД / РЕГИСТРАЦИЯ
# ==========================================
if st.session_state.user is None:
    login_placeholder = st.empty() # Изолированный контейнер для входа
    
    with login_placeholder.container():
        st.title("🔐 SkyChat: Вход")
        t1, t2 = st.tabs(["Вход", "Регистрация"])
        
        with t1:
            e = st.text_input("Email", key="auth_email")
            p = st.text_input("Пароль", type="password", key="auth_pw")
            if st.button("Войти", key="btn_login"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user = res.user
                    login_placeholder.empty() # Удаляем форму входа
                    st.rerun()
                except Exception as ex:
                    st.error(f"Ошибка: {ex}")

        with t2:
            re = st.text_input("Email", key="reg_email")
            rp = st.text_input("Пароль", type="password", key="reg_pw")
            if st.button("Создать аккаунт", key="btn_reg"):
                try:
                    supabase.auth.sign_up({"email": re, "password": rp})
                    st.success("Аккаунт создан! Войдите.")
                except Exception as ex:
                    st.error(f"Ошибка: {ex}")
    st.stop()

# ==========================================
# ЧАСТЬ 2: ПРИЛОЖЕНИЕ
# ==========================================

# Проверка профиля (если нет - создаем)
my_profile = get_my_profile()
if not my_profile:
    st.title("📝 Ваш профиль")
    with st.form("init_profile"):
        new_un = st.text_input("Юзернейм (например: neo)", key="new_un_init").lower().strip()
        new_dn = st.text_input("Ваше имя", key="new_dn_init")
        if st.form_submit_button("Сохранить"):
            try:
                supabase.table("profiles").insert({
                    "id": st.session_state.user.id, 
                    "username": new_un, 
                    "display_name": new_dn
                }).execute()
                st.rerun()
            except:
                st.error("Юзернейм занят!")
    st.stop()

# --- САЙДБАР ---
with st.sidebar:
    st.title("SkyChat")
    st.write(f"Вы: **{my_profile['display_name']}**")
    st.caption(f"@{my_profile['username']}")
    
    menu = st.radio("Навигация", ["Чаты", "Поиск", "Профиль"], key="nav_radio")
    
    st.divider()
    if st.button("Выйти", key="logout_btn"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.chat_with_user = None
        st.rerun()

# --- ГЛАВНЫЙ ЭКРАН (С ОЧИСТКОЙ) ---
main_placeholder = st.empty() # Главный "очиститель"

with main_placeholder.container():

    # 1. ПРОФИЛЬ
    if menu == "Профиль":
        st.header("⚙️ Настройки")
        # Форма изолирует состояние кнопок
        with st.form("edit_profile_form"):
            new_dn = st.text_input("Имя", value=my_profile['display_name'])
            new_un = st.text_input("Юзернейм", value=my_profile['username']).lower().strip()
            
            # Кнопка внутри формы
            submitted = st.form_submit_button("Сохранить изменения")
            
            if submitted:
                try:
                    supabase.table("profiles").update({
                        "display_name": new_dn,
                        "username": new_un
                    }).eq("id", st.session_state.user.id).execute()
                    
                    # Используем toast вместо success+sleep, чтобы не было фризов
                    st.toast("✅ Профиль успешно обновлен!", icon="🎉")
                    # Быстрый перезапуск без задержки
                    st.rerun()
                except Exception as e:
                    st.error("Ошибка: скорее всего юзернейм занят.")

    # 2. ПОИСК
    elif menu == "Поиск":
        st.header("🔍 Поиск людей")
        
        with st.form("search_form"):
            q = st.text_input("Введите юзернейм", key="search_input").lower().strip()
            search_btn = st.form_submit_button("Найти")
        
        if search_btn and q:
            res = supabase.table("profiles").select("*").eq("username", q).execute()
            if res.data:
                st.session_state['search_res'] = res.data[0]
            else:
                st.session_state['search_res'] = None
                st.error("Пользователь не найден")
        
        # Результат поиска (рисуем вне формы)
        if 'search_res' in st.session_state and st.session_state['search_res']:
            found = st.session_state['search_res']
            if found['username'] != my_profile['username']:
                st.success(f"Найдено: **{found['display_name']}**")
                if st.button(f"Написать @{found['username']}", key=f"start_{found['username']}"):
                    st.session_state.chat_with_user = found
                    del st.session_state['search_res'] # Очищаем поиск
                    st.toast("Чат добавлен! Переходим...", icon="🚀")
                    st.rerun() # Мгновенный переход
            else:
                st.info("Это вы :)")

    # 3. ЧАТЫ
    elif menu == "Чаты":
        st.header("💬 Диалоги")
        contacts = get_my_chat_list(my_profile['username'])
        
        c1, c2 = st.columns([1, 2.5])
        
        with c1:
            st.caption("Контакты")
            if not contacts:
                st.info("Пусто")
            for c in contacts:
                # Выделяем активный чат цветом (primary/secondary)
                is_active = (st.session_state.chat_with_user and st.session_state.chat_with_user['username'] == c)
                if st.button(f"👤 {c}", key=f"chat_{c}", use_container_width=True, type="primary" if is_active else "secondary"):
                    res = supabase.table("profiles").select("*").eq("username", c).execute()
                    if res.data:
                        st.session_state.chat_with_user = res.data[0]
                        st.rerun()
        
        with c2:
            target = st.session_state.chat_with_user
            if target:
                st.subheader(f"Чат с {target['display_name']}")
                
                # Поле ввода
                with st.form("msg_form", clear_on_submit=True):
                    text = st.text_input("Сообщение...", key="msg_text")
                    send = st.form_submit_button("Отправить")
                    
                    if send and text.strip():
                        supabase.table("direct_messages").insert({
                            "sender_id": st.session_state.user.id,
                            "sender_username": my_profile['username'],
                            "recipient_username": target['username'],
                            "content": text.strip()
                        }).execute()
                        st.rerun()
                
                # Сообщения
                try:
                    msgs = supabase.table("direct_messages").select("*").or_(
                        f"and(sender_username.eq.{my_profile['username']},recipient_username.eq.{target['username']}),"
                        f"and(sender_username.eq.{target['username']},recipient_username.eq.{my_profile['username']})"
                    ).order("created_at", desc=True).limit(50).execute()
                    
                    for m in msgs.data:
                        is_me = m['sender_username'] == my_profile['username']
                        align = "right" if is_me else "left"
                        color = "#dcf8c6" if is_me else "#ffffff"
                        st.markdown(f"""
                        <div style="text-align:{align}; margin-bottom:5px;">
                            <div style="display:inline-block; background:{color}; padding:8px 12px; border-radius:12px; border:1px solid #ddd; max-width:80%; text-align:left;">
                                {m['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                except:
                    st.error("Ошибка загрузки")
            else:
                st.info("Выберите чат слева")

# Фоновое обновление (не блокирует интерфейс)
time.sleep(5)
st.rerun()