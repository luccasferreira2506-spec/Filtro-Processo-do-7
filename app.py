import streamlit as st
import re
import asyncio
import requests
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DA PÁGINA E SECRETS
# ==============================================================================
st.set_page_config(page_title="Painel Supremo do Sete V2.0", page_icon="⚖️", layout="wide")

try:
    URL_BANCO_GOOGLE = st.secrets["URL_BANCO_GOOGLE"]
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    BOT_USERNAME = st.secrets.get("BOT_USERNAME", "")
    GRUPO_IDENTIFICADOR = st.secrets.get("GRUPO_IDENTIFICADOR", "")
    STRING_SESSION = st.secrets.get("TELEGRAM_STRING_SESSION", "")
except KeyError as e:
    st.error(f"⚠️ Erro: Faltam chaves nos Secrets do Streamlit: {e}")
    st.stop()

# ==============================================================================
# 💾 COMUNICAÇÃO BLINDADA COM PLANILHA GOOGLE
# ==============================================================================
def carregar_dados():
    try:
        res = requests.get(URL_BANCO_GOOGLE, timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass  # Retorna vazio de forma silenciosa se houver instabilidade
    return {"usuarios": {}, "historicos": {}}

def salvar_dados():
    try:
        payload = {
            "tipo": "salvar_tudo",
            "usuarios": st.session_state["usuarios_cadastrados"],
            "historicos": st.session_state["historicos_por_usuario"]
        }
        requests.post(URL_BANCO_GOOGLE, json=payload, timeout=15)
    except Exception:
        pass

# ==============================================================================
# 🔄 INICIALIZAÇÃO DE SESSÕES
# ==============================================================================
if "banco_carregado" not in st.session_state:
    dados_nuvem = carregar_dados()
    st.session_state["usuarios_cadastrados"] = dados_nuvem.get("usuarios", {})
    st.session_state["historicos_por_usuario"] = dados_nuvem.get("historicos", {})
    st.session_state["banco_carregado"] = True

    if "admin" not in st.session_state["usuarios_cadastrados"]:
        st.session_state["usuarios_cadastrados"]["admin"] = st.secrets.get("SENHA_APP", "123456")
        salvar_dados()

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None
if "login_tempo" not in st.session_state:
    st.session_state["login_tempo"] = None
if "conteudo_ativo" not in st.session_state:
    st.session_state["conteudo_ativo"] = None
if "origem_ativa" not in st.session_state:
    st.session_state["origem_ativa"] = ""
if "processos_lista" not in st.session_state:
    st.session_state["processos_lista"] = []

# ==============================================================================
# 🔒 SISTEMA DE LOGIN
# ==============================================================================
if st.session_state["usuario_logado"] and st.session_state["login_tempo"]:
    if (datetime.now() - st.session_state["login_tempo"]).total_seconds() > 3600:
        st.session_state["usuario_logado"] = None
        st.session_state["login_tempo"] = None
        st.warning("⚠️ Sessão expirada após 1 hora. Faça login novamente.")
        st.rerun()
    else:
        st.session_state["login_tempo"] = datetime.now()

if not st.session_state["usuario_logado"]:
    st.title("🔒 Acesso Restrito - Painel Supremo do Sete V2.0")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        user_input = st.text_input("Utilizador:")
        pass_input = st.text_input("Palavra-passe:", type="password")
        if st.button("🔓 Entrar", type="primary", use_container_width=True):
            usuarios = st.session_state["usuarios_cadastrados"]
            if user_input in usuarios and str(usuarios[user_input]) == str(pass_input):
                st.session_state["usuario_logado"] = user_input
                st.session_state["login_tempo"] = datetime.now()
                st.rerun()
            else:
                st.error("❌ Utilizador ou palavra-passe incorretos.")
    st.stop()

usuario_atual = st.session_state["usuario_logado"]
if usuario_atual not in st.session_state["historicos_por_usuario"]:
    st.session_state["historicos_por_usuario"][usuario_atual] = []
    salvar_dados()

# ==============================================================================
# 🤖 INTEGRAÇÃO COM TELEGRAM & PROCESSAMENTO
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
        if arquivo_bytes: break
    await client.disconnect()
    return arquivo_bytes

def extrair_campo(padrao, texto, padrao_padrao="Não informado"):
    match = re.search(padrao, texto, re.IGNORECASE)
    return match.group(1).strip() if match else padrao_padrao

def extrair_telefones(bloco):
    telefones = []
    match_tel_bloco = re.search(r'TELEFONES:\s*(.*?)(?=- ADVOGADO:|- NOME:|\Z)', bloco, re.DOTALL)
    if match_tel_bloco:
        padroes = re.findall(r'\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})', match_tel_bloco.group(1))
        for ddd, p1, p2 in padroes:
            telefones.append(f"55{ddd}{p1}{p2}")
    return list(set(telefones))

def carregar_e_estruturar_relatorio(conteudo_texto):
    pos_primeiro = conteudo_texto.find('PROCESSO:')
    if pos_primeiro != -1:
        cabecalho, corpo = conteudo_texto[:pos_primeiro], conteudo_texto[pos_primeiro:]
    else:
        cabecalho, corpo = "", conteudo_texto

    blocos = re.split(r'\n(?=PROCESSO:)', corpo)
    st.session_state["processos_lista"] = []

    for idx, bloco in enumerate(blocos):
        if not bloco.strip(): continue
        
        auto_hidden = False
        polo_ativo_match = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
        if polo_ativo_match and any(t in polo_ativo_match.group(1).lower() for t in ["ocultada", "ocultado", "res. 121"]):
            auto_hidden = True

        # Extração melhorada do Advogado e campos
        advogado_val = extrair_campo(r'ADVOGADO:\s*(.*)', bloco)
        if advogado_val == "Não informado":
            advogado_val = extrair_campo(r'ADV:\s*(.*)', bloco)

        st.session_state["processos_lista"].append({
            "numero": extrair_campo(r'PROCESSO:\s*(.*)', bloco),
            "classe": extrair_campo(r'CLASSE:\s*(.*)', bloco),
            "valor": extrair_campo(r'VALOR:\s*(.*)', bloco),
            "advogado": advogado_val,
            "polo_ativo_nome": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "polo_ativo_doc": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*DOC:\s*(.*?)\n', bloco, "Sem CPF/DOC"),
            "polo_ativo_renda": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*RENDA:\s*(.*?)\n', bloco),
            "polo_passivo_nome": extrair_campo(r'POLO PASSIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "telefones": extrair_telefones(bloco),
            "bloco_completo": bloco,
            "auto_hidden": auto_hidden
        })

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
        salvar_dados() 

def gerar_texto_filtrado():
    blocos = [p["bloco_completo"] for p in st.session_state["processos_lista"] if not p["auto_hidden"]]
    return "".join(blocos)

# ==============================================================================
# 📂 MENU LATERAL RETRÁTIL
# ==============================================================================
with st.sidebar:
    st.title("📂 Painel de Controlo")
    st.write(f"👤 Utilizador: **{usuario_atual}**")
    if st.button("🚪 Terminar Sessão", use_container_width=True):
        st.session_state["usuario_logado"] = None
        st.rerun()

    menu_escolha = st.radio("Navegação:", ["🔍 Consulta & Processos", "📜 Histórico de Consultas"])
    
    if usuario_atual == "admin":
        with st.expander("🛠️ Gerir Contas de Utilizadores"):
            tab_criar, tab_gerir = st.tabs(["➕ Criar", "✏️/🗑️ Gerir"])
            
            with tab_criar:
                novo_user = st.text_input("Novo Utilizador:")
                nova_pass = st.text_input("Nova Palavra-passe:", type="password")
                if st.button("➕ Criar Conta", use_container_width=True):
                    if novo_user.strip() and nova_pass.strip():
                        if novo_user.strip() in st.session_state["usuarios_cadastrados"]:
                            st.warning("⚠️ Esse utilizador já existe.")
                        else:
                            st.session_state["usuarios_cadastrados"][novo_user.strip()] = nova_pass.strip()
                            salvar_dados()
                            st.success(f"✅ Conta '{novo_user}' criada!")
                            st.rerun()

            with tab_gerir:
                usuarios_lista = list(st.session_state["usuarios_cadastrados"].keys())
                user_selecionado = st.selectbox("Selecione o utilizador:", usuarios_lista)
                nova_senha_edit = st.text_input("Nova palavra-passe:", type="password")
                
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    if st.button("💾 Atualizar", use_container_width=True) and nova_senha_edit.strip():
                        st.session_state["usuarios_cadastrados"][user_selecionado] = nova_senha_edit.strip()
                        salvar_dados()
                        st.success("✅ Atualizada!")
                        st.rerun()
                with col_a2:
                    if user_selecionado != "admin":
                        if st.button("🗑️ Excluir", type="primary", use_container_width=True):
                            del st.session_state["usuarios_cadastrados"][user_selecionado]
                            if user_selecionado in st.session_state["historicos_por_usuario"]:
                                del st.session_state["historicos_por_usuario"][user_selecionado]
                            salvar_dados()
                            st.success("✅ Excluída!")
                            st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Obter Relatório")
    
    # UPLOAD DE FICHEIROS FUNCIONAL
    arquivo_enviado = st.file_uploader("📂 Enviar arquivo (.txt)", type=["txt"])
    if arquivo_enviado is not None:
        conteudo_up = arquivo_enviado.read().decode('utf-8', errors='ignore')
        st.session_state["conteudo_ativo"] = conteudo_up
        st.session_state["origem_ativa"] = f"Upload ({arquivo_enviado.name})"
        salvar_no_historico(st.session_state["origem_ativa"], conteudo_up)
        st.success("✅ Arquivo carregado com sucesso!")
        st.rerun()

    st.markdown("---")
    st.subheader("🤖 Consulta Telegram")
    uf_selecionada = st.selectbox("Estado", ["SP", "PE", "RJ", "MG", "BA", "CE", "PR", "RS", "SC", "AC", "AL", "AM", "AP", "DF", "ES", "GO", "MA", "MS", "MT", "PA", "PB", "PI", "RN", "RO", "RR", "SE", "TO"])
    numero_oab_raw = st.text_input("Número da OAB:")
    apenas_numeros_oab = re.sub(r'\D', '', numero_oab_raw)

    if st.button("🚀 Consultar OAB", type="primary", use_container_width=True) and apenas_numeros_oab:
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
                    st.rerun()
                else:
                    st.error("❌ Sem resposta.")
            except Exception as e:
                st.error(f"⚠️ Erro: {e}")

    if st.session_state["conteudo_ativo"]:
        st.markdown("---")
        st.download_button("📥 Baixar Filtrado", data=gerar_texto_filtrado(), file_name=f"FILTRADO_{st.session_state['origem_ativa']}.txt", type="primary", use_container_width=True)
        st.download_button("📄 Baixar Original", data=st.session_state["conteudo_ativo"], file_name=f"ORIGINAL_{st.session_state['origem_ativa']}.txt", use_container_width=True)


# ==============================================================================
# 💻 TELA PRINCIPAL
# ==============================================================================
st.title("⚖️ Painel Supremo do Sete V2.0")

if menu_escolha == "📜 Histórico de Consultas":
    st.subheader(f"📜 Histórico de `{usuario_atual}`")
    hist_usuario = st.session_state["historicos_por_usuario"][usuario_atual]
    
    if not hist_usuario:
        st.info("Nenhuma consulta.")
    else:
        for idx, item in enumerate(hist_usuario):
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1.5])
                with col1:
                    st.markdown(f"**📌 {item['origem']}**")
                    st.caption(f"🕒 {item['data_hora']}")
                with col2: st.write(f"📊 {item['total']} processos")
                with col3:
                    if st.button("🔄 Carregar", key=f"btn_{idx}", type="primary"):
                        st.session_state["conteudo_ativo"] = item["conteudo_original"]
                        st.session_state["origem_ativa"] = item["origem"]
                        carregar_e_estruturar_relatorio(item["conteudo_original"])
                        st.rerun()
        if st.button("🗑️ Limpar Meu Histórico"):
            st.session_state["historicos_por_usuario"][usuario_atual] = []
            salvar_dados()
            st.rerun()

