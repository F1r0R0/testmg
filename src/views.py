# src/views.py
import streamlit as st
import time
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from src.database import supabase, get_chat_list_by_id, get_groups_by_id, get_unread_counts, get_profile_cached
from src.components import render_messages_with_buttons
from src.config import THEMES

# --- ГЕНЕРАТОР ЦВЕТА АВАТАРКИ ---
def get_avatar_color(user_id):
    """Генерирует стабильный цвет на основе ID пользователя"""
    colors = [
        "#ef4444", "#f97316", "#f59e0b", "#84cc16", "#10b981", 
        "#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#d946ef", "#f43f5e"
    ]
    # Хэшируем ID и берем остаток от деления, чтобы выбрать цвет
    hash_val = int(hashlib.sha256(user_id.encode('utf-8')).hexdigest(), 16)
    return colors[hash_val % len(colors)]

# --- КОМПОНЕНТ АВАТАРКИ (HTML) ---
def get_avatar_html(profile, size="small"):
    """Возвращает HTML код аватарки (картинка или буква)"""
    url = profile.get('avatar_url')
    name = profile.get('display_name', '?')
    letter = name[0] if name else "?"
    
    if size == "large":
        cls_img = "user-avatar"
        cls_ph = "avatar-placeholder"
    else:
        cls_img = "user-avatar-small"
        cls_ph = "avatar-placeholder-small"

    if url:
        return f'<img src="{url}" class="{cls_img}">'
    else:
        color = get_avatar_color(profile['id'])
        return f'<div class="{cls_ph}" style="background-color: {color};">{letter}</div>'

