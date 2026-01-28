import streamlit as st
from supabase import create_client
import time
from datetime import datetime, timezone, timedelta

# --- 1. НАСТРОЙКИ ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Настройте .streamlit/secrets.toml")
    st.stop()

@st.cache_resource
def get_supabase():
    return create_client(URL, KEY)

supabase = get_supabase()

st.set_page_config(page_title="SkyChat Pro", layout="wide", page_icon="⚡")

# --- 2. ПЕРЕМЕННЫЕ ---
if "user" not in st.session_state: st.session_state.user = None
if "chat_with_user" not in st.session_state: st.session_state.chat_with_user = None
if "chat_with_group" not in st.session_state: st.session_state.chat_with_group = None
if "edit_msg_id" not in st.session_state: st.session_state.edit_msg_id = None
if "del_msg_id" not in st.session_state: st.session_state.del_msg_id = None

# --- 3. ОПТИМИЗИРОВАННЫЕ ФУНКЦИИ (КЭШИРОВАНИЕ) ---

# Кэшируем профиль на 10 минут, чтобы не грузить базу
@st.cache_data(ttl=600)
def get_profile_cached(user_id):
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None
    except: return None

# Обычная функция для обновления "last_seen" (без кэша)
def update_heartbeat(user_id):
    try:
        supabase.table("profiles").update({"last_seen": "now()"}).eq("id", user_id).execute()
    except: pass

def get_my_chat_list(my_username):
    # Этот список тоже можно было бы кэшировать, но для актуальности оставим прямым запросом
    try:
        sent = supabase.table("direct_messages").select("recipient_username").eq("sender_username", my_username).execute()
        received = supabase.table("direct_messages").select("sender_username").eq("recipient_username", my_username).execute()
        contacts = set()
        for item in sent.data: contacts.add(item['recipient_username'])
        for item in received.data: contacts.add(item['sender_username'])
        if st.session_state.chat_with_user:
             contacts.add(st.session_state.chat_with_user['username'])
        return list(contacts)
    except: return []

def get_my_groups(my_username):
    try:
        # Сложный запрос, но выполняется быстро благодаря индексам
        m = supabase.table("group_members").select("group_id").eq("username", my_username).execute()
        if not m.data: return []
        ids = [x['group_id'] for x in m.data]
        g = supabase.table("groups").select("*").in_("id", ids).execute()
        return g.data
    except: return []

def is_online(last_seen_str):
    if not last_seen_str: return False
    try:
        dt = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - dt) < timedelta(seconds=65) # Чуть увеличили допуск
    except: return False

# ==========================================
# ЧАСТЬ 4: ФРАГМЕНТЫ (МАГИЯ СКОРОСТИ)
# ==========================================

# ==========================================
# ЧАСТЬ 4: ФРАГМЕНТЫ (МАГИЯ СКОРОСТИ)
# ==========================================

@st.fragment(run_every=2)
def render_messages_auto_update(my_username, target_type, target_obj):
    # 1. Если это личный чат
    if target_type == 'user':
        target_username = target_obj['username']
        
        # Обновляем "Прочитано" тихо
        try:
            supabase.table("direct_messages").update({"is_read": True})\
                .eq("recipient_username", my_username).eq("sender_username", target_username)\
                .eq("is_read", False).execute()
        except: pass

        # Загружаем сообщения
        try:
            res = supabase.table("direct_messages").select("*").or_(
                f"and(sender_username.eq.{my_username},recipient_username.eq.{target_username}),"
                f"and(sender_username.eq.{target_username},recipient_username.eq.{my_username})"
            ).order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: messages = []

    # 2. Если это группа
    else:
        grp_id = target_obj['id']
        try:
            res = supabase.table("group_messages").select("*").eq("group_id", grp_id).order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: messages = []

    # ОТРИСОВКА
    if not messages:
        st.caption("Нет сообщений...")
    
    for m in messages:
        is_me = m['sender_username'] == my_username
        
        # Дизайн
        align = "right" if is_me else "left"
        bg = "#4a4a4a" if is_me else "#262626"
        
        # Мета-данные
        meta_info = ""
        if target_type == 'group' and not is_me:
            meta_info = f"<div style='font-size:0.7em; color:#aaa; margin-bottom:2px;'>{m['sender_username']}</div>"
        
        checks = ""
        if is_me and target_type == 'user':
            checks = "<span style='color:#4ea8de;'>✓✓</span>" if m.get('is_read') else "<span style='color:#777;'>✓</span>"
        
        edited = "<span style='color:#888; font-size:0.7em;'>(ред.)</span>" if m.get('is_edited') else ""

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Мы убираем отступы в начале строк HTML, чтобы Streamlit не думал, что это код
        html_code = f"""
<div style="text-align:{align}; margin-bottom:5px;">
<div style="display:inline-block; background:{bg}; color:white; padding:8px 12px; border-radius:12px; border:1px solid #444; text-align:left; max-width:85%;">
{meta_info}
{m['content']} {edited} {checks}
</div>
</div>
"""
        st.markdown(html_code, unsafe_allow_html=True)
