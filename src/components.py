# src/components.py
import streamlit as st
from src.database import supabase
from src.config import THEMES

@st.fragment(run_every=5)
def render_messages_with_buttons(my_id, target_type, target_obj):
    messages = []
    
    # Загрузка
    if target_type == 'user':
        target_id = target_obj['id']
        try: supabase.table("direct_messages").update({"is_read": True}).eq("recipient_id", my_id).eq("sender_id", target_id).eq("is_read", False).execute()
        except: pass
        try:
            res = supabase.table("direct_messages").select("*").or_(f"and(sender_id.eq.{my_id},recipient_id.eq.{target_id}),and(sender_id.eq.{target_id},recipient_id.eq.{my_id})").order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass
    else:
        gid = target_obj['id']
        try:
            res = supabase.table("group_messages").select("*").eq("group_id", gid).order("created_at", desc=True).limit(50).execute()
            messages = res.data
        except: pass

    if not messages:
        st.caption("Нет сообщений.")
        return

    messages.reverse()

    # Отрисовка
    with st.container(height=550, border=False):
        for m in messages:
            sender_id = m.get('sender_id') 
            is_me = (sender_id == my_id)
            content = m['content']
            
            status_icon = ""
            if is_me and target_type == 'user':
                status_icon = "✓✓" if m.get('is_read') else "✓"
            is_edited = "(ред.)" if m.get('is_edited') else ""
            
            if is_me:
                col_spacer, col_bubble, col_menu = st.columns([0.2, 0.7, 0.1])
                with col_bubble:
                    html = f'<div style="text-align:right;"><div class="bubble bubble-me" style="text-align:left;">{content}<div class="msg-meta" style="color:rgba(255,255,255,0.7);">{is_edited} {status_icon}</div></div></div>'
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
                col_bubble, col_spacer = st.columns([0.8, 0.2])
                with col_bubble:
                    sender_label = ""
                    if target_type == 'group':
                        primary_col = THEMES[st.session_state.theme]['primary']
                        name = m.get('sender_username', 'User')
                        sender_label = f"<div style='font-size:11px; font-weight:bold; color:{primary_col}; margin-bottom:2px;'>{name}</div>"
                    html = f'<div style="text-align:left;"><div class="bubble bubble-other">{sender_label}{content}<div class="msg-meta">{is_edited}</div></div></div>'
                    st.markdown(html, unsafe_allow_html=True)