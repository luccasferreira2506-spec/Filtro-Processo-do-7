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

# Inicializa variáveis de sessão (Session State)
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if "historico_consultas" not in st.session_state:
    st.session_state["historico_consultas"] = []

if "conteudo_ativo" not in st.session_state:
    st.session_state["conteudo_ativo"] = None

if "origem_ativa" not in st.session_state:
    st.session_state["origem_ativa"] = ""

if "processos_lista" not in st.session_state:
    st.session_state["processos_lista"] = []

if "cabecalho_ativo" not in st.session_state:
    st.session_state["cabecalho_ativo"] = ""

# ==============================================================================
# 🔒 SISTEMA DE PROTEÇÃO POR SENHA (SEGURO VIA SECRETS)
# ==============================================================================
if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito - Painel Supremo do Sete V2.0")
    st.write("Digite a senha de acesso para liberar o painel.")

    senha_digitada = st.text_input("Senha de Acesso:", type="password")
    
    if st.button("🔓 Entrar no Sistema", type="primary"):
        try:
            senha_correta = st.secrets["SENHA_APP"]
            if senha_digitada == senha_correta:
                st.session_state["autenticado"] = True
                st.success("✅ Acesso concedido!")
                st.rerun()
            else:
                st.error("❌ Senha incorreta! Tente novamente.")
        except KeyError:
            st.error("⚠️ A variável 'SENHA_APP' não foi configurada nos Secrets do Streamlit Cloud.")
            
    st.stop()

# ==============================================================================
# ⚙️ CREDENCIAIS SEGURAS DO TELEGRAM
# ==============================================================================
try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    BOT_USERNAME = st.secrets.get("BOT_USERNAME", "")
    GRUPO_IDENTIFICADOR = st.secrets.get("GRUPO_IDENTIFICADOR", "")
    STRING_SESSION = st.secrets.get("TELEGRAM_STRING_SESSION", "")
except KeyError as e:
    st.error(f"⚠️ Erro nas credenciais dos Secrets: A chave {e} não foi configurada.")
    st.stop()

# ==============================================================================
# 🤖 FUNÇÃO DE CONEXÃO COM O TELEGRAM
# ==============================================================================
async def buscar_arquivo_no_grupo(comando_oab):
    session = StringSession(STRING_SESSION) if STRING_SESSION else 'sessao_telegram'
    client = TelegramClient(session, API_ID, API_HASH)
    
    await client.start()

    grupo = await client.get_entity(GRUPO_IDENTIFICADOR)
    mensagem_enviada = await client.send_message(grupo, comando_oab)
    
    arquivo_bytes = None
    for _ in range(40):
        await asyncio.sleep(1)
        async for message in client.iter_messages(grupo, limit=5):
            sender_name = getattr(message.sender, 'username', '') if message.sender else ''
            if sender_name == BOT_USERNAME or BOT_USERNAME in str(message.sender_id):
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

def extrair_telefones(bloco):
    """Extrai os telefones de dentro do bloco do processo."""
    telefones = []
    # Procura a seção de telefones
    match_tel_bloco = re.search(r'TELEFONES:\s*(.*?)(?=- ADVOGADO:|- NOME:|\Z)', bloco, re.DOTALL)
    if match_tel_bloco:
        linhas = match_tel_bloco.group(1).split('\n')
        for linha in linhas:
            # Pega números que estejam no formato exato ou limpa os caracteres para pegar os dígitos
            digitos = re.sub(r'\D', '', linha)
            if len(digitos) >= 8:  # Considera número de telefone válido
                telefones.append(digitos)
    return list(set(telefones)) # Remove duplicados