# ==========================================
# ЧАСТЬ 5: СТРАНИЦЫ
# ==========================================

def page_chats(profile):
    st.header("⚡ Быстрые чаты")
    
    # 1. ЛОГИКА ВЫБОРА ЧАТА (Боковая колонка)
    c_list, c_chat = st.columns([1, 3])
    
    with c_list:
        # Группы
        with st.expander("👥 Группы / Создать"):
            groups = get_my_groups(profile['username'])
            for g in groups:
                active = (st.session_state.chat_with_group and st.session_state.chat_with_group['id'] == g['id'])
                if st.button(f"# {g['name']}", key=f"g_{g['id']}", use_container_width=True, type="primary" if active else "secondary"):
                    st.session_state.chat_with_group = g
                    st.session_state.chat_with_user = None
                    st.rerun()
            
            st.divider()
            # Создание группы
            with st.form("new_grp"):
                gn = st.text_input("Название")
                usrs = get_my_chat_list(profile['username'])
                sel = st.multiselect("Участники", usrs)
                if st.form_submit_button("Создать"):
                    # (Код создания группы опущен для краткости, он есть в прошлом ответе)
                    try:
                        r = supabase.table("groups").insert({"name": gn}).execute()
                        gid = r.data[0]['id']
                        mems = [{"group_id": gid, "username": profile['username']}] + [{"group_id": gid, "username": u} for u in sel]
                        supabase.table("group_members").insert(mems).execute()
                        st.toast("Группа создана!")
                        st.rerun()
                    except: st.error("Ошибка")

        # Личные чаты
        users = get_my_chat_list(profile['username'])
        if not users: st.caption("Пусто")
        for u in users:
            active = (st.session_state.chat_with_user and st.session_state.chat_with_user['username'] == u)
            if st.button(f"👤 {u}", key=f"u_{u}", use_container_width=True, type="primary" if active else "secondary"):
                # Тут делаем запрос профиля, он быстрый
                r = supabase.table("profiles").select("*").eq("username", u).execute()
                if r.data:
                    st.session_state.chat_with_user = r.data[0]
                    st.session_state.chat_with_group = None
                    st.rerun()

    # 2. ОКНО ЧАТА
    with c_chat:
        # Определяем, с кем говорим
        target_type = None
        target_obj = None
        
        if st.session_state.chat_with_group:
            target_type = 'group'
            target_obj = st.session_state.chat_with_group
            st.subheader(f"📢 {target_obj['name']}")
            
        elif st.session_state.chat_with_user:
            target_type = 'user'
            target_obj = st.session_state.chat_with_user
            # Проверка онлайн (быстрая)
            try:
                ls = supabase.table("profiles").select("last_seen").eq("username", target_obj['username']).execute()
                online = is_online(ls.data[0]['last_seen']) if ls.data else False
                st.subheader(f"{target_obj['display_name']} {'🟢' if online else '⚪'}")
            except: st.subheader(target_obj['display_name'])

        # Если чат выбран - рисуем интерфейс
        if target_type:
            
            # А) ФОРМА ОТПРАВКИ (Статичная, не мерцает!)
            with st.container():
                # Управление редактированием/удалением (вне авто-обновляемого фрагмента)
                if st.session_state.edit_msg_id:
                    st.info("✏️ Режим редактирования")
                    with st.form("edit_main"):
                        new_txt = st.text_input("Новый текст")
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
                    # Обычная отправка
                    with st.form("send_msg", clear_on_submit=True):
                        txt = st.text_input("Сообщение...", key="main_input")
                        if st.form_submit_button("Отправить") and txt.strip():
                            if target_type == 'user':
                                supabase.table("direct_messages").insert({
                                    "sender_id": st.session_state.user.id,
                                    "sender_username": profile['username'],
                                    "recipient_username": target_obj['username'],
                                    "content": txt.strip()
                                }).execute()
                            else:
                                supabase.table("group_messages").insert({
                                    "group_id": target_obj['id'],
                                    "sender_username": profile['username'],
                                    "content": txt.strip()
                                }).execute()
                            # st.rerun() здесь НЕ ОБЯЗАТЕЛЕН, фрагмент сам подтянет сообщение через 2 сек,
                            # но для мгновенного отклика лучше сделать:
                            st.rerun()

            st.divider()

            # Б) СПИСОК СООБЩЕНИЙ (АВТО-ОБНОВЛЯЕМЫЙ ФРАГМЕНТ)
            # Вся магия скорости здесь. Мы передаем параметры внутрь
            render_messages_auto_update(profile['username'], target_type, target_obj)
            
            # В) КНОПКИ УПРАВЛЕНИЯ (Костыль для Streamlit: кнопки должны быть вне фрагмента для стабильности)
            # Чтобы добавить удаление/редактирование, нужно сделать отдельный список последних 5 своих сообщений
            # с кнопками. Но для скорости пока оставим только чтение/запись.
            
        else:
            st.info("👈 Выберите чат")

