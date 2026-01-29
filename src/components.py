# src/components.py
import streamlit as st
from src.database import supabase, toggle_reaction
from src.config import THEMES
from datetime import datetime, timedelta, timezone

# --- СПИСОК ЭМОДЗИ (30+ ШТУК) ---
TOP_EMOJIS = ["❤️", "🔥", "🤡", "🍌", "🤨"] # Первые 5 (видимые сразу)
EXTRA_EMOJIS = [
    "👍", "👎", "😱", "💩", "🥰", "🤯", "🤔", "🤬", 
    "👏", "🎉", "🤮", "🤧", "🥴", "🌚", "🗿", "⚡",
    "💯", "🏆", "💔", "😐", "🥱", "😭", "🙏", "🕊️",
    "🦄", "🍺", "🥂", "🍾", "🍕", "🍔"
]

# --- ДИАЛОГИ ---
@st.dialog("Просмотр изображения")
def view_image_dialog(url, filename):
    st.image(url, use_container_width=True, caption=filename)
    st.markdown(f"[⬇️ Скачать оригинал]({url})")

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def format_msg_time(iso_str):
    if not iso_str: return "", ""
    dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    dt = dt.astimezone(timezone(timedelta(hours=3)))
    time_str = dt.strftime("%H:%M")
    now = datetime.now(timezone(timedelta(hours=3)))
    if dt.date() == now.date(): date_label = "Сегодня"
    elif dt.date() == (now - timedelta(days=1)).date(): date_label = "Вчера"
    else:
        months = ["", "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        date_label = f"{dt.day} {months[dt.month]}"
    return time_str, date_label

def is_image_file(filename):
    if not filename: return False
    ext = filename.split('.')[-1].lower()
    return ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']

def get_reactions_html(reactions_json, my_id):
    """Генерирует HTML для отображения реакций под сообщением"""
    if not reactions_json: return ""
    
    html = '<div class="reactions-container">'
    for emoji, user_ids in reactions_json.items():
        if not user_ids: continue
        count = len(user_ids)
        # Если я лайкнул - добавляем класс active
        is_active = "reaction-active" if my_id in user_ids else ""
        html += f'<div class="reaction-bubble {is_active}">{emoji} {count}</div>'
    html += '</div>'
    return html

@st.fragment(run_every=5)
def render_messages_with_buttons(my_id, target_type, target_obj):
    messages = []
    
    table_name = "direct_messages" if target_type == 'user' else "group_messages"
    
    # 1. Загрузка
    if target_type == 'user':
        target_id = target_obj['id']
        try: 
            supabase.table("direct_messages").update({"is_read": True})\
                .eq("recipient_id", my_id).eq("sender_id", target_id).eq("is_read", False).execute()
        except: pass
        
        try:
            res = supabase.table("direct_messages").select("*")\
                .or_(f"and(sender_id.eq.{my_id},recipient_id.eq.{target_id},visible_to_sender.eq.true),and(sender_id.eq.{target_id},recipient_id.eq.{my_id},visible_to_recipient.eq.true)")\
                .order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass
    else:
        gid = target_obj['id']
        try:
            res = supabase.table("group_messages").select("*").eq("group_id", gid).order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass

    if not messages:
        st.caption("Нет сообщений")
        return

    messages.reverse()
    last_date_label = None

    # 2. Отрисовка
    with st.container(height=500, border=False):
        for m in messages:
            time_str, date_label = format_msg_time(m['created_at'])
            
            if date_label != last_date_label:
                st.markdown(f'<div style="display:flex;justify-content:center;margin:15px 0 10px 0;"><div style="background-color:rgba(128,128,128,0.2);color:rgba(255,255,255,0.8);padding:4px 12px;border-radius:12px;font-size:12px;font-weight:500;">{date_label}</div></div>', unsafe_allow_html=True)
                last_date_label = date_label

            sender_id = m.get('sender_id') 
            is_me = (sender_id == my_id)
            
            # --- СБОРКА КОНТЕНТА ---
            bubble_inner_html = ""
            file_url = m.get('image_url')
            file_name = m.get('file_name')
            file_size = m.get('file_size')
            
            is_image = False
            check_name = file_name if file_name else (file_url if file_url else "")

            if file_url:
                if is_image_file(check_name):
                    is_image = True
                    bubble_inner_html += f'<img src="{file_url}" class="bubble-image">'
                else:
                    display_name = file_name if file_name else "Файл"
                    display_size = file_size if file_size else "Скачать"
                    icon_arrow = "↓" 
                    bubble_inner_html += f'<a href="{file_url}" target="_blank" download class="tg-file-card"><div class="tg-file-icon">{icon_arrow}</div><div class="tg-file-info"><div class="tg-file-name">{display_name}</div><div class="tg-file-size">{display_size}</div></div></a>'
            
            if m.get('content'):
                style_prefix = "margin-top: 4px;" if file_url else ""
                bubble_inner_html += f'<div class="bubble-text" style="{style_prefix}">{m["content"]}</div>'
            
            # Реакции
            reactions_html = get_reactions_html(m.get('reactions'), my_id)
            bubble_inner_html += reactions_html
            
            status_icon = ""
            if is_me and target_type == 'user':
                status_icon = "✓✓" if m.get('is_read') else "✓"
            is_edited = "(ред.)" if m.get('is_edited') else ""
            
            meta_html = f'<div class="msg-meta">{time_str} {is_edited} {status_icon}</div>'

            # --- ФОРМИРОВАНИЕ КОЛОНОК ---
            if is_me:
                col_spacer, col_bubble, col_menu = st.columns([0.2, 0.7, 0.1])
                with col_bubble:
                    html = f'<div style="display: flex; justify-content: flex-end;"><div class="bubble bubble-me">{bubble_inner_html}{meta_html}</div></div>'
                    st.markdown(html, unsafe_allow_html=True)
            else:
                col_bubble, col_menu, col_spacer = st.columns([0.7, 0.1, 0.2])
                with col_bubble:
                    sender_label_html = ""
                    if target_type == 'group':
                        current_theme = st.session_state.get("theme", "Midnight Blue")
                        primary_col = THEMES.get(current_theme, {}).get('primary', '#3b82f6')
                        name = m.get('sender_username', 'User')
                        sender_label_html = f"<div class='bubble-text' style='padding-bottom: 0; font-size:11px;font-weight:bold;color:{primary_col};'>{name}</div>"
                    html = f'<div style="display: flex; justify-content: flex-start;"><div class="bubble bubble-other">{sender_label_html}{bubble_inner_html}{meta_html}</div></div>'
                    st.markdown(html, unsafe_allow_html=True)

            # --- МЕНЮ ДЕЙСТВИЙ (ОБЩЕЕ) ---
            with col_menu:
                # В Телеграме иконка меню для сообщений обычно невидимая или галочка, здесь используем popover
                with st.popover("⋮", use_container_width=True):
                    
                    # 1. ПАНЕЛЬ РЕАКЦИЙ (TOP 5 + STRETCH)
                    # Создаем 5 колонок для топ эмодзи
                    cols_top = st.columns(5)
                    
                    def reaction_btn(col, emo, msg_id):
                        current_r = m.get('reactions') or {}
                        is_selected = my_id in current_r.get(emo, [])
                        # Визуально выделяем выбранные (но в popover стиль ограничен)
                        label = f"✅ {emo}" if is_selected else emo
                        if col.button(label, key=f"r_{msg_id}_{emo}", use_container_width=True):
                            toggle_reaction(table_name, msg_id, my_id, emo)
                            st.rerun()

                    # Рисуем первые 5
                    for i, emo in enumerate(TOP_EMOJIS):
                        reaction_btn(cols_top[i], emo, m['id'])
                    
                    # СТРЕЛОЧКА ВНИЗ (Expander для остальных)
                    with st.expander("Все реакции 🔽"):
                        # Сетка для остальных эмодзи (по 5 в ряд)
                        rows = [EXTRA_EMOJIS[i:i + 5] for i in range(0, len(EXTRA_EMOJIS), 5)]
                        for row in rows:
                            cols = st.columns(5)
                            for idx, emo in enumerate(row):
                                reaction_btn(cols[idx], emo, m['id'])

                    st.divider()
                    
                    # 2. СПИСОК ДЕЙСТВИЙ (КАК НА СКРИНШОТЕ)
                    
                    # Reply
                    if st.button("↩️ Reply", key=f"rep_{m['id']}", use_container_width=True):
                        st.toast("Функция Reply скоро будет добавлена")
                    
                    # Copy
                    if st.button("📋 Copy", key=f"cpy_{m['id']}", use_container_width=True):
                         st.code(m['content'], language=None)
                    
                    # Open Photo (если есть)
                    if is_image:
                        if st.button("🖼️ Open Photo", key=f"view_{m['id']}", use_container_width=True):
                            view_image_dialog(file_url, file_name or "Image")

                    # Edit (Только свои)
                    if is_me:
                        if st.button("✏️ Edit", key=f"edt_{m['id']}", use_container_width=True):
                            st.session_state.edit_msg_id = m['id']
                            st.rerun()

                    # Delete (Только свои)
                    if is_me:
                        # Делаем кнопку красной через type="primary" (в Streamlit это акцентный цвет)
                        if st.button("🗑️ Delete", key=f"del_{m['id']}", type="primary", use_container_width=True):
                            supabase.table(table_name).delete().eq("id", m['id']).execute()
                            st.toast("Deleted")
                            st.rerun()