else:
    if st.session_state["conteudo_ativo"] and st.session_state["processos_lista"]:
        visiveis = [p for p in st.session_state["processos_lista"] if not p["auto_hidden"]]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", len(st.session_state["processos_lista"]))
        c2.metric("Visíveis", len(visiveis))
        c3.metric("Ocultados (Res. 121)", len(st.session_state["processos_lista"]) - len(visiveis))

        busca = st.text_input("🔍 Pesquisar por Nome/CPF/Processo/Advogado")
        exibidos = [
            p for p in visiveis 
            if busca.lower() in p["numero"].lower() 
            or busca.lower() in p["polo_ativo_nome"].lower() 
            or busca.lower() in p["polo_ativo_doc"].lower()
            or busca.lower() in p["advogado"].lower()
        ] if busca else visiveis

        for p in exibidos:
            with st.container(border=True):
                col_info, col_valores, col_copiar = st.columns([2.5, 2, 1.5])
                with col_info:
                    st.markdown(f"**📌 Processo:** `{p['numero']}`")
                    st.markdown(f"**👤 Ativo:** {p['polo_ativo_nome']}")
                    st.markdown(f"**🏢 Passivo:** {p['polo_passivo_nome']}")
                with col_valores:
                    st.markdown(f"**⚖️ Classe:** {p['classe']}")
                    st.markdown(f"**💰 Valor:** {p['valor']}")
                    st.markdown(f"**👨‍⚖️ Advogado:** {p['advogado']}")  # ADVOGADO GARANTIDO
                with col_copiar:
                    st.caption("📋 **CPF / DOC:**")
                    st.code(p['polo_ativo_doc'], language=None)

                if p["telefones"]:
                    st.markdown("📞 **WhatsApp:**")
                    cols_tel = st.columns(min(len(p["telefones"]), 4))
                    for idx_tel, tel in enumerate(p["telefones"]):
                        cols_tel[idx_tel % len(cols_tel)].link_button(f"💬 {tel}", f"https://wa.me/{tel}", use_container_width=True)

                with st.expander("🔍 Ver bloco original"):
                    st.text(p['bloco_completo'])
    else:
        st.info("👈 Utilize o menu lateral para enviar um arquivo (.txt) ou consultar via Telegram.")