# ==========================================
# ЧАСТЬ 6: MAIN
# ==========================================

# ВХОД (Стандартный блок)
if st.session_state.user is None:
    ph = st.empty()
    with ph.container():
        st.title("⚡ SkyChat: Вход")
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
            if st.button("Регистрация"):
                try: supabase.auth.sign_up({"email": re, "password": rp}); st.success("Ок")
                except: pass
    st.stop()

# Обновляем "я онлайн" (фоново)
update_heartbeat(st.session_state.user.id)

# Грузим профиль (с кэшем!)
my_profile = get_profile_cached(st.session_state.user.id)

if not my_profile:
    st.title("Создание профиля")
    with st.form("init"):
        u, n = st.text_input("Ник"), st.text_input("Имя")
        if st.form_submit_button("Ок"):
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u, "display_name": n}).execute()
            # Сбрасываем кэш, чтобы увидеть новый профиль
            get_profile_cached.clear()
            st.rerun()
    st.stop()

# Сайдбар (Статичный)
with st.sidebar:
    st.header("⚡ SkyChat")
    st.write(f"@{my_profile['username']}")
    menu = st.radio("Меню", ["Чаты", "Поиск", "Профиль"])
    if st.button("Выйти"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# Главный контент
content = st.empty()

# Больше никаких глобальных time.sleep!
# Только локальные обновления внутри фрагментов.

with content.container():
    if menu == "Чаты":
        page_chats(my_profile)
        
    elif menu == "Поиск":
        st.header("🔍 Поиск")
        with st.form("s"):
            q = st.text_input("Юзернейм").lower().strip()
            if st.form_submit_button("Найти"):
                r = supabase.table("profiles").select("*").eq("username", q).execute()
                if r.data:
                    found = r.data[0]
                    st.success(f"Найден: {found['display_name']}")
                    if st.button("Написать"):
                        st.session_state.chat_with_user = found
                        st.session_state.chat_with_group = None
                        st.rerun() # Перебрасываем в чаты
                else: st.error("Нет такого")
                
    elif menu == "Профиль":
        st.header("Настройки")
        with st.form("p"):
            dn = st.text_input("Имя", value=my_profile['display_name'])
            if st.form_submit_button("Сохранить"):
                supabase.table("profiles").update({"display_name": dn}).eq("id", st.session_state.user.id).execute()
                get_profile_cached.clear() # Сброс кэша
                st.toast("Готово!")
                time.sleep(1)
                st.rerun()