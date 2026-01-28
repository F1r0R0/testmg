import streamlit as st
from supabase import create_client
import time
from datetime import datetime, timezone, timedelta

# --- 1. КОНФИГУРАЦИЯ ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Настройте .streamlit/secrets.toml")
    st.stop()

st.set_page_config(page_title="SkyChat", layout="wide", page_icon="✈️", initial_sidebar_state="expanded")

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

# --- 2. СОСТОЯНИЕ ---
if "user" not in st.session_state: st.session_state.user = None
# В chat_with_user мы храним весь объект профиля (id, username, display_name)
if "chat_with_user" not in st.session_state: st.session_state.chat_with_user = None
if "chat_with_group" not in st.session_state: st.session_state.chat_with_group = None
if "edit_msg_id" not in st.session_state: st.session_state.edit_msg_id = None
if "theme" not in st.session_state: st.session_state.theme = "Midnight Blue"
if "search_res" not in st.session_state: st.session_state.search_res = None

# --- 3. ТЕМЫ И ДИЗАЙН ---
THEMES = {
    "Midnight Blue": {
        "bg_color": "#0f172a", "sidebar_bg": "#1e293b", "text_color": "#f1f5f9",
        "primary": "#3b82f6", "bubble_me": "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
        "bubble_other": "#334155", "input_bg": "#1e293b", "border": "#475569"
    },
    "Graphite (Dark)": {
        "bg_color": "#18181b", "sidebar_bg": "#27272a", "text_color": "#e4e4e7",
        "primary": "#10b981", "bubble_me": "#059669", 
        "bubble_other": "#3f3f46", "input_bg": "#27272a", "border": "#52525b"
    },
    "Telegram Light": {
        "bg_color": "#87a3b3", "sidebar_bg": "#ffffff", "text_color": "#1c1c1e",
        "primary": "#40a7e3", "bubble_me": "#eeffde",
        "bubble_other": "#ffffff", "input_bg": "#ffffff", "border": "#d1d5db"
    }
}

