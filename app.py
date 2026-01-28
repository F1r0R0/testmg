import streamlit as st
from supabase import create_client
import time
from datetime import datetime, timezone, timedelta

# --- 1. КОНФИГУРАЦИЯ И СЕКРЕТЫ ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Настройте .streamlit/secrets.toml")
    st.stop()

st.set_page_config(page_title="SkyChat Pro", layout="wide", page_icon="💎")

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

# --- 2. УПРАВЛЕНИЕ СОСТОЯНИЕМ (SESSION STATE) ---
if "user" not in st.session_state: st.session_state.user = None
if "chat_with_user" not in st.session_state: st.session_state.chat_with_user = None
if "chat_with_group" not in st.session_state: st.session_state.chat_with_group = None
if "edit_msg_id" not in st.session_state: st.session_state.edit_msg_id = None
# Дефолтная тема
if "theme" not in st.session_state: st.session_state.theme = "Midnight (Default)"

# --- 3. ДИЗАЙН-СИСТЕМА И ТЕМЫ ---

THEMES = {
    "Midnight (Default)": {
        "bg_color": "#0e1117",
        "sidebar_bg": "rgba(20, 23, 30, 0.9)",
        "text_color": "#ffffff",
        "primary": "#2962ff",
        "bubble_me": "linear-gradient(135deg, #2962ff 0%, #1565c0 100%)",
        "bubble_other": "#1f2937",
        "input_bg": "#1f2937",
        "border": "#374151"
    },
    "Neon Cyberpunk": {
        "bg_color": "#000000",
        "sidebar_bg": "rgba(10, 10, 10, 0.8)",
        "text_color": "#00ffcc",
        "primary": "#d100d1",
        "bubble_me": "linear-gradient(135deg, #d100d1 0%, #990099 100%)",
        "bubble_other": "#111111",
        "input_bg": "#0a0a0a",
        "border": "#00ffcc"
    },
    "Telegram Light": {
        "bg_color": "#8e99a2", # Фон как обои
        "sidebar_bg": "#ffffff",
        "text_color": "#000000",
        "primary": "#4ea8de",
        "bubble_me": "#effdde", # Светло-зеленый телеграм
        "bubble_other": "#ffffff",
        "input_bg": "#ffffff",
        "border": "#dfe1e5"
    },
    "Deep Ocean": {
        "bg_color": "#0f172a",
        "sidebar_bg": "rgba(15, 23, 42, 0.9)",
        "text_color": "#e2e8f0",
        "primary": "#06b6d4",
        "bubble_me": "linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)",
        "bubble_other": "#1e293b",
        "input_bg": "#1e293b",
        "border": "#334155"
    }
}

