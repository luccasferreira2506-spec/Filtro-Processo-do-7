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
    page_title="Painel Poliana do Sete V2.0 ", 
    page_icon="⚖️", 
    layout="wide"
)

# Inicializa variáveis globais de sessão
if "usuarios_cadastrados" not in st.session_state:
    senha_admin_padrao = st.secrets.get("SENHA_APP")
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
                st.success(f"✅ Bem-vindo(a), {user_input}!")
                st.rerun()
            else:
                st.error("❌ Utilizador ou palavra-passe incorretos.")
    
    st.stop()

usuario_atual = st.session_state["usuario_logado"]

if usuario_atual not in st.session_state["historicos_por_usuario"]:
    st.session_state["historicos_por_usuario"][usuario_atual] = []

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
# 🧠 TRATAMENTO E EXTRAÇÃO RIGOROSA DOS TELEFONES
# ==============================================================================
def extrair_campo(padrao, texto, padrao_padrao="Não informado"):
    match = re.search(padrao, texto, re.IGNORECASE)
    return match.group(1).strip() if match else padrao_padrao

def extrair_telefones(bloco):
    telefones = []
    match_tel_bloco = re.search(r'TELEFONES:\s*(.*?)(?=- ADVOGADO:|- NOME:|\Z)', bloco, re.DOTALL)
    if match_tel_bloco:
        texto_tel = match_tel_bloco.group(1)
        padroes = re.findall(r'\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})', texto_tel)
        for ddd, p1, p2 in padroes:
            num_limpo = f"55{ddd}{p1}{p2}"
            telefones.append(num_limpo)
    return list(set(telefones))

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
    blocos = [p["bloco_completo"] for p in st.session_state["processos_lista"] if not p["auto_hidden"]]
    return cabecalho + "".join(blocos)

def salvar_no_historico(origem, conteudo):
    carregar_e_estruturar_relatorio(conteudo)
    total = len(st.session_state["processos_lista"])
    mantidos = sum(1 for p in st.session_state["processos_lista"] if not p["auto_hidden"])
    
    item = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "origem": origem,
        "total": total,
        "mantidos": mantidos,
        "conteudo_original": conteudo
    }
    hist_usuario = st.session_state["historicos_por_usuario"][usuario_atual]
    if not hist_usuario or hist_usuario[0]["conteudo_original"] != conteudo:
        hist_usuario.insert(0, item)

