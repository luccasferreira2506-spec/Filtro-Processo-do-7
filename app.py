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
    page_title="Painel Jurídico de Processos", 
    page_icon="⚖️", 
    layout="wide"
)

# Inicializa variáveis de sessão (Session State)
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if "anotacoes_advogados" not in st.session_state:
    st.session_state["anotacoes_advogados"] = []

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
    st.title("🔒 Acesso Restrito ao Sistema Jurídico")
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
            
    st.stop()  # Impede a execução do restante da tela até fazer login

# ==============================================================================
# ⚙️ CREDENCIAIS SEGURAS DO TELEGRAM (CARREGADAS VIA SECRETS)
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
    # Se STRING_SESSION estiver preenchida, usa ela (ótimo para nuvem/Streamlit Cloud)
    session = StringSession(STRING_SESSION) if STRING_SESSION else 'sessao_telegram'
    client = TelegramClient(session, API_ID, API_HASH)
    
    await client.start()

    grupo = await client.get_entity(GRUPO_IDENTIFICADOR)
    mensagem_enviada = await client.send_message(grupo, comando_oab)
    
    arquivo_bytes = None
    
    # Aguarda até 40 segundos pela resposta do Bot no grupo
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
        
        # Filtro automático: Oculta processos em segredo / res. 121
        auto_hidden = False
        polo_ativo_match = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
        if polo_ativo_match:
            trecho_ativo = polo_ativo_match.group(1).lower()
            if any(termo in trecho_ativo for termo in ["ocultada", "ocultado", "res. 121"]):
                auto_hidden = True

        proc = {
            "id": idx,
            "numero": extrair_campo(r'PROCESSO:\s*(.*)', bloco),
            "link": extrair_campo(r'LINK:\s*(.*)', bloco, ""),
            "tribunal": extrair_campo(r'TRIBUNAL:\s*(.*)', bloco),
            "classe": extrair_campo(r'CLASSE:\s*(.*)', bloco),
            "valor": extrair_campo(r'VALOR:\s*(.*)', bloco),
            "polo_ativo_nome": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "polo_ativo_doc": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*DOC:\s*(.*?)\n', bloco, "Sem CPF/DOC"),
            "polo_ativo_renda": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*RENDA:\s*(.*?)\n', bloco),
            "polo_passivo_nome": extrair_campo(r'POLO PASSIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "bloco_completo": bloco,
            "auto_hidden": auto_hidden,
            "oculto_manual": None
        }
        processos_estruturados.append(proc)

    st.session_state["cabecalho_ativo"] = cabecalho
    st.session_state["processos_lista"] = processos_estruturados

def eh_processo_oculto(proc):
    if proc["oculto_manual"] is not None:
        return proc["oculto_manual"]
    return proc["auto_hidden"]

def gerar_texto_filtrado():
    cabecalho = st.session_state.get("cabecalho_ativo", "")
    blocos = [p["bloco_completo"] for p in st.session_state["processos_lista"] if not eh_processo_oculto(p)]
    return cabecalho + "".join(blocos)

def gerar_texto_ocultados():
    cabecalho = "=== PROCESSOS OCULTADOS / FILTRADOS ===\n\n"
    blocos = [p["bloco_completo"] for p in st.session_state["processos_lista"] if eh_processo_oculto(p)]
    return cabecalho + "".join(blocos)

# ==============================================================================
# 📝 GERADORES DE TEXTO E ANOTAÇÕES
# ==============================================================================
def gerar_texto_anotacoes():
    if not st.session_state["anotacoes_advogados"]:
        return "=== NENHUMA ANOTAÇÃO DE ADVOGADO CADASTRADA ===\n\n"
    
    texto = "===============================================================================\n"
    texto += "                      📝 ANOTAÇÕES DOS ADVOGADOS                              \n"
    texto += "===============================================================================\n\n"
    
    for idx, adv in enumerate(st.session_state["anotacoes_advogados"], start=1):
        texto += f"[{idx}] NOME: {adv['nome']}\n"
        texto += f"    OAB: {adv['oab']}\n"
        texto += f"    CONTATO: {adv['contato']}\n"
        texto += f"    ESCRITÓRIO: {adv['escritorio']}\n"
        texto += f"    OBSERVAÇÕES: {adv['notas']}\n"
        texto += "-" * 79 + "\n\n"
        
    return texto

def gerar_texto_combinado(txt_filtrado):
    cabecalho_anotacoes = gerar_texto_anotacoes()
    divisor = "\n" + "="*79 + "\n"
    divisor += "                     📋 RELATÓRIO DE PROCESSOS FILTRADOS                       \n"
    divisor += "="*79 + "\n\n"
    return cabecalho_anotacoes + divisor + txt_filtrado

def salvar_no_historico(origem, conteudo):
    carregar_e_estruturar_relatorio(conteudo)
    total = len(st.session_state["processos_lista"])
    mantidos = sum(1 for p in st.session_state["processos_lista"] if not eh_processo_oculto(p))
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
# 💻 INTERFACE PRINCIPAL COM ABAS
# ==============================================================================
st.title("⚖️ Painel Jurídico de Consultas e Gestão")

tab_consulta, tab_historico, tab_anotacoes = st.tabs([
    "🔍 Consultar & Filtrar Processos", 
    "📜 Histórico de Consultas", 
    "📝 Anotações do Advogado"
])

# ------------------------------------------------------------------------------
# ABA 1: CONSULTA E FILTRO DE PROCESSOS
# ------------------------------------------------------------------------------
with tab_consulta:
    st.write("Selecione o Estado (UF), digite o número da OAB e realize a consulta direta ao Bot do Telegram ou carregue um arquivo local.")

    col_uf, col_num, col_btn = st.columns([1, 2, 1.5])
    estados = ["SP", "PE", "RJ", "MG", "BA", "CE", "PR", "RS", "SC", "AC", "AL", "AM", "AP", "DF", "ES", "GO", "MA", "MS", "MT", "PA", "PB", "PI", "RN", "RO", "RR", "SE", "TO"]

    with col_uf:
        uf_selecionada = st.selectbox("Estado (UF)", estados, index=0)

    with col_num:
        numero_oab_raw = st.text_input("Número da OAB (Apenas dígitos):", placeholder="Ex: 12345 ou 49892")

    apenas_numeros_oab = re.sub(r'\D', '', numero_oab_raw)

    with col_btn:
        st.write("") 
        st.write("")
        btn_buscar = st.button("🚀 Consultar no Telegram", type="primary", use_container_width=True)

    if btn_buscar:
        if not apenas_numeros_oab:
            st.warning("⚠️ Digite um número de OAB válido (apenas dígitos).")
        else:
            comando_formatado = f"/oab {uf_selecionada.lower()}{apenas_numeros_oab}"
            st.info(f"⚡ Comando gerado para envio seguro: `{comando_formatado}`")

            with st.spinner("Conectando ao Telegram e aguardando retorno do arquivo pelo Bot..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    bytes_recebidos = loop.run_until_complete(buscar_arquivo_no_grupo(comando_formatado))
                    
                    if bytes_recebidos:
                        conteudo = bytes_recebidos.decode('utf-8', errors='ignore')
                        st.session_state["conteudo_ativo"] = conteudo
                        st.session_state["origem_ativa"] = f"Telegram ({uf_selecionada.upper()}{apenas_numeros_oab})"
                        salvar_no_historico(st.session_state["origem_ativa"], conteudo)
                        st.success("✅ Relatório recebido do Telegram e carregado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ O Bot não respondeu com o arquivo no tempo limite de 40 segundos.")
                except Exception as e:
                    st.error(f"⚠️ Erro na conexão com o Telegram: {e}")

    with st.expander("📂 Ou faça Upload Manual de um relatório (.txt)"):
        arquivo_manual = st.file_uploader("Selecione o arquivo .txt local", type=["txt"])
        if arquivo_manual is not None:
            conteudo = arquivo_manual.read().decode('utf-8', errors='ignore')
            st.session_state["conteudo_ativo"] = conteudo
            st.session_state["origem_ativa"] = f"Upload ({arquivo_manual.name})"
            salvar_no_historico(st.session_state["origem_ativa"], conteudo)
            st.success("✅ Arquivo carregado com sucesso!")

    if st.session_state["conteudo_ativo"] and st.session_state["processos_lista"]:
        processos = st.session_state["processos_lista"]
        
        total = len(processos)
        mantidos = sum(1 for p in processos if not eh_processo_oculto(p))
        removidos = total - mantidos

        st.markdown("---")
        st.subheader(f"📊 Consulta Ativa: `{st.session_state['origem_ativa']}`")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Processos", total)
        c2.metric("Visíveis (Mantidos)", mantidos)
        c3.metric("Ocultados (Filtrados)", removidos)

        st.markdown("---")
        col_tog, col_info_tog = st.columns([1.5, 2])
        with col_tog:
            mostrar_ocultos = st.toggle("👁️ Mostrar Processos Ocultados / Filtrados", value=False)
        with col_info_tog:
            if mostrar_ocultos:
                st.info("💡 Exibindo TODOS os processos (incluindo os ocultados pela Res. 121/Segredo).")
            else:
                st.caption("🔒 Os processos ocultados estão escondidos. Ative a chave ao lado para visualizá-los.")

        st.markdown("### 📥 Opções de Download do Relatório")

        txt_filtrado_atual = gerar_texto_filtrado()
        txt_ocultados_atual = gerar_texto_ocultados()
        txt_combinado_atual = gerar_texto_combinado(txt_filtrado_atual)

        col_dl1, col_dl2, col_dl3, col_dl4, col_dl5 = st.columns(5)

        with col_dl1:
            st.download_button(
                label="⭐ Filtrado + Anotações",
                data=txt_combinado_atual,
                file_name=f"FILTRADO_COM_ANOTACOES_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
                mime="text/plain",
                type="primary",
                use_container_width=True
            )

        with col_dl2:
            st.download_button(
                label="📥 Apenas Filtrado",
                data=txt_filtrado_atual,
                file_name=f"FILTRADO_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with col_dl3:
            st.download_button(
                label="🚫 Apenas Ocultados",
                data=txt_ocultados_atual,
                file_name=f"OCULTADOS_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with col_dl4:
            st.download_button(
                label="📄 Sem Filtro (Original)",
                data=st.session_state["conteudo_ativo"],
                file_name=f"ORIGINAL_{st.session_state['origem_ativa'].replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with col_dl5:
            st.download_button(
                label="📝 Apenas Anotações",
                data=gerar_texto_anotacoes(),
                file_name="ANOTACOES_ADVOGADOS.txt",
                mime="text/plain",
                use_container_width=True
            )

        st.markdown("---")
        busca = st.text_input("🔍 Pesquisar por Nome, CPF/CNPJ ou Nº do Processo nesta consulta", "")

        if mostrar_ocultos:
            processos_candidatos = processos
        else:
            processos_candidatos = [p for p in processos if not eh_processo_oculto(p)]

        if busca:
            processos_exibidos = [
                p for p in processos_candidatos 
                if busca.lower() in p["numero"].lower() 
                or busca.lower() in p["polo_ativo_nome"].lower() 
                or busca.lower() in p["polo_ativo_doc"].lower()
            ]
        else:
            processos_exibidos = processos_candidatos

        st.subheader(f"📋 Exibindo {len(processos_exibidos)} de {total} processos")

        for p in processos_exibidos:
            oculto = eh_processo_oculto(p)

            with st.container(border=True):
                if oculto:
                    st.warning("⚠️ **ESTE PROCESSO ESTÁ OCULTADO / FILTRADO**")

                col_info, col_valores, col_copiar, col_acoes = st.columns([2.5, 2, 1.2, 1.5])
                
                with col_info:
                    st.markdown(f"**📌 Processo:** `{p['numero']}`")
                    st.markdown(f"**👤 Polo Ativo:** {p['polo_ativo_nome']}")
                    st.markdown(f"**🏢 Polo Passivo:** {p['polo_passivo_nome']}")

                with col_valores:
                    st.markdown(f"**⚖️ Classe:** {p['classe']}")
                    st.markdown(f"**💰 Valor:** {p['valor']}")
                    st.markdown(f"**💵 Renda:** {p['polo_ativo_renda']}")

                with col_copiar:
                    st.caption("📋 **CPF / DOC (Copiar com 1 clique):**")
                    # st.code gera a caixinha com o botão de copiar nativo no canto superior direito
                    st.code(p['polo_ativo_doc'], language=None)
                    if p['link']:
                        st.link_button("🔗 Abrir Link", p['link'], use_container_width=True)

                with col_acoes:
                    st.caption("🛠️ **Ações Manuais:**")
                    if oculto:
                        if st.button("✅ Mostrar / Restaurar", key=f"unhide_{p['id']}", use_container_width=True, type="primary"):
                            p["oculto_manual"] = False
                            st.rerun()
                    else:
                        if st.button("🚫 Ocultar Processo", key=f"hide_{p['id']}", use_container_width=True, type="secondary"):
                            p["oculto_manual"] = True
                            st.rerun()

                    if p["oculto_manual"] is not None:
                        if st.button("🔄 Resetar Status", key=f"reset_{p['id']}", use_container_width=True):
                            p["oculto_manual"] = None
                            st.rerun()

                with st.expander("🔍 Ver detalhes completos do processo"):
                    st.text(p['bloco_completo'])

# ------------------------------------------------------------------------------
# ABA 2: HISTÓRICO DE CONSULTAS
# ------------------------------------------------------------------------------
with tab_historico:
    st.subheader("📜 Histórico de Consultas Realizadas nesta Sessão")
    st.write("Alterne entre consultas passadas para analisar ou baixar relatórios antigos.")

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
                    st.write(f"📊 Total: {item['total']} | Visíveis: {item['mantidos']} | Ocultados: {item['removidos']}")
                with col_h3:
                    if st.button("🔄 Carregar Esta Consulta", key=f"load_hist_{idx}", type="primary", use_container_width=True):
                        st.session_state["conteudo_ativo"] = item["conteudo_original"]
                        st.session_state["origem_ativa"] = item["origem"]
                        carregar_e_estruturar_relatorio(item["conteudo_original"])
                        st.success(f"Carregado: {item['origem']}")
                        st.rerun()

        if st.button("🗑️ Limpar Todo o Histórico"):
            st.session_state["historico_consultas"] = []
            st.rerun()

# ------------------------------------------------------------------------------
# ABA 3: ANOTAÇÕES DO ADVOGADO
# ------------------------------------------------------------------------------
with tab_anotacoes:
    st.subheader("📝 Gestão de Anotações dos Advogados")
    st.write("Cadastre observações e contatos que serão inseridos no TOPO dos relatórios baixados no formato 'Filtrado + Anotações'.")

    with st.form("form_nova_anotacao", clear_on_submit=True):
        st.write("➕ **Cadastrar Nova Anotação**")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            nome_adv = st.text_input("Nome do Advogado:")
            oab_adv = st.text_input("OAB (Ex: PE49892):")
        with col_f2:
            contato_adv = st.text_input("Telefone / Contato:")
            escritorio_adv = st.text_input("Escritório / Filial:")
            
        notas_adv = st.text_area("Anotações e Observações:")
        
        btn_salvar_anot = st.form_submit_button("💾 Salvar Anotação", type="primary")

        if btn_salvar_anot:
            if not nome_adv.strip():
                st.warning("⚠️ Informe pelo menos o nome do advogado.")
            else:
                st.session_state["anotacoes_advogados"].append({
                    "nome": nome_adv.strip(),
                    "oab": oab_adv.strip(),
                    "contato": contato_adv.strip(),
                    "escritorio": escritorio_adv.strip(),
                    "notas": notas_adv.strip()
                })
                st.success("✅ Anotação salva com sucesso!")
                st.rerun()

    st.markdown("---")
    st.subheader(f"📋 Anotações Cadastradas ({len(st.session_state['anotacoes_advogados'])})")

    if not st.session_state["anotacoes_advogados"]:
        st.info("Nenhuma anotação cadastrada no momento.")
    else:
        busca_adv = st.text_input("🔍 Pesquisar Anotação por Nome ou OAB:", "")
        
        anotacoes_filtradas = [
            (i, a) for i, a in enumerate(st.session_state["anotacoes_advogados"])
            if busca_adv.lower() in a["nome"].lower() or busca_adv.lower() in a["oab"].lower()
        ]

        for idx_original, adv in anotacoes_filtradas:
            with st.container(border=True):
                col_det, col_del = st.columns([5, 1])
                with col_det:
                    st.markdown(f"### 👤 {adv['nome']} `(OAB: {adv['oab']})`")
                    st.markdown(f"**📞 Contato:** {adv['contato']} | **🏢 Escritório:** {adv['escritorio']}")
                    st.info(f"**📝 Observações:**\n\n{adv['notas']}")
                with col_del:
                    if st.button("🗑️ Excluir", key=f"del_adv_{idx_original}", type="secondary"):
                        st.session_state["anotacoes_advogados"].pop(idx_original)
                        st.success("Anotação removida!")
                        st.rerun()
