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
# Для личных чатов
if "chat_with_user" not in st.session_state:
    st.session_state.chat_with_user = None
# Для групповых чатов (НОВОЕ)
if "chat_with_group" not in st.session_state:
    st.session_state.chat_with_group = None

# Состояния редактирования
if "edit_msg_id" not in st.session_state:
    st.session_state.edit_msg_id = None
if "del_msg_id" not in st.session_state:
    st.session_state.del_msg_id = None

# --- 3. ФУНКЦИИ-ПОМОЩНИКИ ---
def get_my_profile():
    try:
        res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
        return res.data[0] if res.data else None
    except:
        return None

def update_last_seen():
    if st.session_state.user:
        try:
            supabase.table("profiles").update({"last_seen": "now()"}).eq("id", st.session_state.user.id).execute()
        except: pass

def get_my_contacts_usernames(my_username):
    """Возвращает список юзернеймов людей, с кем были диалоги (для создания группы)"""
    try:
        sent = supabase.table("direct_messages").select("recipient_username").eq("sender_username", my_username).execute()
        received = supabase.table("direct_messages").select("sender_username").eq("recipient_username", my_username).execute()
        contacts = set()
        for item in sent.data: contacts.add(item['recipient_username'])
        for item in received.data: contacts.add(item['sender_username'])
        return list(contacts)
    except: return []

def get_my_groups(my_username):
    """Получает список групп, в которых я состою"""
    try:
        # 1. Узнаем ID групп, где я есть
        memberships = supabase.table("group_members").select("group_id").eq("username", my_username).execute()
        if not memberships.data:
            return []
        
        group_ids = [m['group_id'] for m in memberships.data]
        
        # 2. Получаем названия этих групп
        groups = supabase.table("groups").select("*").in_("id", group_ids).execute()
        return groups.data
    except:
        return []

def is_user_online(last_seen_str):
    if not last_seen_str: return False
    try:
        last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - last_seen) < timedelta(seconds=60)
    except: return False

# ==========================================
# ЧАСТЬ 4: ЛОГИКА СТРАНИЦ
# ==========================================

def render_profile(profile):
    st.header("⚙️ Настройки")
    with st.form("profile_form"):
        new_dn = st.text_input("Имя", value=profile['display_name'])
        new_un = st.text_input("Юзернейм", value=profile['username']).lower().strip()
        if st.form_submit_button("Сохранить"):
            try:
                supabase.table("profiles").update({"display_name": new_dn, "username": new_un}).eq("id", st.session_state.user.id).execute()
                st.toast("✅ Обновлено!")
                time.sleep(0.5)
                st.rerun()
            except: st.error("Юзернейм занят")

def render_search(my_username):
    st.header("🔍 Поиск")
    with st.form("search_form"):
        q = st.text_input("Юзернейм", key="s_q").lower().strip()
        if st.form_submit_button("Найти"):
            res = supabase.table("profiles").select("*").eq("username", q).execute()
            if res.data: st.session_state['search_res'] = res.data[0]
            else: st.error("Не найдено")
    
    if 'search_res' in st.session_state and st.session_state['search_res']:
        found = st.session_state['search_res']
        if found['username'] != my_username:
            st.success(f"Найдено: **{found['display_name']}**")
            if st.button(f"Написать", key=f"start_{found['username']}"):
                st.session_state.chat_with_user = found
                st.session_state.chat_with_group = None # Сброс группы
                del st.session_state['search_res']
                st.rerun()
        else: st.info("Это вы")

