import streamlit as st
import re
import asyncio
from datetime import datetime
from telethon import TelegramClient

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Painel de Processos, Histórico e Anotações", 
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

if "processos_lista" not in st.session_state:
    st.session_state["processos_lista"] = []

if "cabecalho_ativo" not in st.session_state:
    st.session_state["cabecalho_ativo"] = ""

# ==============================================================================
# 🔒 SISTEMA DE PROTEÇÃO POR SENHA (SEGURO VIA SECRETS)
# ==============================================================================
if not st.session_state["autenticado"]:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🔒 Painel Restrito de Processos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280;'>Introduza a senha de acesso para continuar.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            senha_digitada = st.text_input("Senha de Acesso", type="password")
            btn_entrar = st.form_submit_button("Entrar no Painel", use_container_width=True)
            
            if btn_entrar:
                senha_correta = st.secrets.get("SENHA_ACESSO", "admin123")
                if senha_digitada == senha_correta:
                    st.session_state["autenticado"] = True
                    st.success("Acesso autorizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Senha incorreta. Tente novamente.")
    st.stop()

# ==============================================================================
# 🛠️ FUNÇÕES DE PROCESSAMENTO E ESTRUTURAÇÃO
# ==============================================================================
def limpar_telefone_wa(tel_str):
    apenas_nums = re.sub(r'\D', '', tel_str)
    if len(apenas_nums) <= 9:
        apenas_nums = "81" + apenas_nums
    if not apenas_nums.startswith("55"):
        apenas_nums = "55" + apenas_nums
    return apenas_nums

def carregar_e_estruturar_relatorio(texto_bruto, origem_nome=""):
    linhas = texto_bruto.splitlines()
    cabecalho = []
    for l in linhas[:15]:
        if "PROCESSO:" in l:
            break
        cabecalho.append(l)
    cabecalho_str = "\n".join(cabecalho)

    blocos = re.split(r'\n(?=PROCESSO:)', texto_bruto)
    processos = []

    for bloco in blocos:
        if not bloco.strip().startswith("PROCESSO:"):
            continue
        
        proc_dict = {
            "texto_original": bloco,
            "numero": "",
            "link": "",
            "tribunal": "",
            "classe": "",
            "assunto": "",
            "valor": "",
            "data_inicio": "",
            "data_ultimo_movimento": "",
            "orgao_julgador": "",
            "polo_ativo_nome": "",
            "polo_ativo_doc": "",
            "polo_ativo_adv": "",
            "polo_passivo_nome": "",
            "polo_passivo_doc": "",
            "polo_passivo_adv": "",
            "telefones": [],
            "oculto": False,
            "editado_manualmente": False
        }

        m_num = re.search(r'PROCESSO:\s*(.*)', bloco)
        if m_num: proc_dict["numero"] = m_num.group(1).strip()

        m_link = re.search(r'LINK:\s*(.*)', bloco)
        if m_link: proc_dict["link"] = m_link.group(1).strip()

        m_trib = re.search(r'TRIBUNAL:\s*(.*)', bloco)
        if m_trib: proc_dict["tribunal"] = m_trib.group(1).strip()

        m_classe = re.search(r'CLASSE:\s*(.*)', bloco)
        if m_classe: proc_dict["classe"] = m_classe.group(1).strip()

        m_assunto = re.search(r'ASSUNTO:\s*(.*)', bloco)
        if m_assunto: proc_dict["assunto"] = m_assunto.group(1).strip()

        m_valor = re.search(r'VALOR:\s*(.*)', bloco)
        if m_valor: proc_dict["valor"] = m_valor.group(1).strip()

        m_dt_ini = re.search(r'DATA INICIO:\s*(.*)', bloco)
        if m_dt_ini: proc_dict["data_inicio"] = m_dt_ini.group(1).strip()

        m_dt_mov = re.search(r'DATA ULTIMO MOVIMENTO:\s*(.*)', bloco)
        if m_dt_mov: proc_dict["data_ultimo_movimento"] = m_dt_mov.group(1).strip()

        m_orgao = re.search(r'ORGAO JULGADOR:\s*(.*)', bloco)
        if m_orgao: proc_dict["orgao_julgador"] = m_orgao.group(1).strip()

        # Extração Polo Ativo
        ativo_sec = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
        if ativo_sec:
            at_txt = ativo_sec.group(1)
            m_nom = re.search(r'NOME:\s*(.*)', at_txt)
            if m_nom: proc_dict["polo_ativo_nome"] = m_nom.group(1).strip()
            
            m_doc = re.search(r'DOC:\s*(.*)', at_txt)
            if m_doc: proc_dict["polo_ativo_doc"] = m_doc.group(1).strip()
            
            m_adv = re.search(r'ADVOGADO:\s*(.*)', at_txt)
            if m_adv: proc_dict["polo_ativo_adv"] = m_adv.group(1).strip()

        # Extração Polo Passivo
        passivo_sec = re.search(r'POLO PASSIVO:(.*?)(?=\n[A-Z]+:|\Z)', bloco, re.DOTALL)
        if passivo_sec:
            ps_txt = passivo_sec.group(1)
            m_nom_p = re.search(r'NOME:\s*(.*)', ps_txt)
            if m_nom_p: proc_dict["polo_passivo_nome"] = m_nom_p.group(1).strip()
            
            m_doc_p = re.search(r'DOC:\s*(.*)', ps_txt)
            if m_doc_p: proc_dict["polo_passivo_doc"] = m_doc_p.group(1).strip()
            
            m_adv_p = re.search(r'ADVOGADO:\s*(.*)', ps_txt)
            if m_adv_p: proc_dict["polo_passivo_adv"] = m_adv_p.group(1).strip()

        # Telefones
        tels = re.findall(r'📞\s*([^\n]+)', bloco)
        if not tels:
            tels = re.findall(r'(?:\(\d{2}\)\s*|\d{2}\s*)\d{4,5}[-.\s]?\d{4}', bloco)
        proc_dict["telefones"] = [t.strip() for t in tels]

        termo_ativo_upper = proc_dict["polo_ativo_nome"].upper()
        if any(termo in termo_ativo_upper for termo in ["SEGREDO DE JUSTICA", "SEGREDO DE JUSTIÇA", "SIGILOSO", "CONFIDENCIAL"]):
            proc_dict["oculto"] = True

        processos.append(proc_dict)

    return processos, cabecalho_str