# ==============================================================================
# 📂 MENU LATERAL RETRÁTIL (SIDEBAR) COM DOWNLOADS À ESQUERDA
# ==============================================================================
with st.sidebar:
    st.title("📂 Painel de Controlo")
    st.write(f"👤 Utilizador: **{usuario_atual}**")
    
    if st.button("🚪 Terminar Sessão", use_container_width=True):
        st.session_state["usuario_logado"] = None
        st.rerun()

    st.markdown("---")
    menu_escolha = st.radio(
        "Navegação:",
        ["🔍 Consulta & Processos", "📜 Histórico de Consultas"]
    )
    
    # PAINEL EXCLUSIVO PARA O ADMIN GERIR CONTAS (CRIAR, EDITAR, EXCLUIR)
    if usuario_atual == "admin":
        with st.expander("🛠️ Gerir Contas de Utilizadores"):
            tab_criar, tab_gerir = st.tabs(["➕ Criar", "✏️/🗑️ Editar/Excluir"])
            
            # Aba 1: Criar Conta
            with tab_criar:
                novo_user = st.text_input("Novo Utilizador:", key="input_novo_user")
                nova_pass = st.text_input("Nova Palavra-passe:", type="password", key="input_nova_pass")
                if st.button("➕ Criar Conta", use_container_width=True):
                    if novo_user.strip() and nova_pass.strip():
                        if novo_user.strip() in st.session_state["usuarios_cadastrados"]:
                            st.warning("⚠️ Esse utilizador já existe.")
                        else:
                            st.session_state["usuarios_cadastrados"][novo_user.strip()] = nova_pass.strip()
                            st.success(f"✅ Conta '{novo_user}' criada com sucesso!")
                            st.rerun()
                    else:
                        st.warning("Preencha todos os campos.")

            # Aba 2: Editar ou Excluir Conta
            with tab_gerir:
                usuarios_lista = list(st.session_state["usuarios_cadastrados"].keys())
                user_selecionado = st.selectbox("Selecione o utilizador:", usuarios_lista, key="select_user_gerir")
                
                # Campo para alterar a palavra-passe
                nova_senha_edit = st.text_input(f"Nova palavra-passe para '{user_selecionado}':", type="password", key="input_edit_pass")
                
                col_acao1, col_acao2 = st.columns(2)
                
                with col_acao1:
                    if st.button("💾 Atualizar", use_container_width=True):
                        if nova_senha_edit.strip():
                            st.session_state["usuarios_cadastrados"][user_selecionado] = nova_senha_edit.strip()
                            st.success(f"✅ Palavra-passe atualizada!")
                            st.rerun()
                        else:
                            st.warning("Digite a nova palavra-passe.")
                
                with col_acao2:
                    if user_selecionado == "admin":
                        st.caption("🔒 O admin não pode ser excluído.")
                    else:
                        if st.button("🗑️ Excluir", type="primary", use_container_width=True):
                            del st.session_state["usuarios_cadastrados"][user_selecionado]
                            st.success(f"✅ Conta '{user_selecionado}' excluída!")
                            st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Consulta Telegram")
    estados = ["SP", "PE", "RJ", "MG", "BA", "CE", "PR", "RS", "SC", "AC", "AL", "AM", "AP", "DF", "ES", "GO", "MA", "MS", "MT", "PA", "PB", "PI", "RN", "RO", "RR", "SE", "TO"]
    uf_selecionada = st.selectbox("Estado (UF)", estados, index=0)
    numero_oab_raw = st.text_input("Número da OAB:", placeholder="Ex: 49892")
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

    # OPÇÕES DE DOWNLOAD NO LADO ESQUERDO (SIDEBAR)
    if st.session_state["conteudo_ativo"]:
        st.markdown("---")
        st.subheader("📥 Opções de Download")
        txt_filtrado_atual = gerar_texto_filtrado()
        
        st.download_button(
            label="📥 Baixar Apenas Filtrado",
            data=txt_filtrado_atual,
            file_name=f"FILTRADO_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
            mime="text/plain",
            type="primary",
            use_container_width=True
        )
        st.download_button(
            label="📄 Baixar Sem Filtro (Original)",
            data=st.session_state["conteudo_ativo"],
            file_name=f"ORIGINAL_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )

# ==============================================================================
# 💻 TELA PRINCIPAL: PAINEL SUPREMO DO SETE V2.0
# ==============================================================================
st.title("⚖️ Painel Supremo do Sete V2.0")

if menu_escolha == "📜 Histórico de Consultas":
    st.subheader(f"📜 Histórico de Consultas de `{usuario_atual}`")
    hist_usuario = st.session_state["historicos_por_usuario"][usuario_atual]
    
    if not hist_usuario:
        st.info("Nenhuma consulta registrada no seu histórico.")
    else:
        for idx, item in enumerate(hist_usuario):
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
        if st.button("🗑️ Limpar Meu Histórico"):
            st.session_state["historicos_por_usuario"][usuario_atual] = []
            st.rerun()

else:
    # --------------------------------------------------------------------------
    # SECÇÃO DO ADVOGADO COM SETA EXPANSÍVEL / RECOLHÍVEL
    # --------------------------------------------------------------------------
    with st.expander("👤 **Identificação e Dados do Advogado** (Clique para recolher/expandir)", expanded=True):
        col_adv1, col_adv2, col_adv3, col_adv4 = st.columns(4)
        with col_adv1:
            nome_adv_input = st.text_input("Nome do Advogado:", value="Dr(a). Nome Exemplo")
        with col_adv2:
            oab_adv_input = st.text_input("OAB:", value="SP000000")
        with col_adv3:
            whats_adv_input = st.text_input("WhatsApp (Ex: 5581999999999):", value="")
        with col_adv4:
            insta_adv_input = st.text_input("Instagram (@usuario):", value="")

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

    if st.session_state["conteudo_ativo"] and st.session_state["processos_lista"]:
        processos = st.session_state["processos_lista"]
        processos_visiveis = [p for p in processos if not p["auto_hidden"]]
        
        total = len(processos)
        mantidos = len(processos_visiveis)
        removidos = total - mantidos

        st.subheader(f"📊 Relatório Ativo: `{st.session_state['origem_ativa']}`")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Processos", total)
        c2.metric("Visíveis", mantidos)
        c3.metric("Ocultados (Res. 121)", removidos)

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

                # BOTÕES DE WHATSAPP PARA OS NÚMEROS DO PROCESSO CORRIGIDOS
                if p["telefones"]:
                    st.markdown("📞 **Telefones de Contato (Clique para WhatsApp):**")
                    cols_tel = st.columns(min(len(p["telefones"]), 4))
                    for idx_tel, tel in enumerate(p["telefones"]):
                        col_atual = cols_tel[idx_tel % len(cols_tel)]
                        with col_atual:
                            st.link_button(f"💬 {tel}", f"https://wa.me/{tel}", use_container_width=True)

                with st.expander("🔍 Ver detalhes completos do processo"):
                    st.text(p['bloco_completo'])
    else:
        st.info("👈 Utilize o menu lateral esquerdo para realizar uma nova consulta via Telegram ou carregar um arquivo .txt local.")