def render_chats(profile):
    st.header("💬 Диалоги")
    
    # === БЛОК СОЗДАНИЯ ГРУППЫ ===
    with st.expander("➕ Создать новую группу"):
        with st.form("create_group_form"):
            grp_name = st.text_input("Название группы")
            # Получаем список контактов для добавления
            my_contacts = get_my_contacts_usernames(profile['username'])
            selected_members = st.multiselect("Добавить участников", my_contacts)
            
            if st.form_submit_button("Создать группу"):
                if grp_name and selected_members:
                    try:
                        # 1. Создаем группу
                        g_res = supabase.table("groups").insert({"name": grp_name}).execute()
                        new_grp_id = g_res.data[0]['id']
                        
                        # 2. Добавляем МЕНЯ
                        members_data = [{"group_id": new_grp_id, "username": profile['username']}]
                        # 3. Добавляем ОСТАЛЬНЫХ
                        for m in selected_members:
                            members_data.append({"group_id": new_grp_id, "username": m})
                        
                        supabase.table("group_members").insert(members_data).execute()
                        st.toast(f"Группа '{grp_name}' создана!", icon="🎉")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
                else:
                    st.warning("Введите название и выберите хотя бы одного участника")

    st.divider()

    # === СПИСОК ЧАТОВ (СЛЕВА) ===
    c1, c2 = st.columns([1, 2.5])
    
    with c1:
        st.subheader("Список")
        
        # 1. ГРУППЫ
        my_groups = get_my_groups(profile['username'])
        if my_groups:
            st.caption("Группы")
            for g in my_groups:
                # Проверка активности
                is_active = (st.session_state.chat_with_group and st.session_state.chat_with_group['id'] == g['id'])
                if st.button(f"📢 {g['name']}", key=f"grp_{g['id']}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.chat_with_group = g
                    st.session_state.chat_with_user = None # Сброс личного чата
                    st.rerun()
        
        # 2. ЛИЧНЫЕ ЧАТЫ
        contacts = get_my_contacts_usernames(profile['username'])
        # Если кого-то выбрали в поиске, добавляем временно
        if st.session_state.chat_with_user and st.session_state.chat_with_user['username'] not in contacts:
            contacts.append(st.session_state.chat_with_user['username'])

        st.caption("Личные сообщения")
        if not contacts: st.info("Нет диалогов")
        
        for c in contacts:
            is_active = (st.session_state.chat_with_user and st.session_state.chat_with_user['username'] == c)
            if st.button(f"👤 {c}", key=f"user_{c}", use_container_width=True, type="primary" if is_active else "secondary"):
                # Загружаем профиль собеседника
                res = supabase.table("profiles").select("*").eq("username", c).execute()
                if res.data:
                    st.session_state.chat_with_user = res.data[0]
                    st.session_state.chat_with_group = None # Сброс группы
                    st.rerun()

    # === ОКНО ЧАТА (СПРАВА) ===
    with c2:
        # --- ВАРИАНТ 1: ГРУППОВОЙ ЧАТ ---
        if st.session_state.chat_with_group:
            curr_grp = st.session_state.chat_with_group
            st.subheader(f"📢 {curr_grp['name']}")
            
            # Форма отправки в группу
            with st.form("grp_send", clear_on_submit=True):
                txt = st.text_input("Сообщение...", key="grp_msg_in")
                if st.form_submit_button("Отправить") and txt.strip():
                    supabase.table("group_messages").insert({
                        "group_id": curr_grp['id'],
                        "sender_username": profile['username'],
                        "content": txt.strip()
                    }).execute()
                    st.rerun()
            
            # Загрузка сообщений группы
            try:
                g_msgs = supabase.table("group_messages").select("*").eq("group_id", curr_grp['id'])\
                    .order("created_at", desc=True).limit(50).execute()
                
                for m in g_msgs.data:
                    is_me = m['sender_username'] == profile['username']
                    align = "right" if is_me else "left"
                    bg = "#4a4a4a" if is_me else "#262626"
                    
                    st.markdown(f"""
                    <div style="text-align:{align}; margin-bottom:5px;">
                        <div style="display:inline-block; background:{bg}; color:white; padding:8px 12px; border-radius:10px; border:1px solid #444; text-align:left;">
                            <div style="font-size:0.7em; color:#bbb; margin-bottom:2px;">{m['sender_username']}</div>
                            {m['content']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            except: st.error("Ошибка загрузки группы")
            
            time.sleep(5)
            st.rerun()

        # --- ВАРИАНТ 2: ЛИЧНЫЙ ЧАТ (Старый код) ---
        elif st.session_state.chat_with_user:
            target = st.session_state.chat_with_user
            
            # Онлайн статус и Прочитано
            try:
                fresh = supabase.table("profiles").select("last_seen").eq("username", target['username']).execute()
                online = is_user_online(fresh.data[0]['last_seen']) if fresh.data else False
                st.caption(f"Чат с **{target['display_name']}** ({'🟢 В сети' if online else '⚪ Оффлайн'})")
                
                supabase.table("direct_messages").update({"is_read": True})\
                    .eq("recipient_username", profile['username']).eq("sender_username", target['username']).eq("is_read", False).execute()
            except: pass

            # Форма отправки (если не ред.)
            if st.session_state.edit_msg_id is None:
                with st.form("dm_send", clear_on_submit=True):
                    txt = st.text_input("Сообщение...", key="dm_msg_in")
                    if st.form_submit_button("Отправить") and txt.strip():
                        supabase.table("direct_messages").insert({
                            "sender_id": st.session_state.user.id,
                            "sender_username": profile['username'],
                            "recipient_username": target['username'],
                            "content": txt.strip()
                        }).execute()
                        st.rerun()

            # Сообщения
            try:
                msgs = supabase.table("direct_messages").select("*").or_(
                    f"and(sender_username.eq.{profile['username']},recipient_username.eq.{target['username']}),"
                    f"and(sender_username.eq.{target['username']},recipient_username.eq.{profile['username']})"
                ).order("created_at", desc=True).limit(50).execute()

                for m in msgs.data:
                    is_me = m['sender_username'] == profile['username']
                    align = "right" if is_me else "left"
                    bg = "#4a4a4a" if is_me else "#262626"
                    checks = ("✓✓" if m.get('is_read') else "✓") if is_me else ""
                    edit_mark = "(ред.)" if m.get('is_edited') else ""

                    st.markdown(f"""
                    <div style="text-align:{align}; margin-bottom:5px;">
                        <div style="display:inline-block; background:{bg}; color:white; padding:10px 14px; border-radius:12px; border:1px solid #444; text-align:left;">
                            {m['content']} <span style="color:#888; font-size:0.8em;">{edit_mark} {checks}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Кнопки ред/уд (только для DM пока)
                    if is_me:
                        if st.session_state.edit_msg_id == m['id']:
                            with st.form(f"ed_{m['id']}"):
                                nt = st.text_input("Ред.", value=m['content'])
                                if st.form_submit_button("Сохранить"):
                                    supabase.table("direct_messages").update({"content": nt, "is_edited": True}).eq("id", m['id']).execute()
                                    st.session_state.edit_msg_id = None; st.rerun()
                                if st.form_submit_button("Отмена"):
                                    st.session_state.edit_msg_id = None; st.rerun()
                        elif st.session_state.del_msg_id == m['id']:
                            st.warning("Удалить?")
                            c_y, c_n = st.columns(2)
                            if c_y.button("Да", key=f"y_{m['id']}"):
                                supabase.table("direct_messages").delete().eq("id", m['id']).execute()
                                st.session_state.del_msg_id = None; st.rerun()
                            if c_n.button("Нет", key=f"n_{m['id']}"):
                                st.session_state.del_msg_id = None; st.rerun()
                        else:
                            c_space, c_e, c_d = st.columns([0.8, 0.1, 0.1])
                            with c_e: 
                                if st.button("✏️", key=f"e_{m['id']}"): st.session_state.edit_msg_id = m['id']; st.rerun()
                            with c_d:
                                if st.button("🗑️", key=f"d_{m['id']}"): st.session_state.del_msg_id = m['id']; st.rerun()

            except Exception as e: st.caption(f"Ошибка: {e}")
            
            time.sleep(5)
            st.rerun()
        else:
            st.info("Выберите чат или группу слева")

# ==========================================
# ЧАСТЬ 5: MAIN
# ==========================================
if st.session_state.user is None:
    # ВХОД... (тот же код входа, сокращаю для лимита символов, он не менялся)
    # Используй код входа из предыдущего ответа, он идеален.
    # Вставлю кратко:
    ph = st.empty()
    with ph.container():
        st.title("🔐 Вход")
        t1, t2 = st.tabs(["Вход", "Регистрация"])
        with t1:
            e, p = st.text_input("Email"), st.text_input("Пароль", type="password")
            if st.button("Войти"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user = res.user
                    ph.empty(); st.rerun()
                except Exception as ex: st.error(ex)
        with t2:
            re, rp = st.text_input("Reg Email"), st.text_input("Reg Pass", type="password")
            if st.button("Создать"):
                try: supabase.auth.sign_up({"email": re, "password": rp}); st.success("Ок")
                except: pass
    st.stop()

update_last_seen()
my_profile = get_my_profile()
if not my_profile:
    # СОЗДАНИЕ ПРОФИЛЯ... (тот же код)
    st.title("Создать профиль")
    with st.form("i"):
        u, n = st.text_input("Юзернейм"), st.text_input("Имя")
        if st.form_submit_button("Ок"):
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u, "display_name": n}).execute()
            st.rerun()
    st.stop()

with st.sidebar:
    st.title("SkyChat")
    st.write(f"@{my_profile['username']}")
    menu = st.radio("Меню", ["Чаты", "Поиск", "Профиль"])
    if st.button("Выйти"): supabase.auth.sign_out(); st.session_state.user = None; st.rerun()

cont = st.empty()
cont.empty()
with cont.container():
    if menu == "Профиль": render_profile(my_profile)
    elif menu == "Поиск": render_search(my_profile['username'])
    elif menu == "Чаты": render_chats(my_profile)