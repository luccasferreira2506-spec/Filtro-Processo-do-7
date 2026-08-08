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
        corpo = conteudo_texto

    blocos = re.split(r'\n(?=PROCESSO:)', corpo)
    processos_validos = []
    txt_filtrado_blocos = []
    removidos = 0

    for bloco in blocos:
        if not bloco.strip():
            continue
        
        polo_ativo_match = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
        if polo_ativo_match:
            trecho_ativo = polo_ativo_match.group(1).lower()
            if any(termo in trecho_ativo for termo in ["ocultada", "ocultado", "res. 121"]):
                removidos += 1
                continue

        txt_filtrado_blocos.append(bloco)
        
        proc = {
            "numero": extrair_campo(r'PROCESSO:\s*(.*)', bloco),
            "link": extrair_campo(r'LINK:\s*(.*)', bloco, ""),
            "tribunal": extrair_campo(r'TRIBUNAL:\s*(.*)', bloco),
            "classe": extrair_campo(r'CLASSE:\s*(.*)', bloco),
            "valor": extrair_campo(r'VALOR:\s*(.*)', bloco),
            "polo_ativo_nome": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "polo_ativo_doc": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*DOC:\s*(.*?)\n', bloco, "Sem CPF/DOC"),
            "polo_ativo_renda": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*RENDA:\s*(.*?)\n', bloco),
            "polo_passivo_nome": extrair_campo(r'POLO PASSIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "bloco_completo": bloco
        }
        processos_validos.append(proc)

    texto_final = cabecalho + "".join(txt_filtrado_blocos)
    return texto_final, processos_validos, len(blocos), len(processos_validos), removidos

# ==============================================================================
# 💻 INTERFACE PRINCIPAL COM ABAS
# ==============================================================================
st.title("⚖️ Sistema Jurídico de Consultas e Gestão")

# CRIAÇÃO DAS ABAS
tab_consulta, tab_anotacoes = st.tabs(["🔍 Consultar & Filtrar Processos", "📝 Anotações do Advogado"])

# ------------------------------------------------------------------------------
# ABA 1: CONSULTA E FILTRO DE PROCESSOS
# ------------------------------------------------------------------------------
with tab_consulta:
    st.write("Selecione o estado, digite o número da OAB e realize a consulta direta ao Telegram.")

    col_uf, col_num, col_btn = st.columns([1, 2, 1.5])
    estados = ["PE", "SP", "RJ", "MG", "BA", "CE", "PR", "RS", "SC", "AC", "AL", "AM", "AP", "DF", "ES", "GO", "MA", "MS", "MT", "PA", "PB", "PI", "RN", "RO", "RR", "SE", "TO"]

    with col_uf:
        uf_selecionada = st.selectbox("Estado (UF)",
