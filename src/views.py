# src/views.py
import streamlit as st
import time
from src.database import supabase, get_chat_list_by_id, get_groups_by_id, get_unread_counts, get_profile_cached
from src.components import render_messages_with_buttons
from src.config import THEMES

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
                count = unread_counts.get(u['id'], 0)
                label = f"🔴 {count} | {u['display_name']}" if count > 0 else f"👤 {u['display_name']}"
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

    with c_right:
        ttype, tobj = None, None
        if st.session_state.chat_with_group: ttype, tobj = 'group', st.session_state.chat_with_group
        elif st.session_state.chat_with_user: ttype, tobj = 'user', st.session_state.chat_with_user
        
        if ttype:
            title = tobj['name'] if ttype == 'group' else tobj['display_name']
            st.markdown(f"<h3 style='margin-top:0;'>{title}</h3>", unsafe_allow_html=True)
            render_messages_with_buttons(my_id, ttype, tobj)
            
            st.write("") 
            if st.session_state.edit_msg_id:
                st.info("✏️ Редактирование")
                with st.form("edit"):
                    nt = st.text_input("Новый текст")
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Сохранить"):
                        table = "direct_messages" if ttype == 'user' else "group_messages"
                        supabase.table(table).update({"content": nt, "is_edited": True}).eq("id", st.session_state.edit_msg_id).execute()
                        st.session_state.edit_msg_id = None
                        st.rerun()
                    if c2.form_submit_button("Отмена"):
                        st.session_state.edit_msg_id = None
                        st.rerun()
            else:
                with st.form("send", clear_on_submit=True):
                    c_in, c_btn = st.columns([6, 1])
                    with c_in: txt = st.text_input("msg", label_visibility="collapsed", placeholder="Сообщение...")
                    with c_btn: 
                        if st.form_submit_button("➤", use_container_width=True) and txt.strip():
                            if ttype == 'user':
                                supabase.table("direct_messages").insert({
                                    "sender_id": my_id, "sender_username": profile['username'],
                                    "recipient_id": tobj['id'], "recipient_username": tobj['username'],
                                    "content": txt.strip()
                                }).execute()
                            else:
                                supabase.table("group_messages").insert({
                                    "group_id": tobj['id'], "sender_id": my_id, "sender_username": profile['username'],
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
        un = st.text_input("Юзернейм (@)", value=profile['username']).strip()
        if st.form_submit_button("Сохранить"):
            try:
                supabase.table("profiles").update({"display_name": dn, "username": un}).eq("id", st.session_state.user.id).execute()
                get_profile_cached.clear()
                st.success("Сохранено!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Ошибка: {e}")

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
        st.success(f"Нашли: {f['display_name']}")
        if st.button(f"Написать @{f['username']}"):
            st.session_state.chat_with_user = f
            st.session_state.chat_with_group = None
            st.session_state.search_res = None
            st.rerun()