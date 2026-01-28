# src/styles.py
import streamlit as st
from src.config import THEMES

def inject_custom_css():
    if "theme" not in st.session_state:
        st.session_state.theme = "Midnight Blue"
        
    t = THEMES[st.session_state.theme]
    text_me = "#000000" if "Light" in st.session_state.theme else "#ffffff"
    text_other = "#000000" if "Light" in st.session_state.theme else "#e2e8f0"
    
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="css"] {{ font-family: 'Roboto', sans-serif; }}
        #MainMenu, footer {{visibility: hidden;}}
        .stApp {{ background-color: {t['bg_color']}; }}
        section[data-testid="stSidebar"] {{ background-color: {t['sidebar_bg']}; border-right: 1px solid {t['border']}; }}
        
        .stButton button {{ border-radius: 10px !important; border: none !important; background-color: {t['input_bg']} !important; color: {t['text_color']} !important; }}
        .stButton button:hover {{ filter: brightness(1.2); }}
        .stTextInput input {{ background-color: {t['input_bg']} !important; color: {t['text_color']} !important; border: 1px solid {t['border']} !important; border-radius: 12px !important; }}
        
        .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
        .stTabs [data-baseweb="tab"] {{ background-color: {t['input_bg']}; border-radius: 8px; padding: 5px 15px; color: {t['text_color']}; }}
        .stTabs [aria-selected="true"] {{ background-color: {t['primary']} !important; color: white !important; }}
        
        /* Стили пузырей */
        .bubble {{ 
            padding: 8px 14px; 
            border-radius: 16px; 
            font-size: 15px; 
            line-height: 1.5; 
            box-shadow: 0 1px 2px rgba(0,0,0,0.1); 
            display: inline-block; 
            max-width: 100%; 
            word-wrap: break-word; 
        }}
        .bubble-me {{ background: {t['bubble_me']}; color: {text_me}; border-bottom-right-radius: 2px; }}
        .bubble-other {{ background: {t['bubble_other']}; color: {text_other}; border-bottom-left-radius: 2px; }}
        
        .msg-meta {{ font-size: 11px; margin-top: 4px; display: flex; justify-content: flex-end; align-items: center; opacity: 0.7; gap: 5px; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)