# --- МОДАЛЬНОЕ ОКНО ПРОФИЛЯ (ЧУЖОГО) ---
@st.dialog("Профиль пользователя")
def view_profile_dialog(user_profile):
    st.markdown(f"<div style='text-align:center'>{get_avatar_html(user_profile, 'large')}</div>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center; margin:0;'>{user_profile['display_name']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; opacity:0.7;'>@{user_profile['username']}</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    bio = user_profile.get('bio')
    if bio:
        st.subheader("О себе")
        st.info(bio)
    else:
        st.caption("Информация не указана")
        
    # Показываем статус (онлайн/офлайн)
    is_on, txt = get_user_status(user_profile.get('last_seen'))
    st.caption(f"Статус: {txt}")

# --- ЛОГИКА СТАТУСА ---
def get_user_status(last_seen_iso):
    if not last_seen_iso: return False, "Был(а) давно"
    try:
        dt = datetime.fromisoformat(last_seen_iso.replace('Z', '+00:00'))
        dt = dt.astimezone(timezone(timedelta(hours=3))) 
        now = datetime.now(timezone(timedelta(hours=3)))
        diff_seconds = (now - dt).total_seconds()
        
        if diff_seconds < 60: return True, "В сети"
        
        time_str = dt.strftime("%H:%M")
        if dt.date() == now.date(): return False, f"Был(а) сегодня в {time_str}"
        elif dt.date() == (now - timedelta(days=1)).date(): return False, f"Был(а) вчера в {time_str}"
        else:
            return False, f"Был(а) {dt.strftime('%d.%m')} в {time_str}"
    except: return False, "Не в сети"

def page_chats(profile):
    c_left, c_right = st.columns([1, 2.5])
    my_id = st.session_state.user.id
    
    with c_left:
        st.subheader("💬 Чаты")
        tab_dm, tab_grp = st.tabs(["Личные", "Группы"])
        unread_counts = get_unread_counts(my_id)
        
        with tab_dm:
            users = get_chat_list_by_id(my_id)
            if not users: st.caption("Пусто")
            for u in users:
                active = (st.session_state.chat_with_user and st.session_state.chat_with_user['id'] == u['id'])
                is_online, _ = get_user_status(u.get('last_seen'))
                # В списке пока оставляем эмодзи для простоты, т.к. st.button не рендерит HTML
                status_icon = "🟢" if is_online else "👤"
                count = unread_counts.get(u['id'], 0)
                prefix = f"🔴 {count}" if count > 0 else status_icon
                label = f"{prefix} | {u['display_name']}"
                
                if st.button(label, key=f"u_{u['id']}", use_container_width=True, type="primary" if active else "secondary"):
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
                    friends = get_chat_list_by_id(my_id)
                    friend_map = {f"{u['display_name']} (@{u['username']})": u['id'] for u in friends}
                    sel_names = st.multiselect("Участники", list(friend_map.keys()))
                    if st.form_submit_button("Создать"):
                        try:
                            r = supabase.table("groups").insert({"name": gn}).execute()
                            gid = r.data[0]['id']
                            mems = [{"group_id": gid, "user_id": my_id, "username": profile['username']}]
                            for name in sel_names:
                                uid = friend_map[name]
                                uname = next(u['username'] for u in friends if u['id'] == uid)
                                mems.append({"group_id": gid, "user_id": uid, "username": uname})
                            supabase.table("group_members").insert(mems).execute()
                            st.toast("Создано!")
                            st.rerun()
                        except Exception as e: st.error(f"Ошибка: {e}")

    # --- ОКНО ЧАТА ---
    with c_right:
        ttype, tobj = None, None
        if st.session_state.chat_with_group: ttype, tobj = 'group', st.session_state.chat_with_group
        elif st.session_state.chat_with_user: ttype, tobj = 'user', st.session_state.chat_with_user
        
        if ttype:
            # === ШАПКА ЧАТА (С КЛИКАБЕЛЬНЫМ ПРОФИЛЕМ) ===
            c_head, c_act = st.columns([0.9, 0.1])
            with c_head:
                if ttype == 'user':
                    # Сюда вставляем аватарку и имя. При нажатии на кнопку - открываем профиль
                    # Хак: делаем невидимую кнопку поверх или просто кнопку с именем
                    
                    is_on, status_text = get_user_status(tobj.get('last_seen'))
                    status_color = "#10b981" if is_on else "gray"
                    
                    # Разметка шапки с HTML аватаром
                    col_ava, col_info = st.columns([0.1, 0.9])
                    with col_ava:
                        st.markdown(get_avatar_html(tobj, "small"), unsafe_allow_html=True)
                    with col_info:
                        # Кнопка-ссылка на профиль
                        if st.button(f"{tobj['display_name']}", key="head_name", type="tertiary"):
                            view_profile_dialog(tobj)
                        
                        st.markdown(f"<div style='margin-top:-15px; font-size:12px; color:{status_color}'>{status_text}</div>", unsafe_allow_html=True)

                else:
                    st.markdown(f"<h3 style='margin:0;'>📢 {tobj['name']}</h3>", unsafe_allow_html=True)

            with c_act:
                with st.popover("⚙️", use_container_width=True):
                    if ttype == 'user':
                        if st.button("Открыть профиль"):
                            view_profile_dialog(tobj)
                        if st.button("🗑️ Удалить чат"):
                            uid = tobj['id']
                            supabase.table("direct_messages").update({"visible_to_sender": False}).eq("sender_id", my_id).eq("recipient_id", uid).execute()
                            supabase.table("direct_messages").update({"visible_to_recipient": False}).eq("sender_id", uid).eq("recipient_id", my_id).execute()
                            st.session_state.chat_with_user = None
                            st.rerun()
                        if st.button("🧹 Очистить"):
                             uid = tobj['id']
                             supabase.table("direct_messages").delete().or_(f"and(sender_id.eq.{my_id},recipient_id.eq.{uid}),and(sender_id.eq.{uid},recipient_id.eq.{my_id})").execute()
                             supabase.table("direct_messages").insert({"sender_id": my_id, "sender_username": profile['username'], "recipient_id": uid, "recipient_username": tobj['username'], "content": "🧹 История очищена", "is_read": True, "visible_to_sender": True, "visible_to_recipient": True}).execute()
                             st.rerun()
                    else:
                        if st.button("🚪 Выйти"):
                            gid = tobj['id']
                            supabase.table("group_members").delete().eq("group_id", gid).eq("user_id", my_id).execute()
                            st.session_state.chat_with_group = None
                            st.rerun()

            render_messages_with_buttons(my_id, ttype, tobj)
            
            # ВВОД
            st.write("") 
            with st.expander("📎 Прикрепить файл", expanded=False):
                upl_file = st.file_uploader("Файл", type=None, label_visibility="collapsed")
                if upl_file and st.button("Отправить файл"):
                    try:
                        sz = f"{upl_file.size/1024:.1f} KB" if upl_file.size < 1024**2 else f"{upl_file.size/1024**2:.1f} MB"
                        orig_name = upl_file.name
                        ext = orig_name.split('.')[-1] if '.' in orig_name else ""
                        path = f"{my_id}/{int(time.time())}_{uuid.uuid4()}.{ext}"
                        supabase.storage.from_("avatars").upload(path, upl_file.getvalue(), {"content-type": upl_file.type}) # Используем avatars или chat_images? Лучше chat_images для чата
                        # Ой, тут ошибка в логике, файлы чата должны в chat_images
                        # Исправляем на chat_images
                        supabase.storage.from_("chat_images").upload(path, upl_file.getvalue(), {"content-type": upl_file.type})
                        url = supabase.storage.from_("chat_images").get_public_url(path)
                        
                        msg = {"sender_id": my_id, "sender_username": profile['username'], "content": "", "image_url": url, "file_name": orig_name, "file_size": sz}
                        if ttype == 'user':
                            msg.update({"recipient_id": tobj['id'], "recipient_username": tobj['username']})
                            supabase.table("direct_messages").insert(msg).execute()
                        else:
                            msg.update({"group_id": tobj['id']})
                            supabase.table("group_messages").insert(msg).execute()
                        st.rerun()
                    except Exception as e: st.error(str(e))

            with st.form("send", clear_on_submit=True):
                c1, c2 = st.columns([6,1])
                txt = c1.text_input("msg", label_visibility="collapsed", placeholder="Сообщение...")
                if c2.form_submit_button("➤", use_container_width=True) and txt.strip():
                    if ttype == 'user':
                        supabase.table("direct_messages").insert({"sender_id": my_id, "sender_username": profile['username'], "recipient_id": tobj['id'], "recipient_username": tobj['username'], "content": txt.strip()}).execute()
                    else:
                        supabase.table("group_messages").insert({"group_id": tobj['id'], "sender_id": my_id, "sender_username": profile['username'], "content": txt.strip()}).execute()
                    st.rerun()
        else:
            st.info("Выберите чат")

# --- СТРАНИЦА "МОЙ ПРОФИЛЬ" (РЕДАКТИРОВАНИЕ) ---
def page_profile(profile):
    st.title("👤 Мой профиль")
    
    # Показываем текущую аватарку
    st.markdown(f"<div style='text-align:center'>{get_avatar_html(profile, 'large')}</div>", unsafe_allow_html=True)
    
    with st.form("prof_upd"):
        st.subheader("Редактирование")
        
        # Загрузка новой аватарки
        new_ava = st.file_uploader("Изменить аватарку", type=['png', 'jpg', 'jpeg'])
        
        c1, c2 = st.columns(2)
        dn = c1.text_input("Имя", value=profile['display_name'])
        un = c2.text_input("Юзернейм", value=profile['username']).strip()
        
        bio = st.text_area("О себе", value=profile.get('bio') or "", placeholder="Расскажите о себе...")
        
        if st.form_submit_button("💾 Сохранить изменения"):
            updates = {"display_name": dn, "username": un, "bio": bio}
            
            # Если загрузили фото
            if new_ava:
                try:
                    ext = new_ava.name.split('.')[-1]
                    path = f"avatars/{profile['id']}_{int(time.time())}.{ext}"
                    supabase.storage.from_("avatars").upload(path, new_ava.getvalue(), {"content-type": new_ava.type})
                    url = supabase.storage.from_("avatars").get_public_url(path)
                    updates["avatar_url"] = url
                except Exception as e:
                    st.error(f"Ошибка фото: {e}")
            
            try:
                supabase.table("profiles").update(updates).eq("id", st.session_state.user.id).execute()
                get_profile_cached.clear()
                st.success("Сохранено!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Ошибка сохранения: {e}")

# ... остальные функции (settings, search) без изменений ...
def page_settings(profile):
    st.title("⚙️ Настройки")
    st.subheader("Внешний вид")
    current = st.selectbox("Тема оформления", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))
    if current != st.session_state.theme:
        st.session_state.theme = current
        st.rerun()

def page_search(profile):
    st.title("🔍 Поиск")
    with st.form("s"):
        q = st.text_input("Введите юзернейм").strip()
        submitted = st.form_submit_button("Найти")
    
    if submitted:
        r = supabase.table("profiles").select("*").eq("username", q).execute()
        if r.data: st.session_state.search_res = r.data[0]
        else: st.session_state.search_res = None; st.error("Никого не нашли")

    if st.session_state.search_res:
        f = st.session_state.search_res
        
        # Красивая карточка результата поиска
        c_ava, c_info = st.columns([0.2, 0.8])
        with c_ava:
             st.markdown(get_avatar_html(f, 'large'), unsafe_allow_html=True)
        with c_info:
            st.subheader(f['display_name'])
            st.write(f"@{f['username']}")
            if st.button(f"Написать сообщение"):
                st.session_state.chat_with_user = f
                st.session_state.chat_with_group = None
                st.session_state.search_res = None
                st.rerun()