import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="SmartPag - Distribuição & Conciliação",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilo para tela cheia e visual limpo
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        iframe {
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Carrega o HTML completo e interativo
html_path = os.path.join(os.path.dirname(__file__), "index.html")

if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=1200, scrolling=True)
else:
    st.error("Arquivo index.html não encontrado no diretório do projeto.")
