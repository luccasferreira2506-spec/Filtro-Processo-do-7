import streamlit as st
import re
import asyncio
from telethon import TelegramClient

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Painel de Processos e Anotações", page_icon="⚖️", layout="wide")

# Inicializa o armazenamento das anotações em memória
if "anotacoes_advogados" not in st.session_state:
    st.session_state["anotacoes_advogados"] = []

# ==============================================================================
# 🔒 SISTEMA DE PROTEÇÃO POR SENHA
# ==============================================================================
def verificar_senha():
    if "senha_correta" not in st.session_state:
        st.session_state["senha_correta"] = False

    if st.session_state["senha_correta"]:
        return True

    st.title("🔒 Acesso Restrito ao Sistema")
    st.write("Introduza a senha para aceder ao painel de consultas e processos.")

    with st.form("form_login"):
        senha_input = st.text_input("Senha de Acesso:", type="password")
        btn_login = st.form_submit_button("Entrar no Sistema", type="primary")

        if btn_login:
            senha_correta = st.secrets.get("SENHA_APP", "123456")
            if senha_input == senha_correta:
                st.session_state["senha_correta"] = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta! Tente novamente.")

    return False

if not verificar_senha():
    st.stop()

# ==============================================================================
# ⚙️ CREDENCIAIS DO TELEGRAM (Substitua pelos seus dados)
# ==============================================================================
API_ID = 12345678                  # Seu API ID (número)
API_HASH = 'SEU_API_HASH_AQUI'     # Seu API Hash (texto)
BOT_USERNAME = 'nome_do_bot'       # Username do Bot (sem o @)
GRUPO_IDENTIFICADOR = 'nome_grupo' # Username do Grupo ou ID

# ==============================================================================
# 🤖 FUNÇÃO DE CONEXÃO COM O TELEGRAM
# ==============================================================================
async def buscar_arquivo_no_grupo(comando_oab):
    client = TelegramClient('sessao_telegram', API_ID, API_HASH)
    await client.start()

    grupo = await client.get_entity(GRUPO_IDENTIFICADOR)
    mensagem_enviada = await client.send_message(grupo, comando_oab)
    
    arquivo_bytes = None
    
    for _ in range(40):
        await asyncio.sleep(1)
        async for message in client.iter_messages(grupo, limit=5):
            if message.sender and message.sender.username == BOT_USERNAME:
                if message.file and message.id > mensagem_enviada.id:
                    arquivo_bytes = await client.download_media(message.file, file=bytes)
                    break
        if arquivo_bytes:
            break

    await client.disconnect()
    return arquivo_bytes

# ==============================================================================
# 🧠 FILTRAGEM E TRATAMENTO DOS PROCESSOS
# ==============================================================================
def extrair_campo(padrao, texto, padrao_padrao="Não informado"):
    match = re.search(padrao, texto, re.IGNORECASE)
    return match.group(1).strip() if match else padrao_padrao

def processar_relatorio(conteudo_texto):
    pos_primeiro = conteudo_texto.find('PROCESSO:')
    if pos_primeiro != -1:
        cabecalho = conteudo_texto[:pos_primeiro]
        corpo = conteudo_texto[pos_primeiro:]
    else:
        cabecalho = ""
