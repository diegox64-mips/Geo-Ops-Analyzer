# Em Home.py

import streamlit as st
from analyzer_app import run_analyzer_app
from mapper_app import run_mapper_app

# --- Configuração da Página ---
st.set_page_config(
    page_title="Central de Ferramentas",
    layout="wide"
)

# --- Controle de Navegação ---
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = 'home'

# Função para criar um botão de "Voltar"
def create_back_button():
    if st.button("⬅️ Voltar ao Menu Principal"):
        st.session_state.app_mode = 'home'
        st.rerun()

# --- Roteamento das Páginas ---
if st.session_state.app_mode == 'home':
    st.title("Central de Ferramentas de Análise de SVOs")
    st.markdown("### Escolha a ferramenta que deseja utilizar:")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔎 Analisador de SVOs Pendentes", use_container_width=True):
            st.session_state.app_mode = 'analyzer'
            st.rerun()

    with col2:
        if st.button("🗺️ Gerador de Mapas de Calor", use_container_width=True):
            st.session_state.app_mode = 'mapper'
            st.rerun()

elif st.session_state.app_mode == 'analyzer':
    create_back_button()
    st.markdown("---")
    run_analyzer_app()

elif st.session_state.app_mode == 'mapper':
    create_back_button()
    st.markdown("---")
    run_mapper_app()