def inject_custom_css():
    t = THEMES[st.session_state.theme]
    text_me = "#000000" if "Light" in st.session_state.theme else "#ffffff"
    text_other = "#000000" if "Light" in st.session_state.theme else "#e2e8f0"
    
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="css"] {{ font-family: 'Roboto', sans-serif; overflow: hidden; }}
        #MainMenu, footer {{visibility: hidden;}}
        .stApp {{ background-color: {t['bg_color']}; }}
        section[data-testid="stSidebar"] {{ background-color: {t['sidebar_bg']}; border-right: 1px solid {t['border']}; }}
        
        .stButton button {{ border-radius: 10px !important; border: none !important; background-color: {t['input_bg']} !important; color: {t['text_color']} !important; }}
        .stButton button:hover {{ filter: brightness(1.2); }}
        .stTextInput input {{ background-color: {t['input_bg']} !important; color: {t['text_color']} !important; border: 1px solid {t['border']} !important; border-radius: 12px !important; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
        .stTabs [data-baseweb="tab"] {{ background-color: {t['input_bg']}; border-radius: 8px; padding: 5px 15px; color: {t['text_color']}; }}
        .stTabs [aria-selected="true"] {{ background-color: {t['primary']} !important; color: white !important; }}
        
        /* СКРОЛЛ ЧАТА */
        .msg-container {{ height: 68vh; overflow-y: auto; display: flex; flex-direction: column-reverse; gap: 8px; padding-right: 10px; padding-bottom: 10px; }}
        .msg-container::-webkit-scrollbar {{ width: 6px; }}
        .msg-container::-webkit-scrollbar-thumb {{ background: {t['border']}; border-radius: 3px; }}
        
        .msg-row {{ display: flex; width: 100%; }}
        .row-me {{ justify-content: flex-end; }}
        .row-other {{ justify-content: flex-start; }}
        .bubble {{ max-width: 75%; padding: 8px 14px; border-radius: 16px; font-size: 15px; line-height: 1.5; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }}
        .bubble-me {{ background: {t['bubble_me']}; color: {text_me}; border-bottom-right-radius: 2px; }}
        .bubble-other {{ background: {t['bubble_other']}; color: {text_other}; border-bottom-left-radius: 2px; }}
        .msg-meta {{ font-size: 11px; margin-top: 4px; display: flex; justify-content: flex-end; align-items: center; opacity: 0.7; gap: 5px; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_custom_css()

# --- 4. DATA FUNCTIONS (ТЕПЕРЬ НА ID) ---

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
    """Ищет собеседников по ID, а не по имени"""
    try:
        # Выбираем ID всех, с кем я общался
        sent = supabase.table("direct_messages").select("recipient_id").eq("sender_id", my_id).execute()
        received = supabase.table("direct_messages").select("sender_id").eq("recipient_id", my_id).execute()
        
        ids = set()
        for x in sent.data: 
            if x['recipient_id']: ids.add(x['recipient_id'])
        for x in received.data: 
            if x['sender_id']: ids.add(x['sender_id'])
            
        if not ids: return []
        
        # Получаем профили этих людей (их актуальные имена)
        profiles = supabase.table("profiles").select("*").in_("id", list(ids)).execute()
        return profiles.data
    except: return []

def get_groups_by_id(my_id):
    """Ищет группы, где я состою, по моему ID"""
    try:
        m = supabase.table("group_members").select("group_id").eq("user_id", my_id).execute()
        if not m.data: return []
        ids = [x['group_id'] for x in m.data]
        return supabase.table("groups").select("*").in_("id", ids).execute().data
    except: return []

# --- 5. ФРАГМЕНТ СООБЩЕНИЙ ---

@st.fragment(run_every=3)
def render_messages(my_id, target_type, target_obj):
    messages = []
    
    if target_type == 'user':
        # ЛОГИКА НА ID:
        target_id = target_obj['id']
        
        # Помечаем прочитанным
        try: supabase.table("direct_messages").update({"is_read": True})\
            .eq("recipient_id", my_id).eq("sender_id", target_id).eq("is_read", False).execute()
        except: pass
        
        try:
            # Загружаем сообщения, где (Я отправил ЕМУ) или (ОН отправил МНЕ) - по ID
            res = supabase.table("direct_messages").select("*")\
                .or_(f"and(sender_id.eq.{my_id},recipient_id.eq.{target_id}),and(sender_id.eq.{target_id},recipient_id.eq.{my_id})")\
                .order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass

    else:
        # Группы (тут пока по group_id, всё ок)
        gid = target_obj['id']
        try:
            res = supabase.table("group_messages").select("*").eq("group_id", gid).order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass

    if not messages:
        st.caption("Нет сообщений.")
        return

    html_content = '<div class="msg-container">'
    for m in messages:
        # Проверка "Я ли это" теперь по ID (надежно!)
        is_me = m['sender_id'] == my_id
        
        row_cls = "row-me" if is_me else "row-other"
        bub_cls = "bubble-me" if is_me else "bubble-other"
        
        sender_div = ""
        if target_type == 'group' and not is_me:
            primary_col = THEMES[st.session_state.theme]['primary']
            # В старых сообщениях может не быть username, но пока оставим как fallback
            name_show = m.get('sender_username', 'User')
            sender_div = f"<div style='font-size:12px; color:{primary_col}; font-weight:bold; margin-bottom:2px;'>{name_show}</div>"
        
        status_span = ""
        if is_me and target_type == 'user':
            icon = "✓✓" if m.get('is_read') else "✓"
            status_span = f"<span>{icon}</span>"
        edit_span = "<span>(ред.)</span>" if m.get('is_edited') else ""
        
        html_content += f'<div class="msg-row {row_cls}"><div class="bubble {bub_cls}">{sender_div}{m["content"]}<div class="msg-meta">{edit_span} {status_span}</div></div></div>'

    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)


# --- 6. СТРАНИЦЫ ---

def page_chats(profile):
    c_left, c_right = st.columns([1, 2.5])
    my_id = st.session_state.user.id
    
    with c_left:
        st.subheader("💬 Чаты")
        tab_dm, tab_grp = st.tabs(["Личные", "Группы"])
        
        with tab_dm:
            # Получаем СПИСОК ПРОФИЛЕЙ людей
            users = get_chat_list_by_id(my_id)
            if not users: st.caption("Пусто")
            for u in users:
                active = (st.session_state.chat_with_user and st.session_state.chat_with_user['id'] == u['id'])
                # Отображаем актуальное имя из профиля
                if st.button(f"👤 {u['display_name']}", key=f"u_{u['id']}", use_container_width=True, type="primary" if active else "secondary"):
                    st.session_state.chat_with_user = u
                    st.session_state.chat_with_group = None
                    st.rerun()

        with tab_grp:
            grps = get_groups_by_id(my_id)
            for g in grps:
                active = (st.session_state.chat_with_group and st.session_state.chat_with_group['id'] == g['id'])
                if st.button(f"📢 {g['name']}", key=f"g_{g['id']}", use_container_width=True, type="primary" if active else "secondary"):
                    st.session_state.chat_with_group = g
                    st.session_state.chat_with_user = None
                    st.rerun()
            
            st.markdown("---")
            with st.expander("➕ Новая группа"):
                with st.form("new_g"):
                    gn = st.text_input("Название")
                    # Для создания группы тоже нужны ID
                    friends = get_chat_list_by_id(my_id)
                    # Создаем словарь {username: id} для выбора
                    friend_map = {f"{u['display_name']} (@{u['username']})": u['id'] for u in friends}
                    sel_names = st.multiselect("Участники", list(friend_map.keys()))
                    
                    if st.form_submit_button("Создать"):
                        try:
                            r = supabase.table("groups").insert({"name": gn}).execute()
                            gid = r.data[0]['id']
                            # Добавляем участников по ID
                            mems = [{"group_id": gid, "user_id": my_id, "username": profile['username']}]
                            for name in sel_names:
                                uid = friend_map[name]
                                # Находим username для обратной совместимости
                                uname = next(u['username'] for u in friends if u['id'] == uid)
                                mems.append({"group_id": gid, "user_id": uid, "username": uname})
                                
                            supabase.table("group_members").insert(mems).execute()
                            st.toast("Создано!")
                            st.rerun()
                        except Exception as e: st.error(f"Ошибка: {e}")

    with c_right:
        ttype, tobj = None, None
        if st.session_state.chat_with_group: ttype, tobj = 'group', st.session_state.chat_with_group
        elif st.session_state.chat_with_user: ttype, tobj = 'user', st.session_state.chat_with_user
        
        if ttype:
            title = tobj['name'] if ttype == 'group' else tobj['display_name']
            st.markdown(f"<h3 style='margin-top:0;'>{title}</h3>", unsafe_allow_html=True)
            
            render_messages(my_id, ttype, tobj)
            
            # ВВОД
            if st.session_state.edit_msg_id:
                st.info("✏️ Редактирование")
                with st.form("edit"):
                    nt = st.text_input("Текст")
                    if st.form_submit_button("Сохранить"):
                        supabase.table("direct_messages").update({"content": nt, "is_edited": True}).eq("id", st.session_state.edit_msg_id).execute()
                        st.session_state.edit_msg_id = None
                        st.rerun()
                    if st.form_submit_button("Отмена"):
                        st.session_state.edit_msg_id = None
                        st.rerun()
            else:
                with st.form("send", clear_on_submit=True):
                    c_in, c_btn = st.columns([6, 1])
                    with c_in: txt = st.text_input("msg", label_visibility="collapsed", placeholder="Сообщение...")
                    with c_btn: 
                        if st.form_submit_button("➤", use_container_width=True) and txt.strip():
                            if ttype == 'user':
                                # ВАЖНО: ОТПРАВЛЯЕМ С sender_id и recipient_id
                                supabase.table("direct_messages").insert({
                                    "sender_id": my_id,
                                    "sender_username": profile['username'], # Оставляем для истории
                                    "recipient_id": tobj['id'],
                                    "recipient_username": tobj['username'],
                                    "content": txt.strip()
                                }).execute()
                            else:
                                supabase.table("group_messages").insert({
                                    "group_id": tobj['id'],
                                    "sender_id": my_id, # Добавляем ID отправителя
                                    "sender_username": profile['username'],
                                    "content": txt.strip()
                                }).execute()
                            st.rerun()
        else:
            st.info("Выберите чат")

def page_settings(profile):
    st.title("⚙️ Настройки")
    st.subheader("Внешний вид")
    current = st.selectbox("Тема оформления", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))
    if current != st.session_state.theme:
        st.session_state.theme = current
        st.rerun()

def page_profile(profile):
    st.title("👤 Профиль")
    with st.form("prof_upd"):
        dn = st.text_input("Отображаемое имя", value=profile['display_name'])
        un_val = profile['username'] if profile['username'] else ""
        un = st.text_input("Юзернейм (@)", value=un_val).strip()
        
        if st.form_submit_button("Сохранить"):
            try:
                # Теперь обновляем без страха, связи Foreign Key мы удалили в SQL
                supabase.table("profiles").update({"display_name": dn, "username": un}).eq("id", st.session_state.user.id).execute()
                get_profile_cached.clear()
                st.success("Сохранено!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка обновления: {e}")

def page_search(profile):
    st.title("🔍 Поиск")
    with st.form("s"):
        q = st.text_input("Введите юзернейм").strip()
        submitted = st.form_submit_button("Найти")
    
    if submitted:
        r = supabase.table("profiles").select("*").eq("username", q).execute()
        if r.data:
            st.session_state.search_res = r.data[0]
        else:
            st.session_state.search_res = None
            st.error("Никого не нашли")

    if st.session_state.search_res:
        f = st.session_state.search_res
        st.success(f"Нашли: {f['display_name']}")
        if st.button(f"Написать @{f['username']}"):
            st.session_state.chat_with_user = f
            st.session_state.chat_with_group = None
            st.session_state.search_res = None
            st.rerun()

# --- 7. MAIN ---

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

# --- САЙДБАР ---
with st.sidebar:
    st.header("SkyChat")
    st.write(f"Привет, **{my_profile['display_name']}**")
    menu = st.radio("Навигация", ["Чаты", "Поиск", "Профиль", "Настройки"], label_visibility="collapsed")
    st.divider()
    if st.button("Выйти", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

if menu == "Чаты": page_chats(my_profile)
elif menu == "Поиск": page_search(my_profile)
elif menu == "Профиль": page_profile(my_profile)
elif menu == "Настройки": page_settings(my_profile)