# ==============================================================================
# 🎨 MENU LATERAL (SIDEBAR)
# ==============================================================================
st.sidebar.markdown("### ⚖️ Menu Principal")
aba_selecionada = st.sidebar.radio(
    "Navegação",
    ["📊 Painel de Processos", "🤖 Consulta Telegram", "📂 Upload Manual", "📜 Histórico de Consultas", "👤 Anotações de Advogados"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 Terminar Sessão", use_container_width=True):
    st.session_state["autenticado"] = False
    st.rerun()

# ==============================================================================
# 📊 ABA 1: PAINEL DE PROCESSOS
# ==============================================================================
if aba_selecionada == "📊 Painel de Processos":
    st.title("📊 Painel de Gestão de Processos")
    
    if not st.session_state["processos_lista"]:
        st.info("Nenhum processo carregado no momento. Faça uma consulta via Telegram ou envie um ficheiro manualmente.")
    else:
        col_f1, col_f2, col_f3 = st.columns([3, 2, 2])
        with col_f1:
            termo_busca = st.text_input("🔍 Pesquisar por Processo, Nome, Parte ou Advogado:", "")
        with col_f2:
            filtro_status = st.selectbox("Filtrar Visibilidade:", ["Todos (Visíveis)", "Apenas Ocultos", "Ver Todos"])
        with col_f3:
            st.write("")
            st.write(f"**Total na lista:** {len(st.session_state['processos_lista'])}")

        processos_filtrados = []
        for i, p in enumerate(st.session_state["processos_lista"]):
            if filtro_status == "Apenas Ocultos" and not p["oculto"]:
                continue
            if filtro_status == "Todos (Visíveis)" and p["oculto"]:
                continue
            
            if termo_busca:
                txt_completo = f"{p['numero']} {p['polo_ativo_nome']} {p['polo_passivo_nome']} {p['polo_ativo_adv']} {p['polo_passivo_adv']} {p['classe']}".lower()
                if termo_busca.lower() not in txt_completo:
                    continue
            
            processos_filtrados.append((i, p))

        st.markdown(f"**Exibindo {len(processos_filtrados)} processos.**")
        
        for idx, proc in processos_filtrados:
            status_tag = "🔴 [OCULTO]" if proc["oculto"] else "🟢 [VISÍVEL]"
            with st.expander(f"Processo: {proc['numero']} | Ativo: {proc['polo_ativo_nome'][:25]}... {status_tag}"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**Tribunal:** {proc['tribunal']}")
                    st.markdown(f"**Classe:** {proc['classe']} | **Assunto:** {proc['assunto']}")
                    st.markdown(f"**Valor da Causa:** {proc['valor']}")
                    st.markdown(f"**Órgão Julgador:** {proc['orgao_julgador']}")
                    
                    st.markdown("---")
                    st.markdown(f"**🟢 Polo Ativo:** `{proc['polo_ativo_nome']}` (Doc: {proc['polo_ativo_doc']})")
                    st.markdown(f"**⚖️ Advogado (Ativo):** `{proc['polo_ativo_adv'] if proc['polo_ativo_adv'] else 'Não informado'}`")
                    
                    st.markdown(f"**🔴 Polo Passivo:** `{proc['polo_passivo_nome']}` (Doc: {proc['polo_passivo_doc']})")
                    st.markdown(f"**⚖️ Advogado (Passivo):** `{proc['polo_passivo_adv'] if proc['polo_passivo_adv'] else 'Não informado'}`")
                    
                    if proc["telefones"]:
                        st.markdown("---")
                        st.markdown("**📞 Telefones de Contato (WhatsApp Direto wa.me):**")
                        cols_tel = st.columns(min(len(proc["telefones"]), 4))
                        for t_i, tel in enumerate(proc["telefones"]):
                            num_clean = limpar_telefone_wa(tel)
                            with cols_tel[t_i % len(cols_tel)]:
                                st.markdown(f'<a href="https://wa.me/{num_clean}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px;">💬 {tel}</button></a>', unsafe_allow_html=True)

                    if proc["link"]:
                        st.markdown(f"[🔗 Aceder ao Link do Processo]({proc['link']})")

                with c2:
                    st.markdown("### ⚙️ Gestão")
                    novo_estado = st.checkbox("Ocultar Processo", value=proc["oculto"], key=f"chk_oculto_{idx}")
                    if novo_estado != proc["oculto"]:
                        st.session_state["processos_lista"][idx]["oculto"] = novo_estado
                        st.session_state["processos_lista"][idx]["editado_manualmente"] = True
                        st.rerun()

        st.markdown("---")
        st.subheader("📥 Exportação de Relatórios")
        
        col_d1, col_d2 = st.columns(2)
        
        texto_sem_filtro = st.session_state["cabecalho_ativo"] + "\n\n"
        for p in st.session_state["processos_lista"]:
            texto_sem_filtro += p["texto_original"] + "\n\n----------------------------------------------\n"

        texto_filtrado = st.session_state["cabecalho_ativo"] + "\n\n"
        for p in st.session_state["processos_lista"]:
            if not p["oculto"]:
                texto_filtrado += p["texto_original"] + "\n\n----------------------------------------------\n"

        with col_d1:
            st.download_button(
                label="📥 Baixar Arquivo Original (Sem Filtro)",
                data=texto_sem_filtro,
                file_name="relatorio_original.txt",
                mime="text/plain",
                use_container_width=True
            )

        with col_d2:
            st.download_button(
                label="📥 Baixar Arquivo Filtrado",
                data=texto_filtrado,
                file_name="relatorio_filtrado.txt",
                mime="text/plain",
                use_container_width=True
            )

# ==============================================================================
# 🤖 ABA 2: CONSULTA TELEGRAM
# ==============================================================================
elif aba_selecionada == "🤖 Consulta Telegram":
    st.title("🤖 Consulta Automatizada via Telegram")
    st.markdown("Insira o comando de OAB (ex: `/oab PE49892`) para interagir com o bot e extrair os processos.")

    with st.form("form_telegram"):
        oab_input = st.text_input("Comando OAB:", placeholder="/oab PE49892")
        btn_consultar = st.form_submit_button("Executar Consulta", use_container_width=True)

        if btn_consultar:
            if not oab_input.strip():
                st.warning("Insira um comando OAB válido.")
            else:
                api_id = st.secrets.get("TELEGRAM_API_ID", 0)
                api_hash = st.secrets.get("TELEGRAM_API_HASH", "")
                grupo_destino = st.secrets.get("TELEGRAM_GRUPO", "")

                if not api_id or not api_hash or not grupo_destino:
                    st.error("As credenciais do Telegram (API_ID, API_HASH, TELEGRAM_GRUPO) não estão configuradas nos Secrets.")
                else:
                    with st.spinner("A ligar ao Telegram e a efetuar a consulta..."):
                        async def run_telegram():
                            client = TelegramClient('sessao_streamlit', int(api_id), api_hash)
                            await client.start()
                            await client.send_message(grupo_destino, oab_input)
                            await asyncio.sleep(5)
                            
                            mensagens = []
                            async for message in client.iter_messages(grupo_destino, limit=5):
                                if message.text and "PROCESSO:" in message.text:
                                    mensagens.append(message.text)
                            await client.disconnect()
                            return mensagens

                        try:
                            respostas = asyncio.run(run_telegram())
                            if respostas:
                                texto_capturado = respostas[0]
                                processos, cabecalho = carregar_e_estruturar_relatorio(texto_capturado, "Telegram")
                                st.session_state["processos_lista"] = processos
                                st.session_state["cabecalho_ativo"] = cabecalho
                                
                                registro = {
                                    "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                    "origem": f"Telegram ({oab_input})",
                                    "total": len(processos),
                                    "conteudo": texto_capturado,
                                    "cabecalho": cabecalho
                                }
                                st.session_state["historico_consultas"].insert(0, registro)
                                st.success(f"Consulta efetuada com sucesso! {len(processos)} processos carregados.")
                            else:
                                st.warning("Nenhum relatório de processos foi retornado pelo bot no tempo limite.")
                        except Exception as e:
                            st.error(f"Erro ao comunicar com o Telegram: {e}")

# ==============================================================================
# 📂 ABA 3: UPLOAD MANUAL
# ==============================================================================
elif aba_selecionada == "📂 Upload Manual":
    st.title("📂 Upload Manual de Ficheiro TXT")
    st.markdown("Carregue diretamente um relatório de processos em formato `.txt` para processamento imediato.")

    arquivo_enviado = st.file_uploader("Selecionar ficheiro .txt", type=["txt"])
    
    if arquivo_enviado is not None:
        texto_bruto = arquivo_enviado.getvalue().decode("utf-8")
        if st.button("Processar Ficheiro Carregado", use_container_width=True):
            processos, cabecalho = carregar_e_estruturar_relatorio(texto_bruto, arquivo_enviado.name)
            st.session_state["processos_lista"] = processos
            st.session_state["cabecalho_ativo"] = cabecalho
            
            registro = {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "origem": f"Upload: {arquivo_enviado.name}",
                "total": len(processos),
                "conteudo": texto_bruto,
                "cabecalho": cabecalho
            }
            st.session_state["historico_consultas"].insert(0, registro)
            st.success(f"Ficheiro processado com sucesso! {len(processos)} processos carregados.")

# ==============================================================================
# 📜 ABA 4: HISTÓRICO DE CONSULTAS
# ==============================================================================
elif aba_selecionada == "📜 Histórico de Consultas":
    st.title("📜 Histórico de Consultas da Sessão")
    st.markdown("Registo das consultas e ficheiros carregados durante a sessão atual.")

    if not st.session_state["historico_consultas"]:
        st.info("Nenhum histórico registado até o momento.")
    else:
        if st.button("🗑️ Limpar Histórico", type="secondary"):
            st.session_state["historico_consultas"] = []
            st.success("Histórico limpo com sucesso!")
            st.rerun()

        for idx, item in enumerate(st.session_state["historico_consultas"]):
            with st.expander(f"🕒 {item['data']} | Origem: {item['origem']} | Total: {item['total']} processos"):
                st.markdown(f"**Total de Processos:** {item['total']}")
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    if st.button("📂 Carregar este Relatório no Painel", key=f"load_hist_{idx}"):
                        procs, cab = carregar_e_estruturar_relatorio(item["conteudo"], item["origem"])
                        st.session_state["processos_lista"] = procs
                        st.session_state["cabecalho_ativo"] = cab
                        st.success("Relatório carregado para o painel principal!")
                with col_h2:
                    st.download_button(
                        label="📥 Baixar Ficheiro",
                        data=item["conteudo"],
                        file_name=f"historico_{idx}.txt",
                        mime="text/plain",
                        key=f"dl_hist_{idx}"
                    )

# ==============================================================================
# 👤 ABA 5: ANOTAÇÕES DE ADVOGADOS
# ==============================================================================
elif aba_selecionada == "👤 Anotações de Advogados":
    st.title("👤 Gestão e Anotações de Advogados")
    st.markdown("Registe anotações, contactos e observações sobre advogados.")

    def gerar_texto_anotacoes():
        txt = "REGISTO DE ANOTAÇÕES DE ADVOGADOS\n==============================================\n\n"
        for a in st.session_state["anotacoes_advogados"]:
            txt += f"NOME: {a['nome']}\nOAB: {a['oab']}\nCONTATO: {a['contato']}\nESCRITÓRIO: {a['escritorio']}\nNOTAS:\n{a['notas']}\n\n----------------------------------------------\n"
        return txt

    with st.form("form_advogado_anotacao", clear_on_submit=True):
        st.subheader("Adicionar Novo Advogado / Anotação")
        c_adv1, c_adv2 = st.columns(2)
        with c_adv1:
            nome_adv = st.text_input("Nome do Advogado")
            oab_adv = st.text_input("Número da OAB (ex: PE00000)")
        with c_adv2:
            contato_adv = st.text_input("Contato / Telefone")
            escritorio_adv = st.text_input("Escritório / Empresa")
        
        notas_adv = st.text_area("Observações e Anotações")
        btn_add_adv = st.form_submit_button("Guardar Anotação", use_container_width=True)

        if btn_add_adv:
            if nome_adv.strip() and oab_adv.strip():
                st.session_state["anotacoes_advogados"].append({
                    "nome": nome_adv,
                    "oab": oab_adv,
                    "contato": contato_adv,
                    "escritorio": escritorio_adv,
                    "notas": notas_adv
                })
                st.success("Anotação guardada com sucesso!")
            else:
                st.warning("Preencha pelo menos o Nome e a OAB.")

    st.markdown("---")
    st.subheader("Lista de Anotações Guardadas")
    
    if not st.session_state["anotacoes_advogados"]:
        st.info("Nenhuma anotação de advogado registada.")
    else:
        col_busca_adv, col_dl_anot = st.columns([3, 1])
        with col_busca_adv:
            busca_adv = st.text_input("🔍 Pesquisar anotação por Nome ou OAB:", "")
            
        with col_dl_anot:
            st.write("")
            st.download_button(
                label="📥 Baixar Anotações",
                data=gerar_texto_anotacoes(),
                file_name="ANOTACOES_ADVOGADOS.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        anotacoes_filtradas = [
            (i, a) for i, a in enumerate(st.session_state["anotacoes_advogados"])
            if busca_adv.lower() in a["nome"].lower() or busca_adv.lower() in a["oab"].lower()
        ]

        for index, adv in anotacoes_filtradas:
            with st.container(border=True):
                col_det, col_del = st.columns([5, 1])
                
                with col_det:
                    st.markdown(f"### 👤 {adv['nome']} `(OAB: {adv['oab']})`")
                    st.markdown(f"**📞 Contato:** {adv['contato']} | **🏢 Escritório:** {adv['escritorio']}")
                    st.info(f"**📝 Observações:**\n\n{adv['notas']}")

                with col_del:
                    if st.button("🗑️ Excluir", key=f"del_adv_{index}", type="secondary"):
                        st.session_state["anotacoes_advogados"].pop(index)
                        st.rerun()
