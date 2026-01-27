import streamlit as st
from supabase import create_client
import time
from datetime import datetime, timezone, timedelta

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

# --- 2. ПЕРЕМЕННЫЕ ---
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_with_user" not in st.session_state:
    st.session_state.chat_with_user = None

# --- 3. ФУНКЦИИ-ПОМОЩНИКИ ---
def get_my_profile():
    try:
        res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
        return res.data[0] if res.data else None
    except:
        return None

def update_last_seen():
    """Обновляет статус 'в сети' для текущего пользователя"""
    if st.session_state.user:
        try:
            # Просто ставим текущее время
            supabase.table("profiles").update({"last_seen": "now()"}).eq("id", st.session_state.user.id).execute()
        except:
            pass

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

def is_user_online(last_seen_str):
    """Проверяет, был ли пользователь в сети за последнюю минуту"""
    if not last_seen_str:
        return False
    try:
        # Парсим время из Supabase (ISO формат)
        last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        # Разница во времени
        diff = now - last_seen
        # Если разница меньше 60 секунд (1 минута)
        return diff < timedelta(seconds=60)
    except:
        return False

# ==========================================
# ЧАСТЬ 4: ФУНКЦИИ СТРАНИЦ
# ==========================================

def render_profile(profile):
    st.header("⚙️ Настройки")
    with st.form("profile_form"):
        new_dn = st.text_input("Имя", value=profile['display_name'])
        new_un = st.text_input("Юзернейм", value=profile['username']).lower().strip()
        
        if st.form_submit_button("Сохранить изменения"):
            try:
                supabase.table("profiles").update({
                    "display_name": new_dn,
                    "username": new_un
                }).eq("id", st.session_state.user.id).execute()
                st.toast("✅ Обновлено!")
                time.sleep(0.5)
                st.rerun()
            except:
                st.error("Юзернейм занят")

def render_search(my_username):
    st.header("🔍 Поиск людей")
    
    with st.form("search_form"):
        q = st.text_input("Введите юзернейм", key="search_input").lower().strip()
        if st.form_submit_button("Найти"):
            res = supabase.table("profiles").select("*").eq("username", q).execute()
            if res.data:
                st.session_state['search_res'] = res.data[0]
            else:
                st.session_state['search_res'] = None
                st.error("Не найдено")

    if 'search_res' in st.session_state and st.session_state['search_res']:
        found = st.session_state['search_res']
        if found['username'] != my_username:
            st.success(f"Найдено: **{found['display_name']}**")
            if st.button(f"Написать @{found['username']}", key=f"btn_start_{found['username']}"):
                st.session_state.chat_with_user = found
                del st.session_state['search_res']
                st.toast("Переходим...")
                st.rerun()
        else:
            st.info("Это вы")