def inject_custom_css():
    """Генерирует CSS на основе выбранной темы"""
    t = THEMES[st.session_state.theme]
    
    # Цвет текста внутри пузырей (черный для светлой темы, белый для темной)
    bubble_text_me = "#000000" if st.session_state.theme == "Telegram Light" else "#ffffff"
    bubble_text_other = "#000000" if st.session_state.theme == "Telegram Light" else "#e0e0e0"

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        
        /* Глобальные настройки */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}
        
        /* Скрываем лишнее */
        header {{visibility: hidden !important;}}
        footer {{visibility: hidden !important;}}
        #MainMenu {{visibility: hidden !important;}}
        
        /* Фон приложения */
        .stApp {{
            background-color: {t['bg_color']};
            background-image: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.02) 0%, transparent 50%);
        }}
        
        /* Сайдбар (Glassmorphism) */
        section[data-testid="stSidebar"] {{
            background-color: {t['sidebar_bg']};
            border-right: 1px solid {t['border']};
            backdrop-filter: blur(10px);
        }}
        
        /* Кнопки */
        .stButton > button {{
            border-radius: 12px !important;
            border: none !important;
            font-weight: 500 !important;
            background-color: {t['input_bg']} !important;
            color: {t['text_color']} !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
            transition: all 0.2s ease !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
            background-color: {t['border']} !important;
        }}
        /* Активная кнопка (primary) */
        .stButton > button[kind="primary"] {{
            background: {t['primary']} !important;
            color: white !important;
        }}

        /* Поля ввода (Input) */
        .stTextInput > div > div > input {{
            background-color: {t['input_bg']} !important;
            color: {t['text_color']} !important;
            border-radius: 20px !important;
            border: 1px solid {t['border']} !important;
            padding: 10px 15px !important;
        }}
        .stTextInput > div > div > input:focus {{
            border-color: {t['primary']} !important;
            box-shadow: 0 0 0 2px rgba(255,255,255,0.1) !important;
        }}

        /* АНИМАЦИЯ СООБЩЕНИЙ */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Пузыри сообщений */
        .chat-row {{
            display: flex;
            width: 100%;
            margin-bottom: 8px;
            animation: fadeIn 0.3s ease-out;
        }}
        .row-right {{ justify-content: flex-end; }}
        .row-left {{ justify-content: flex-start; }}

        .bubble {{
            max-width: 75%;
            padding: 10px 16px;
            border-radius: 16px;
            position: relative;
            font-size: 15px;
            line-height: 1.5;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }}
        
        .bubble-me {{
            background: {t['bubble_me']};
            color: {bubble_text_me};
            border-bottom-right-radius: 4px;
        }}
        
        .bubble-other {{
            background: {t['bubble_other']};
            color: {bubble_text_other};
            border: 1px solid {t['border']};
            border-bottom-left-radius: 4px;
        }}

        /* Скроллбар */
        ::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        ::-webkit-scrollbar-track {{
            background: transparent;
        }}
        ::-webkit-scrollbar-thumb {{
            background: {t['border']};
            border-radius: 3px;
        }}
        
        /* Текст заголовков */
        h1, h2, h3, p, span, div {{
            color: {t['text_color']};
        }}
        
        /* Блок статуса (галочки) */
        .meta-info {{
            font-size: 11px;
            margin-top: 4px;
            text-align: right;
            opacity: 0.7;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 4px;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Загружаем CSS сразу
inject_custom_css()

# --- 4. ФУНКЦИИ ДАННЫХ (Backend) ---

@st.cache_data(ttl=300)
def get_profile_cached(user_id):
    try:
        res = supabase.table("profiles").select("username, display_name").eq("id", user_id).execute()
        return res.data[0] if res.data else None
    except: return None

def update_heartbeat(user_id):
    try:
        supabase.table("profiles").update({"last_seen": "now()"}).eq("id", user_id).execute()
    except: pass

def get_my_chat_list(my_username):
    try:
        res = supabase.table("direct_messages").select("sender_username, recipient_username")\
            .or_(f"sender_username.eq.{my_username},recipient_username.eq.{my_username}").execute()
        contacts = set()
        for item in res.data:
            if item['sender_username'] != my_username: contacts.add(item['sender_username'])
            else: contacts.add(item['recipient_username'])
        if st.session_state.chat_with_user:
             contacts.add(st.session_state.chat_with_user['username'])
        return list(contacts)
    except: return []

def get_my_groups(my_username):
    try:
        m = supabase.table("group_members").select("group_id").eq("username", my_username).execute()
        if not m.data: return []
        ids = [x['group_id'] for x in m.data]
        g = supabase.table("groups").select("id, name").in_("id", ids).execute()
        return g.data
    except: return []

def is_online(last_seen_str):
    if not last_seen_str: return False
    try:
        dt = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - dt) < timedelta(seconds=70)
    except: return False

# --- 5. ФРАГМЕНТ ОТРИСОВКИ СООБЩЕНИЙ ---

@st.fragment(run_every=3)
def render_messages_fragment(my_username, target_type, target_obj):
    messages = []
    
    # Логика получения сообщений (без изменений логики, только стиль)
    if target_type == 'user':
        target_username = target_obj['username']
        try:
            supabase.table("direct_messages").update({"is_read": True})\
                .eq("recipient_username", my_username).eq("sender_username", target_username)\
                .eq("is_read", False).execute()
        except: pass

        try:
            res = supabase.table("direct_messages")\
                .select("id, content, sender_username, is_read, is_edited, created_at")\
                .or_(f"and(sender_username.eq.{my_username},recipient_username.eq.{target_username}),and(sender_username.eq.{target_username},recipient_username.eq.{my_username})")\
                .order("created_at", desc=True).limit(30).execute()
            messages = res.data
        except: pass
    else:
        grp_id = target_obj['id']
        try:
            res = supabase.table("group_messages")\
                .select("id, content, sender_username, created_at")\
                .eq("group_id", grp_id).order("created_at", desc=True).limit(30).execute()
            messages = res.data
        except: pass

    if not messages:
        st.markdown("<div style='text-align:center; opacity:0.5; margin-top:20px;'>Нет сообщений... Начните общение!</div>", unsafe_allow_html=True)
        return

    # РЕНДЕРИНГ HTML
    html_buffer = ""
    for m in messages:
        is_me = m['sender_username'] == my_username
        
        # Классы стилей
        row_class = "row-right" if is_me else "row-left"
        bubble_class = "bubble-me" if is_me else "bubble-other"
        
        # Имя отправителя в группе
        sender_label = ""
        if target_type == 'group' and not is_me:
            sender_label = f"<div style='font-size:11px; font-weight:bold; margin-bottom:2px; color:{THEMES[st.session_state.theme]['primary']};'>@{m['sender_username']}</div>"
        
        # Статус (галочки)
        status_html = ""
        if is_me and target_type == 'user':
            checks = "✓✓" if m.get('is_read') else "✓"
            # Цвет галочек зависит от темы, но сделаем универсально
            check_color = "inherit" 
            status_html = f"<span>{checks}</span>"
        
        edited_html = "<span style='margin-right:5px;'>(ред.)</span>" if m.get('is_edited') else ""
        
        # Формируем блок
        html_buffer += f"""
        <div class="chat-row {row_class}">
            <div class="bubble {bubble_class}">
                {sender_label}
                {m['content']}
                <div class="meta-info">
                    {edited_html}
                    {status_html}
                </div>
            </div>
        </div>
        """
    
    st.markdown(html_buffer, unsafe_allow_html=True)

# --- 6. ОСНОВНЫЕ СТРАНИЦЫ ---

def page_chats(profile):
    # Разметка
    c_list, c_chat = st.columns([1, 3])
    
    # ЛЕВАЯ КОЛОНКА (СПИСОК)
    with c_list:
        st.markdown("### 💬 Чаты")
        
        # Вкладки Группы/ЛС
        tab_dm, tab_grp = st.tabs(["Личные", "Группы"])
        
        with tab_dm:
            users = get_my_chat_list(profile['username'])
            if not users: st.caption("Пусто")
            for u in users:
                is_active = (st.session_state.chat_with_user and st.session_state.chat_with_user['username'] == u)
                if st.button(f"👤 {u}", key=f"u_{u}", use_container_width=True, type="primary" if is_active else "secondary"):
                    r = supabase.table("profiles").select("*").eq("username", u).execute()
                    if r.data:
                        st.session_state.chat_with_user = r.data[0]
                        st.session_state.chat_with_group = None
                        st.rerun()

        with tab_grp:
            groups = get_my_groups(profile['username'])
            for g in groups:
                is_active = (st.session_state.chat_with_group and st.session_state.chat_with_group['id'] == g['id'])
                if st.button(f"📢 {g['name']}", key=f"g_{g['id']}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.chat_with_group = g
                    st.session_state.chat_with_user = None
                    st.rerun()
            
            with st.expander("➕ Создать группу"):
                with st.form("create_grp"):
                    gn = st.text_input("Название")
                    usrs = get_my_chat_list(profile['username'])
                    sel = st.multiselect("Кого добавить", usrs)
                    if st.form_submit_button("Создать"):
                        try:
                            r = supabase.table("groups").insert({"name": gn}).execute()
                            gid = r.data[0]['id']
                            mems = [{"group_id": gid, "username": profile['username']}] + [{"group_id": gid, "username": u} for u in sel]
                            supabase.table("group_members").insert(mems).execute()
                            st.toast("Готово!")
                            st.rerun()
                        except: pass

    # ПРАВАЯ КОЛОНКА (ОКНО ЧАТА)
    with c_chat:
        target_type = None
        target_obj = None
        
        # Определяем заголовок
        header_text = "Выберите чат"
        sub_text = ""
        
        if st.session_state.chat_with_group:
            target_type = 'group'
            target_obj = st.session_state.chat_with_group
            header_text = f"📢 {target_obj['name']}"
            
        elif st.session_state.chat_with_user:
            target_type = 'user'
            target_obj = st.session_state.chat_with_user
            try:
                ls = supabase.table("profiles").select("last_seen").eq("username", target_obj['username']).execute()
                online = is_online(ls.data[0]['last_seen']) if ls.data else False
                status = "🟢 В сети" if online else "⚪ Был недавно"
            except: status = ""
            header_text = target_obj['display_name']
            sub_text = status

        # Рисуем заголовок чата
        if target_type:
            st.markdown(f"""
            <div style="padding: 10px 20px; background: rgba(255,255,255,0.05); border-radius: 12px; margin-bottom: 20px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size: 1.2rem; font-weight: 600;">{header_text}</div>
                    <div style="font-size: 0.8rem; opacity: 0.7;">{sub_text}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Поле ввода (над сообщениями или под - лучше под, как в мессенджерах)
            # Но в Streamlit для стабильности лучше поле ввода ставить в контейнер
            
            with st.container():
                # Режим редактирования
                if st.session_state.edit_msg_id:
                    st.info("✏️ Режим редактирования")
                    with st.form("edit_form"):
                        new_txt = st.text_input("Изменить текст")
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("Сохранить"):
                            if target_type == 'user':
                                supabase.table("direct_messages").update({"content": new_txt, "is_edited": True}).eq("id", st.session_state.edit_msg_id).execute()
                            st.session_state.edit_msg_id = None
                            st.rerun()
                        if c2.form_submit_button("Отмена"):
                            st.session_state.edit_msg_id = None
                            st.rerun()
                else:
                    # Обычный ввод
                    with st.form("send_form", clear_on_submit=True):
                        col_input, col_btn = st.columns([6, 1], gap="small")
                        with col_input:
                            msg_txt = st.text_input("msg", placeholder="Напишите сообщение...", label_visibility="collapsed")
                        with col_btn:
                            sent = st.form_submit_button("➤", use_container_width=True)
                        
                        if sent and msg_txt.strip():
                            if target_type == 'user':
                                supabase.table("direct_messages").insert({
                                    "sender_id": st.session_state.user.id,
                                    "sender_username": profile['username'],
                                    "recipient_username": target_obj['username'],
                                    "content": msg_txt.strip()
                                }).execute()
                            else:
                                supabase.table("group_messages").insert({
                                    "group_id": target_obj['id'],
                                    "sender_username": profile['username'],
                                    "content": msg_txt.strip()
                                }).execute()
                            st.rerun()

            st.markdown("---")
            # Рендер сообщений
            render_messages_fragment(profile['username'], target_type, target_obj)
        
        else:
            st.markdown("""
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:50vh; opacity:0.5;">
                <h2>👋 Добро пожаловать в SkyChat</h2>
                <p>Выберите чат слева или найдите пользователя</p>
            </div>
            """, unsafe_allow_html=True)


# --- 7. ТОЧКА ВХОДА (MAIN) ---

if st.session_state.user is None:
    # Красивый экран входа
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align:center;'>💎 SkyChat Pro</h1>", unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["Вход", "Регистрация"])
        with tab_login:
            e = st.text_input("Email")
            p = st.text_input("Пароль", type="password")
            if st.button("Войти", use_container_width=True, type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as ex: st.error(f"Ошибка: {ex}")
        with tab_reg:
            re = st.text_input("Reg Email")
            rp = st.text_input("Reg Password", type="password")
            if st.button("Создать аккаунт", use_container_width=True):
                try: supabase.auth.sign_up({"email": re, "password": rp}); st.success("Ок! Подтвердите почту или войдите.")
                except: pass
    st.stop()

# Логика после входа
update_heartbeat(st.session_state.user.id)
my_profile = get_profile_cached(st.session_state.user.id)

if not my_profile:
    st.title("Добро пожаловать")
    with st.form("init"):
        u = st.text_input("Придумайте юзернейм")
        n = st.text_input("Ваше имя")
        if st.form_submit_button("Начать"):
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u, "display_name": n}).execute()
            get_profile_cached.clear()
            st.rerun()
    st.stop()

# --- САЙДБАР (НАСТРОЙКИ И МЕНЮ) ---
with st.sidebar:
    st.markdown(f"### 👤 {my_profile['display_name']}")
    st.caption(f"@{my_profile['username']}")
    
    st.markdown("---")
    
    # МЕНЮ НАВИГАЦИИ
    selected_page = st.radio("Навигация", ["💬 Диалоги", "🔍 Поиск", "⚙️ Настройки"], label_visibility="collapsed")
    
    st.markdown("---")
    
    # БЛОК ВЫБОРА ТЕМЫ (В САЙДБАРЕ, КАК ПРОСИЛИ)
    st.markdown("### 🎨 Внешний вид")
    current_theme = st.selectbox("Выберите тему", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))
    
    # Если тему сменили - перезагружаем
    if current_theme != st.session_state.theme:
        st.session_state.theme = current_theme
        st.rerun()
        
    st.markdown("---")
    if st.button("Выйти", type="primary", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# --- РОУТИНГ СТРАНИЦ ---
if "Диалоги" in selected_page:
    page_chats(my_profile)

elif "Поиск" in selected_page:
    st.title("🔍 Поиск людей")
    with st.form("search"):
        col_q, col_b = st.columns([4,1])
        with col_q: q = st.text_input("Юзернейм", label_visibility="collapsed", placeholder="Введите username...")
        with col_b: btn = st.form_submit_button("Найти", use_container_width=True)
        
        if btn:
            r = supabase.table("profiles").select("*").eq("username", q).execute()
            if r.data:
                f = r.data[0]
                st.success(f"Нашли: {f['display_name']}")
                if st.button(f"Написать @{f['username']}"):
                    st.session_state.chat_with_user = f
                    st.session_state.chat_with_group = None
                    st.rerun() # Нужно как-то переключить вкладку, но пока просто обновим
            else: st.error("Не найдено")

elif "Настройки" in selected_page:
    st.title("⚙️ Настройки профиля")
    with st.form("settings"):
        new_dn = st.text_input("Отображаемое имя", value=my_profile['display_name'])
        if st.form_submit_button("Сохранить"):
            supabase.table("profiles").update({"display_name": new_dn}).eq("id", st.session_state.user.id).execute()
            get_profile_cached.clear()
            st.toast("Сохранено!")
            time.sleep(1)
            st.rerun()