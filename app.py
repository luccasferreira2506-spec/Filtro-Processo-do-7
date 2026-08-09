import streamlit as st
import re
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Painel Supremo do Sete V2.0", 
    page_icon="⚖️", 
    layout="wide"
)

# Inicializa variáveis globais de sessão
if "usuarios_cadastrados" not in st.session_state:
    senha_admin_padrao = st.secrets.get("SENHA_APP", "123456")
    st.session_state["usuarios_cadastrados"] = {
        "admin": senha_admin_padrao
    }

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

if "login_tempo" not in st.session_state:
    st.session_state["login_tempo"] = None

if "historicos_por_usuario" not in st.session_state:
    st.session_state["historicos_por_usuario"] = {}

if "conteudo_ativo" not in st.session_state:
    st.session_state["conteudo_ativo"] = None

if "origem_ativa" not in st.session_state:
    st.session_state["origem_ativa"] = ""

if "processos_lista" not in st.session_state:
    st.session_state["processos_lista"] = []

if "cabecalho_ativo" not in st.session_state:
    st.session_state["cabecalho_ativo"] = ""

# Controlo de expiração de sessão (1 hora de inatividade)
if st.session_state["usuario_logado"] and st.session_state["login_tempo"]:
    tempo_decorrido = (datetime.now() - st.session_state["login_tempo"]).total_seconds()
    if tempo_decorrido > 3600:
        st.session_state["usuario_logado"] = None
        st.session_state["login_tempo"] = None
        st.warning("⚠️ Sessão expirada após 1 hora de inatividade. Faça login novamente.")
        st.rerun()
    else:
        st.session_state["login_tempo"] = datetime.now()

# ==============================================================================
# 🔒 SISTEMA DE LOGIN E CONTROLE DE CONTAS EXCLUSIVAS
# ==============================================================================
if not st.session_state["usuario_logado"]:
    st.title("🔒 Acesso Restrito - Painel Supremo do Sete V2.0")
    st.write("Digite suas credenciais de acesso para entrar no sistema.")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        user_input = st.text_input("Utilizador:")
        pass_input = st.text_input("Palavra-passe:", type="password")
        
        if st.button("🔓 Entrar", type="primary", use_container_width=True):
            usuarios = st.session_state["usuarios_cadastrados"]
            if user_input in usuarios and usuarios[user_input] == pass_input:
                st.session_state["usuario_logado"] = user_input
                st.session_state["login_tempo"] = datetime.now()
