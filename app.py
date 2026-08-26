import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="SmartPag - Distribuição & Conciliação",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilo para tela cheia, eliminando margens e espaços em branco vazios
st.markdown(
    """
    <style>
        #MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
        }
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        iframe {
            width: 100% !important;
            min-height: 98vh !important;
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
    components.html(html_content, height=1600, scrolling=True)
else:
    st.error("Arquivo index.html não encontrado no diretório do projeto.")