def carregar_e_estruturar_relatorio(conteudo_texto):
    pos_primeiro = conteudo_texto.find('PROCESSO:')
    if pos_primeiro != -1:
        cabecalho = conteudo_texto[:pos_primeiro]
        corpo = conteudo_texto[pos_primeiro:]
    else:
        cabecalho = ""
        corpo = conteudo_texto

    blocos = re.split(r'\n(?=PROCESSO:)', corpo)
    processos_estruturados = []

    for idx, bloco in enumerate(blocos):
        if not bloco.strip():
            continue
        
        auto_hidden = False
        polo_ativo_match = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
        if polo_ativo_match:
            trecho_ativo = polo_ativo_match.group(1).lower()
            if any(termo in trecho_ativo for termo in ["ocultada", "ocultado", "res. 121"]):
                auto_hidden = True

        proc = {
            "id": idx,
            "numero": extrair_campo(r'PROCESSO:\s*(.*)', bloco),
            "tribunal": extrair_campo(r'TRIBUNAL:\s*(.*)', bloco),
            "classe": extrair_campo(r'CLASSE:\s*(.*)', bloco),
            "valor": extrair_campo(r'VALOR:\s*(.*)', bloco),
            "polo_ativo_nome": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "polo_ativo_doc": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*DOC:\s*(.*?)\n', bloco, "Sem CPF/DOC"),
            "polo_ativo_renda": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*RENDA:\s*(.*?)\n', bloco),
            "polo_passivo_nome": extrair_campo(r'POLO PASSIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "telefones": extrair_telefones(bloco),
            "bloco_completo": bloco,
            "auto_hidden": auto_hidden
        }
        processos_estruturados.append(proc)

    st.session_state["cabecalho_ativo"] = cabecalho
    st.session_state["processos_lista"] = processos_estruturados

def gerar_texto_filtrado():
    cabecalho = st.session_state.get("cabecalho_ativo", "")
    # Remove automaticamente os processos ocultados/Res. 121 no arquivo filtrado
    blocos = [p["bloco_completo"] for p in st.session_state["processos_lista"] if not p["auto_hidden"]]
    return cabecalho + "".join(blocos)

def salvar_no_historico(origem, conteudo):
    carregar_e_estruturar_relatorio(conteudo)
    total = len(st.session_state["processos_lista"])
    mantidos = sum(1 for p in st.session_state["processos_lista"] if not p["auto_hidden"])
    removidos = total - mantidos

    item = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "origem": origem,
        "total": total,
        "mantidos": mantidos,
        "removidos": removidos,
        "conteudo_original": conteudo
    }
    if not st.session_state["historico_consultas"] or st.session_state["historico_consultas"][0]["conteudo_original"] != conteudo:
        st.session_state["historico_consultas"].insert(0, item)

