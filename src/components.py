# src/components.py
import streamlit as st
from src.database import supabase
from src.config import THEMES
from datetime import datetime, timedelta, timezone

def format_msg_time(iso_str):
    """
    Превращает строку времени из БД в:
    1. time_str: "14:30" (для пузыря)
    2. date_label: "Сегодня", "Вчера" или "28 янв" (для разделителя)
    """
    # Парсим дату из строки ISO. Заменяем Z на +00:00 для Python < 3.11
    dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    
    # Конвертируем в часовой пояс пользователя 
    # (Пока ставим фиксировано UTC+3 для Москвы/Минска, так как браузерное время получить сложно)
    dt = dt.astimezone(timezone(timedelta(hours=3)))
    
    # Время для сообщения
    time_str = dt.strftime("%H:%M")
    
    # Дата для разделителя
    now = datetime.now(timezone(timedelta(hours=3)))
    
    if dt.date() == now.date():
        date_label = "Сегодня"
    elif dt.date() == (now - timedelta(days=1)).date():
        date_label = "Вчера"
    else:
        # Русские названия месяцев
        months = ["", "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        date_label = f"{dt.day} {months[dt.month]}"
        
    return time_str, date_label

@st.fragment(run_every=5)
def render_messages_with_buttons(my_id, target_type, target_obj):
    messages = []
    
    # 1. Загрузка сообщений из базы
    if target_type == 'user':
        target_id = target_obj['id']
        try: 
            # Отмечаем прочитанным
            supabase.table("direct_messages").update({"is_read": True})\
                .eq("recipient_id", my_id).eq("sender_id", target_id).eq("is_read", False).execute()
        except: pass
        
        try:
            res = supabase.table("direct_messages").select("*")\
                .or_(f"and(sender_id.eq.{my_id},recipient_id.eq.{target_id}),and(sender_id.eq.{target_id},recipient_id.eq.{my_id})")\
                .order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass
    else:
        # Группы
        gid = target_obj['id']
        try:
            res = supabase.table("group_messages").select("*").eq("group_id", gid).order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass

    if not messages:
        st.caption("Нет сообщений.")
        return

    # Разворачиваем (получаем [Старое ... Новое]), чтобы идти сверху вниз
    messages.reverse()

    # Переменная для отслеживания смены даты
    last_date_label = None

    # 2. Отрисовка
    with st.container(height=550, border=False):
        for m in messages:
            # Обработка времени
            time_str, date_label = format_msg_time(m['created_at'])
            
            # --- РАЗДЕЛИТЕЛЬ ДАТ ---
            if date_label != last_date_label:
                st.markdown(f"""
                <div style="display: flex; justify-content: center; margin: 15px 0 10px 0;">
                    <div style="
                        background-color: rgba(128, 128, 128, 0.2); 
                        color: rgba(255, 255, 255, 0.8); 
                        padding: 4px 12px; 
                        border-radius: 12px; 
                        font-size: 12px; 
                        font-weight: 500;">
                        {date_label}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                last_date_label = date_label

            # --- САМО СООБЩЕНИЕ ---
            sender_id = m.get('sender_id') 
            is_me = (sender_id == my_id)
            content = m['content']
            
            # Мета-информация (время + галочки)
            status_icon = ""
            if is_me and target_type == 'user':
                status_icon = "✓✓" if m.get('is_read') else "✓"
            is_edited = "(ред.)" if m.get('is_edited') else ""
            
            # Сборка подписи (14:30 ✓✓)
            meta_html = f'<span style="margin-right:5px; font-size:10px; opacity:0.8;">{time_str}</span>{is_edited} {status_icon}'
            
            if is_me:
                # МОЁ
                col_spacer, col_bubble, col_menu = st.columns([0.2, 0.7, 0.1])
                with col_bubble:
                    html = f'<div style="text-align:right;"><div class="bubble bubble-me" style="text-align:left;">{content}<div class="msg-meta" style="color:rgba(255,255,255,0.9);">{meta_html}</div></div></div>'
                    st.markdown(html, unsafe_allow_html=True)
                with col_menu:
                    with st.popover("⋮", use_container_width=True):
                        if st.button("✏️", key=f"ed_{m['id']}"):
                            st.session_state.edit_msg_id = m['id']
                            st.rerun()
                        if st.button("🗑️", key=f"del_{m['id']}"):
                            table = "direct_messages" if target_type == 'user' else "group_messages"
                            supabase.table(table).delete().eq("id", m['id']).execute()
                            st.toast("Удалено")
                            st.rerun()
            else:
                # ЧУЖОЕ
                col_bubble, col_spacer = st.columns([0.8, 0.2])
                with col_bubble:
                    sender_label = ""
                    if target_type == 'group':
                        current_theme = st.session_state.get("theme", "Midnight Blue")
                        primary_col = THEMES[current_theme]['primary']
                        name = m.get('sender_username', 'User')
                        sender_label = f"<div style='font-size:11px; font-weight:bold; color:{primary_col}; margin-bottom:2px;'>{name}</div>"
                    
                    html = f'<div style="text-align:left;"><div class="bubble bubble-other">{sender_label}{content}<div class="msg-meta">{meta_html}</div></div></div>'
                    st.markdown(html, unsafe_allow_html=True)