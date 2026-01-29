# src/styles.py
import streamlit as st
from src.config import THEMES

def inject_custom_css():
    # 1. Загрузка темы
    if "theme" not in st.session_state:
        st.session_state.theme = "Midnight Blue (Default)"
    
    if st.session_state.theme not in THEMES:
        st.session_state.theme = "Midnight Blue (Default)"

    t = THEMES[st.session_state.theme]
    
    text_me = t.get('msg_text_me', '#ffffff')
    text_other = t.get('msg_text_other', '#ffffff')
    
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        
        /* === ГЛОБАЛЬНЫЕ СТИЛИ === */
        html, body, [class*="css"], .stApp {{
            font-family: 'Roboto', sans-serif;
            color: {t['text_color']} !important;
            background-color: {t['bg_color']};
        }}
        
        h1, h2, h3, h4, h5, h6, p, div, span, label {{
            color: {t['text_color']} !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: {t['sidebar_bg']};
            border-right: 1px solid {t['border']};
        }}
        section[data-testid="stSidebar"] * {{
            color: {t['text_color']} !important;
        }}
        
        #MainMenu, footer {{visibility: hidden;}}
        
        /* === ИНПУТЫ И КНОПКИ === */
        .stTextInput input, .stTextArea textarea {{
            background-color: {t['input_bg']} !important;
            color: {t['text_color']} !important;
            border: 1px solid {t['border']} !important;
            border-radius: 12px !important;
        }}
        ::placeholder {{
            color: {t['text_color']} !important;
            opacity: 0.5;
        }}

        .stButton button {{
            border-radius: 10px !important;
            border: none !important;
            background-color: {t['input_bg']} !important;
            color: {t['text_color']} !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }}
        .stButton button:hover {{
            filter: brightness(1.1);
            transform: translateY(-1px);
        }}
        
        .stButton button[kind="primary"] {{
            background-color: {t['primary']} !important;
            color: #ffffff !important; 
        }}
        .stButton button[kind="primary"] p {{
            color: #ffffff !important;
        }}
        
        /* === АВАТАРКИ === */
        .user-avatar {{
            width: 110px;
            height: 110px;
            min-width: 110px;
            min-height: 110px;
            border-radius: 50%;
            object-fit: cover !important;
            object-position: center !important;
            border: 3px solid {t['border']};
            display: block;
            margin: 0 auto 10px auto;
            background-color: {t['input_bg']};
        }}
        
        .user-avatar-small {{
            width: 42px;
            height: 42px;
            min-width: 42px;
            min-height: 42px;
            border-radius: 50%;
            object-fit: cover !important;
            object-position: center !important;
            vertical-align: middle;
            border: 1px solid {t['border']};
            background-color: {t['input_bg']};
        }}
        
        .avatar-placeholder {{
            width: 110px;
            height: 110px;
            min-width: 110px;
            min-height: 110px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 44px;
            font-weight: bold;
            color: white !important;
            margin: 0 auto 10px auto;
            text-transform: uppercase;
            border: 3px solid {t['border']};
        }}
        
        .avatar-placeholder-small {{
            width: 42px;
            height: 42px;
            min-width: 42px;
            min-height: 42px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
            color: white !important;
            text-transform: uppercase;
        }}

        /* === ПУЗЫРИ СООБЩЕНИЙ === */
        .bubble {{
            border-radius: 16px;
            font-size: 15px;
            line-height: 1.5;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            
            display: inline-block; 
            width: fit-content;    
            max-width: 85%;       
            
            word-wrap: break-word;
            overflow: hidden;
        }}
        
        .bubble-text {{ padding: 8px 14px; }}

        .bubble-image {{
            display: block;
            width: 100%;
            max-width: 350px;
            height: auto;
            object-fit: cover;
            cursor: zoom-in;
            transition: opacity 0.2s;
        }}
        .bubble-image:hover {{ opacity: 0.9; }}
        
        /* === ФАЙЛЫ === */
        .tg-file-card {{
            display: flex;
            align-items: center;
            padding: 10px;
            text-decoration: none !important;
            transition: background-color 0.2s;
            max-width: 320px; 
            gap: 12px;
        }}
        
        .tg-file-icon {{
            width: 42px;
            height: 42px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
            flex-shrink: 0;
        }}
        
        .tg-file-info {{
            display: flex;
            flex-direction: column;
            overflow: hidden;
            justify-content: center;
        }}
        
        .tg-file-name {{
            font-weight: 600;
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.2;
            margin-bottom: 2px;
        }}
        
        .tg-file-size {{
            font-size: 12px;
            opacity: 0.7;
            line-height: 1;
        }}

        /* === РЕАКЦИИ (SUPER TIGHT) === */
        .reactions-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            
            /* 1. Максимально прижимаем к содержимому сверху */
            margin-top: 2px;
            
            /* 2. УБИРАЕМ ОТСТУП СНИЗУ (было 3-4px, стало 0px) */
            padding: 0 8px 0px 8px;   
        }}
        
        .reaction-bubble {{
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            
            padding: 0px 6px; 
            
            font-size: 12px;
            line-height: 1.6;
            font-weight: 500;
            
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 3px;
        }}
        
        .reaction-bubble:hover {{
            border-color: {t['primary']};
            background-color: rgba(255, 255, 255, 0.3);
        }}
        
        .reaction-active {{
            background-color: {t['primary']} !important;
            color: white !important;
            border-color: {t['primary']};
        }}
        
        /* === ЦВЕТА И МЕТА (ВРЕМЯ) === */
        .bubble-me {{
            background: {t['bubble_me']};
            border-bottom-right-radius: 2px;
        }}
        .bubble-me, .bubble-me * {{ color: {text_me} !important; }}
        
        .bubble-me .tg-file-icon {{
            background-color: rgba(255, 255, 255, 0.25);
            color: {text_me} !important;
        }}
        
        /* Специфика реакций на моих сообщениях */
        .bubble-me .reaction-bubble {{
            background-color: rgba(0, 0, 0, 0.1); 
        }}
        .bubble-me .reaction-active {{
            background-color: rgba(255, 255, 255, 0.3) !important;
            border: 1px solid rgba(255, 255, 255, 0.5);
        }}
        
        .bubble-other {{
            background: {t['bubble_other']};
            border-bottom-left-radius: 2px;
        }}
        .bubble-other, .bubble-other * {{ color: {text_other} !important; }}
        
        .bubble-other .tg-file-icon {{
            background-color: {t['primary']}; 
            color: #ffffff !important;
        }}
        
        /* Специфика реакций на чужих сообщениях */
        .bubble-other .reaction-bubble {{
            background-color: rgba(0, 0, 0, 0.05);
        }}
        
        /* --- ВРЕМЯ (СЖИМАЕМ ОТСТУП) --- */
        .msg-meta {{
            font-size: 11px;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            opacity: 0.7;
            gap: 5px;
            
            /* Уменьшил нижний отступ с 6px до 3px */
            padding: 0 10px 3px 10px; 
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)