# ==============================================================================
# 📂 MENU LATERAL RETRÁTIL (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.title("📂 Painel de Controle")
    st.write("Gerencie suas consultas e dados por aqui.")
    
    menu_escolha = st.radio(
        "Navegação:",
        ["🔍 Consulta & Processos", "📜 Histórico de Consultas"]
    )
    
    st.markdown("---")
    st.subheader("⚙️ Nova Consulta Telegram")
    estados = ["SP", "PE", "RJ", "MG", "BA", "CE", "PR", "RS", "SC", "AC", "AL", "AM", "AP", "DF", "ES", "GO", "MA", "MS", "MT", "PA", "PB", "PI", "RN", "RO", "RR", "SE", "TO"]
    uf_selecionada = st.selectbox("Estado (UF)", estados, index=0)
    numero_oab_raw = st.text_input("Número da OAB (Apenas dígitos):", placeholder="Ex: 49892")
    apenas_numeros_oab = re.sub(r'\D', '', numero_oab_raw)

    if st.button("🚀 Consultar no Telegram", type="primary", use_container_width=True):
        if not apenas_numeros_oab:
            st.warning("⚠️ Digite um número de OAB válido.")
        else:
            comando_formatado = f"/oab {uf_selecionada.lower()}{apenas_numeros_oab}"
            with st.spinner("Buscando no Telegram..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    bytes_recebidos = loop.run_until_complete(buscar_arquivo_no_grupo(comando_formatado))
                    if bytes_recebidos:
                        conteudo = bytes_recebidos.decode('utf-8', errors='ignore')
                        st.session_state["conteudo_ativo"] = conteudo
                        st.session_state["origem_ativa"] = f"Telegram ({uf_selecionada.upper()}{apenas_numeros_oab})"
                        salvar_no_historico(st.session_state["origem_ativa"], conteudo)
                        st.success("✅ Relatório carregado!")
                        st.rerun()
                    else:
                        st.error("❌ O Bot não respondeu a tempo.")
                except Exception as e:
                    st.error(f"⚠️ Erro: {e}")

    with st.expander("📂 Upload Manual (.txt)"):
        arquivo_manual = st.file_uploader("Arquivo local", type=["txt"])
        if arquivo_manual is not None:
            conteudo = arquivo_manual.read().decode('utf-8', errors='ignore')
            st.session_state["conteudo_ativo"] = conteudo
            st.session_state["origem_ativa"] = f"Upload ({arquivo_manual.name})"
            salvar_no_historico(st.session_state["origem_ativa"], conteudo)
            st.success("✅ Carregado com sucesso!")

# ==============================================================================
# 💻 TELA PRINCIPAL: PAINEL SUPREMO DO SETE V2.0
# ==============================================================================
st.title("⚖️ Painel Supremo do Sete V2.0")

# Se a escolha no menu lateral for histórico
if menu_escolha == "📜 Histórico de Consultas":
    st.subheader("📜 Histórico de Consultas Realizadas")
    if not st.session_state["historico_consultas"]:
        st.info("Nenhuma consulta registrada ainda.")
    else:
        for idx, item in enumerate(st.session_state["historico_consultas"]):
            with st.container(border=True):
                col_h1, col_h2, col_h3 = st.columns([3, 2, 1.5])
                with col_h1:
                    st.markdown(f"**📌 Origem:** `{item['origem']}`")
                    st.caption(f"🕒 Data/Hora: {item['data_hora']}")
                with col_h2:
                    st.write(f"📊 Total: {item['total']} | Visíveis: {item['mantidos']}")
                with col_h3:
                    if st.button("🔄 Carregar", key=f"load_hist_{idx}", type="primary", use_container_width=True):
                        st.session_state["conteudo_ativo"] = item["conteudo_original"]
                        st.session_state["origem_ativa"] = item["origem"]
                        carregar_e_estruturar_relatorio(item["conteudo_original"])
                        st.success("Consulta carregada!")
                        st.rerun()
        if st.button("🗑️ Limpar Histórico"):
            st.session_state["historico_consultas"] = []
            st.rerun()

else:
    # --------------------------------------------------------------------------
    # ABA PRINCIPAL: IDENTIFICAÇÃO DO ADVOGADO NO TOPO
    # --------------------------------------------------------------------------
    st.markdown("### 👤 Identificação do Advogado")
    with st.container(border=True):
        col_adv1, col_adv2, col_adv3, col_adv4 = st.columns(4)
        with col_adv1:
            nome_adv_input = st.text_input("Nome do Advogado:", value="Dr(a). Nome Exemplo")
        with col_adv2:
            oab_adv_input = st.text_input("OAB:", value="SP000000")
        with col_adv3:
            whats_adv_input = st.text_input("WhatsApp (Ex: 5581999999999):", value="")
        with col_adv4:
            insta_adv_input = st.text_input("Instagram (@usuario):", value="")

        # Renderização dinâmica dos botões com links clicáveis do advogado
        col_btn_w, col_btn_i = st.columns(2)
        with col_btn_w:
            if whats_adv_input.strip():
                limpa_whats = re.sub(r'\D', '', whats_adv_input)
                st.link_button(f"💬 Abrir WhatsApp do Advogado", f"https://wa.me/{limpa_whats}", use_container_width=True)
            else:
                st.caption("Insira o número do WhatsApp acima para gerar o botão.")
        with col_btn_i:
            if insta_adv_input.strip():
                limpa_insta = insta_adv_input.strip().replace("@", "")
                st.link_button(f"📸 Abrir Instagram (@{limpa_insta})", f"https://instagram.com/{limpa_insta}", use_container_width=True)
            else:
                st.caption("Insira o Instagram acima para gerar o botão.")

    st.markdown("---")

    # SE HOUVER RELATÓRIO CARREGADO
    if st.session_state["conteudo_ativo"] and st.session_state["processos_lista"]:
        processos = st.session_state["processos_lista"]
        
        # Filtra automaticamente tirando os ocultados da exibição e download padrão
        processos_visiveis = [p for p in processos if not p["auto_hidden"]]
        
        total = len(processos)
        mantidos = len(processos_visiveis)
        removidos = total - mantidos

        st.subheader(f"📊 Relatório Ativo: `{st.session_state['origem_ativa']}`")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Processos", total)
        c2.metric("Visíveis", mantidos)
        c3.metric("Ocultados (Res. 121)", removidos)

        # OPÇÕES DE DOWNLOAD SOLICITADAS (APENAS FILTRADO E SEM FILTRO)
        st.markdown("### 📥 Opções de Download")
        txt_filtrado_atual = gerar_texto_filtrado()
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📥 Baixar Apenas Filtrado",
                data=txt_filtrado_atual,
                file_name=f"FILTRADO_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
                mime="text/plain",
                type="primary",
                use_container_width=True
            )
        with col_dl2:
            st.download_button(
                label="📄 Baixar Sem Filtro (Original)",
                data=st.session_state["conteudo_ativo"],
                file_name=f"ORIGINAL_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        st.markdown("---")
        busca = st.text_input("🔍 Pesquisar por Nome, CPF/CNPJ ou Nº do Processo", "")

        if busca:
            processos_exibidos = [
                p for p in processos_visiveis 
                if busca.lower() in p["numero"].lower() 
                or busca.lower() in p["polo_ativo_nome"].lower() 
                or busca.lower() in p["polo_ativo_doc"].lower()
            ]
        else:
            processos_exibidos = processos_visiveis

        st.subheader(f"📋 Exibindo {len(processos_exibidos)} de {mantidos} processos visíveis")

        for p in processos_exibidos:
            with st.container(border=True):
                col_info, col_valores, col_copiar = st.columns([2.5, 2, 1.5])
                
                with col_info:
                    st.markdown(f"**📌 Processo:** `{p['numero']}`")
                    st.markdown(f"**👤 Polo Ativo:** {p['polo_ativo_nome']}")
                    st.markdown(f"**🏢 Polo Passivo:** {p['polo_passivo_nome']}")

                with col_valores:
                    st.markdown(f"**⚖️ Classe:** {p['classe']}")
                    st.markdown(f"**💰 Valor:** {p['valor']}")
                    st.markdown(f"**💵 Renda:** {p['polo_ativo_renda']}")

                with col_copiar:
                    st.caption("📋 **CPF / DOC (Copiar):**")
                    st.code(p['polo_ativo_doc'], language=None)

                # BOTÕES DE WHATSAPP PARA OS NÚMEROS LIGADOS AO PROCESSO
                if p["telefones"]:
                    st.markdown("📞 **Telefones de Contato (Clique para WhatsApp):**")
                    cols_tel = st.columns(min(len(p["telefones"]), 4)) # Cria colunas dinâmicas para os telefones
                    for idx_tel, tel in enumerate(p["telefones"]):
                        col_atual = cols_tel[idx_tel % len(cols_tel)]
                        with col_atual:
                            st.link_button(f"💬 {tel}", f"https://wa.me/55{tel}", use_container_width=True)

                with st.expander("🔍 Ver detalhes completos do processo"):
                    st.text(p['bloco_completo'])
    else:
        st.info("👈 Utilize o menu lateral esquerdo para realizar uma nova consulta via Telegram ou carregar um arquivo .txt local.")
