import streamlit as st
import re
import asyncio
from telethon import TelegramClient

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Painel de Processos e Consulta OAB", page_icon="⚖️", layout="wide")

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
            # Procura a senha definida no Secrets do Streamlit, senão usa a senha padrão '123456'
            senha_correta = st.secrets.get("SENHA_APP", "123456")
            if senha_input == senha_correta:
                st.session_state["senha_correta"] = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta! Tente novamente.")

    return False

# Interrompe o carregamento se não estiver autenticado
if not verificar_senha():
    st.stop()

# ==============================================================================
# ⚙️ CREDENCIAIS DO TELEGRAM (Substitua pelos seus dados)
# ==============================================================================
API_ID = 12345678                  # Seu API ID (número) obtido no my.telegram.org
API_HASH = 'SEU_API_HASH_AQUI'     # Seu API Hash (texto) obtido no my.telegram.org
BOT_USERNAME = 'nome_do_bot'       # Username do Bot (sem o @)
GRUPO_IDENTIFICADOR = 'nome_grupo' # Username do Grupo (ex: 'meu_grupo') ou ID numérico

# ==============================================================================
# 🤖 FUNÇÃO DE CONEXÃO COM O TELEGRAM
# ==============================================================================
async def buscar_arquivo_no_grupo(comando_oab):
    client = TelegramClient('sessao_telegram', API_ID, API_HASH)
    await client.start()

    # Localiza o grupo no Telegram
    grupo = await client.get_entity(GRUPO_IDENTIFICADOR)

    # Envia o comando estritamente formatado (ex: /oab sp12345)
    mensagem_enviada = await client.send_message(grupo, comando_oab)
    
    arquivo_bytes = None
    
    # Aguarda a resposta do bot com o ficheiro (tempo limite: 40 segundos)
    for _ in range(40):
        await asyncio.sleep(1)
        async for message in client.iter_messages(grupo, limit=5):
            # Valida se a mensagem veio do bot, contém um ficheiro e é resposta à nossa consulta
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
        
        # Filtra e remove caso o Polo Ativo esteja ocultado
        polo_ativo_match = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
        if polo_ativo_match:
            trecho_ativo = polo_ativo_match.group(1).lower()
            if any(termo in trecho_ativo for termo in ["ocultada", "ocultado", "res. 121"]):
                removidos += 1
                continue

        txt_filtrado_blocos.append(bloco)
        
        # Extrai os dados para montar os cards
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
# 💻 INTERFACE PRINCIPAL DO PAINEL
# ==============================================================================
st.title("⚖️ Painel de Consulta OAB e Filtro de Processos")
st.write("Selecione o estado, digite o número da OAB e realize a consulta direta ao Telegram.")

# --- ENTRADA DE DADOS: UF E NÚMERO OAB ---
col_uf, col_num, col_btn = st.columns([1, 2, 1.5])

estados = ["PE", "SP", "RJ", "MG", "BA", "CE", "PR", "RS", "SC", "AC", "AL", "AM", "AP", "DF", "ES", "GO", "MA", "MS", "MT", "PA", "PB", "PI", "RN", "RO", "RR", "SE", "TO"]

with col_uf:
    uf_selecionada = st.selectbox("Estado (UF)", estados)

with col_num:
    numero_oab = st.text_input("Número da OAB", placeholder="Ex: 12345 ou 49892")

with col_btn:
    st.write("") 
    st.write("")
    btn_buscar = st.button("🚀 Consultar no Telegram", type="primary", use_container_width=True)

# Variável para armazenar o conteúdo do relatório
conteudo_texto = None

# SE O UTILIZADOR CLICOU NO BOTÃO DE CONSULTA
if btn_buscar:
    if not numero_oab.strip():
        st.warning("⚠️ Digite o número da OAB.")
    else:
        # Garante que no número só existem dígitos
        apenas_numeros = re.sub(r'\D', '', numero_oab)
        
        # Monta o comando exato exigido pelo bot
        comando_formatado = f"/oab {uf_selecionada.lower()}{apenas_numeros}"
        
        st.info(f"Comando gerado com segurança: `{comando_formatado}`")

        with st.spinner("A conectar ao Telegram e a aguardar resposta do Bot..."):
            try:
                # Executa a chamada assíncrona do Telegram
                bytes_recebidos = asyncio.run(buscar_arquivo_no_grupo(comando_formatado))
                
                if bytes_recebidos:
                    conteudo_texto = bytes_recebidos.decode('utf-8', errors='ignore')
                    st.success("✅ Ficheiro de processos recebido com sucesso!")
                else:
                    st.error("❌ O Bot não enviou o ficheiro no tempo limite. Confirme o comando e se o Bot está ativo no grupo.")
            except Exception as e:
                st.error(f"Erro de conexão com o Telegram: {e}")

# Opção de Upload Manual
with st.expander("📂 Ou faça upload manual de um ficheiro .txt do seu dispositivo"):
    arquivo_manual = st.file_uploader("Selecione o arquivo .txt", type=["txt"])
    if arquivo_manual is not None:
        conteudo_texto = arquivo_manual.read().decode('utf-8', errors='ignore')

# --- EXIBIÇÃO E FILTRAGEM DOS RESULTADOS ---
if conteudo_texto:
    txt_filtrado, processos, total, mantidos, removidos = processar_relatorio(conteudo_texto)

    st.markdown("---")
    
    # Cartões de Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Processos", total)
    c2.metric("Mantidos (Visíveis)", mantidos)
    c3.metric("Removidos (Ocultados)", removidos)

    st.markdown("---")
    
    # Controles: Baixar TXT e Barra de Pesquisa
    col_dl, col_search = st.columns([1, 2])
    
    with col_dl:
        st.download_button(
            label="📥 Baixar TXT Filtrado",
            data=txt_filtrado,
            file_name=f"filtrado_{uf_selecionada}{numero_oab}.txt",
            mime="text/plain",
            type="primary",
            use_container_width=True
        )
    
    with col_search:
        busca = st.text_input("🔍 Pesquisar por Nome, CPF ou Nº do Processo", "")

    # Filtragem instantânea da pesquisa
    if busca:
        processos_exibidos = [
            p for p in processos 
            if busca.lower() in p["numero"].lower() 
            or busca.lower() in p["polo_ativo_nome"].lower() 
            or busca.lower() in p["polo_ativo_doc"].lower()
        ]
    else:
        processos_exibidos = processos

    st.subheader(f"📋 Exibindo {len(processos_exibidos)} processos")

    # Renderização visual dos Cards de Processo
    for p in processos_exibidos:
        with st.container(border=True):
            col_info, col_valores, col_copiar = st.columns([2.5, 2, 1.2])
            
            with col_info:
                st.markdown(f"**📌 Processo:** `{p['numero']}`")
                st.markdown(f"**👤 Polo Ativo:** {p['polo_ativo_nome']}")
                st.markdown(f"**🏢 Polo Passivo:** {p['polo_passivo_nome']}")

            with col_valores:
                st.markdown(f"**⚖️ Classe:** {p['classe']}")
                st.markdown(f"**💰 Valor:** {p['valor']}")
                st.markdown(f"**💵 Renda:** {p['polo_ativo_renda']}")

            with col_copiar:
                st.caption("📋 **Copiar CPF / DOC:**")
                # O bloco st.code cria a caixa cinzenta com ícone de cópia em 1 clique
                st.code(p['polo_ativo_doc'], language=None)
                if p['link']:
                    st.link_button("🔗 Abrir Processo", p['link'], use_container_width=True)

            with st.expander("🔍 Ver detalhes completos do processo"):
                st.text(p['bloco_completo'])