def render_chats(profile):
    st.header("💬 Диалоги")
    contacts = get_my_chat_list(profile['username'])
    
    c1, c2 = st.columns([1, 2.5])
    
    with c1:
        st.caption("Контакты")
        if not contacts:
            st.info("Пусто")
        for c in contacts:
            is_active = (st.session_state.chat_with_user and st.session_state.chat_with_user['username'] == c)
            if st.button(f"👤 {c}", key=f"chat_{c}", use_container_width=True, type="primary" if is_active else "secondary"):
                # При клике обновляем данные о пользователе (чтобы получить свежий last_seen)
                res = supabase.table("profiles").select("*").eq("username", c).execute()
                if res.data:
                    st.session_state.chat_with_user = res.data[0]
                    st.rerun()
    
    with c2:
        target = st.session_state.chat_with_user
        if target:
            # --- ЛОГИКА ОНЛАЙН СТАТУСА ---
            # Получаем свежие данные о собеседнике
            fresh_target_data = supabase.table("profiles").select("last_seen").eq("username", target['username']).execute()
            is_online = False
            if fresh_target_data.data:
                is_online = is_user_online(fresh_target_data.data[0].get('last_seen'))
            
            status_icon = "🟢 В сети" if is_online else "⚪ Не в сети"
            st.caption(f"Чат с **{target['display_name']}** ({status_icon})")
            # -----------------------------

            # --- ЛОГИКА "ПРОЧИТАНО" (Отмечаем входящие как прочитанные) ---
            try:
                supabase.table("direct_messages").update({"is_read": True})\
                    .eq("recipient_username", profile['username'])\
                    .eq("sender_username", target['username'])\
                    .eq("is_read", False).execute()
            except:
                pass
            # -----------------------------------------------------------
            
            with st.form("chat_form", clear_on_submit=True):
                txt = st.text_input("Сообщение...", key="msg_input")
                if st.form_submit_button("Отправить") and txt.strip():
                    supabase.table("direct_messages").insert({
                        "sender_id": st.session_state.user.id,
                        "sender_username": profile['username'],
                        "recipient_username": target['username'],
                        "content": txt.strip()
                    }).execute()
                    st.rerun()
            
            try:
                # Загружаем сообщения + поле is_read
                msgs = supabase.table("direct_messages").select("*").or_(
                    f"and(sender_username.eq.{profile['username']},recipient_username.eq.{target['username']}),"
                    f"and(sender_username.eq.{target['username']},recipient_username.eq.{profile['username']})"
                ).order("created_at", desc=True).limit(50).execute()
                
                for m in msgs.data:
                    is_me = m['sender_username'] == profile['username']
                    align = "right" if is_me else "left"
                    
                    # Цвета и Галочки
                    if is_me:
                        bg_col = "#4a4a4a"
                        # Логика галочек
                        if m.get('is_read'):
                            checks = "<span style='color:#4ea8de; font-size:0.8em; margin-left:5px;'>✓✓</span>" # Голубые галочки
                        else:
                            checks = "<span style='color:#aaaaaa; font-size:0.8em; margin-left:5px;'>✓</span>" # Серая галочка
                    else:
                        bg_col = "#262626"
                        checks = "" # У чужих сообщений галочки не ставим
                    
                    st.markdown(f"""
                    <div style="text-align:{align}; margin-bottom:5px;">
                        <div style="display:inline-block; background:{bg_col}; color:#ffffff; padding:10px 14px; border-radius:12px; border:1px solid #333; text-align:left; max-width:80%;">
                            {m['content']} {checks}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.caption(f"Ошибка: {e}")
                
            time.sleep(5)
            st.rerun()
            
        else:
            st.info("Выберите чат")

# ==========================================
# ЧАСТЬ 5: ОСНОВНОЙ СКРИПТ
# ==========================================

if st.session_state.user is None:
    login_placeholder = st.empty()
    with login_placeholder.container():
        st.title("🔐 Вход")
        t1, t2 = st.tabs(["Вход", "Регистрация"])
        with t1:
            e = st.text_input("Email")
            p = st.text_input("Пароль", type="password")
            if st.button("Войти"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user = res.user
                    login_placeholder.empty()
                    st.rerun()
                except Exception as ex: st.error(ex)
        with t2:
            re = st.text_input("Reg Email")
            rp = st.text_input("Reg Password", type="password")
            if st.button("Создать"):
                try:
                    supabase.auth.sign_up({"email": re, "password": rp})
                    st.success("Готово! Войдите.")
                except Exception as ex: st.error(ex)
    st.stop()

# --- ОБНОВЛЯЕМ "СЕРДЦЕБИЕНИЕ" (Я ТУТ, Я ОНЛАЙН) ---
update_last_seen()
# --------------------------------------------------

my_profile = get_my_profile()
if not my_profile:
    st.title("📝 Создание профиля")
    with st.form("init"):
        u = st.text_input("Юзернейм").lower().strip()
        n = st.text_input("Имя")
        if st.form_submit_button("Начать"):
            try:
                supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u, "display_name": n}).execute()
                st.rerun()
            except: st.error("Занято")
    st.stop()

with st.sidebar:
    st.title("SkyChat")
    st.write(f"@{my_profile['username']}")
    menu = st.radio("Меню", ["Чаты", "Поиск", "Профиль"])
    if st.button("Выйти"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

content = st.empty()
content.empty()

with content.container():
    if menu == "Профиль":
        render_profile(my_profile)
    elif menu == "Поиск":
        render_search(my_profile['username'])
    elif menu == "Чаты":
        render_chats(my_profile)