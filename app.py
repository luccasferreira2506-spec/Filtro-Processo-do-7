import streamlit as st
import re
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

# ==============================================================================
# ⚙️ CONFIGURAÇÃO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="Painel Jurídico",
    page_icon="⚖️",
    layout="wide"
)

# ==============================================================================
# 🔐 CARREGAR CREDENCIAIS SEGURAS DO SECRETS
# ==============================================================================
try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    BOT_USERNAME = st.secrets.get("BOT_USERNAME", "")
    GRUPO_ID = int(st.secrets.get("GRUPO_IDENTIFICADOR", 0))
    STRING_SESSION = st.secrets.get("TELEGRAM_STRING_SESSION", "")
    SENHA_APP = st.secrets["SENHA_APP"]
except KeyError as e:
    st.error(f"⚠️ Configure a chave {e} no secrets.toml")
    st.stop()

# ==============================================================================
# 💾 PERSISTÊNCIA DE DADOS
# ==============================================================================
def criar_pasta_dados():
    Path("dados").mkdir(exist_ok=True)

def carregar_dados(arquivo, padrao=None):
    if padrao is None:
        padrao = {}
    try:
        if Path(f"dados/{arquivo}").exists():
            with open(f"dados/{arquivo}", 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return padrao

def salvar_dados(arquivo, dados):
    try:
        with open(f"dados/{arquivo}", 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

criar_pasta_dados()

# ==============================================================================
# 🍪 SISTEMA DE LOGIN PERSISTENTE
# ==============================================================================
def verificar_sessao_ativa():
    sessoes = carregar_dados("sessoes.json")
    agora = datetime.now()
    
    for usuario, dados in list(sessoes.items()):
        try:
            expiracao = datetime.fromisoformat(dados.get("expiracao", ""))
            if agora < expiracao:
                usuarios = carregar_dados("usuarios.json")
                if usuario in usuarios:
                    return usuario, dados.get("lembrar", False)
        except:
            pass
    
    return None, False

def salvar_sessao(usuario, lembrar=True):
    sessoes = carregar_dados("sessoes.json")
    
    if lembrar:
        expiracao = (datetime.now() + timedelta(days=30)).isoformat()
    else:
        expiracao = (datetime.now() + timedelta(hours=24)).isoformat()
    
    sessoes[usuario] = {
        "expiracao": expiracao,
        "lembrar": lembrar,
        "ultimo_acesso": datetime.now().isoformat()
    }
    
    salvar_dados("sessoes.json", sessoes)

def limpar_sessao(usuario):
    sessoes = carregar_dados("sessoes.json")
    if usuario in sessoes:
        del sessoes[usuario]
        salvar_dados("sessoes.json", sessoes)

# ==============================================================================
# 🔒 SISTEMA DE LOGIN
# ==============================================================================
if "logado" not in st.session_state:
    usuario_sessao, lembrar = verificar_sessao_ativa()
    
    if usuario_sessao:
        st.session_state.logado = True
        st.session_state.usuario = usuario_sessao
        st.session_state.lembrar = lembrar
    else:
        st.session_state.logado = False
        st.session_state.usuario = None
        st.session_state.lembrar = False

if not st.session_state.logado:
    st.title("⚖️ Painel Jurídico")
    st.markdown("---")
    
    with st.container(border=True):
        st.markdown("### 🔐 Faça seu login")
        
        usuario = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
        
        lembrar = st.checkbox("🍪 Manter conectado por 30 dias", value=True)
        
        if st.button("🔓 Entrar", use_container_width=True, type="primary"):
            usuarios = carregar_dados("usuarios.json")
            
            if not usuarios:
                usuarios = {"admin": SENHA_APP}
                salvar_dados("usuarios.json", usuarios)
            
            if usuario in usuarios and usuarios[usuario] == senha:
                st.session_state.logado = True
                st.session_state.usuario = usuario
                st.session_state.lembrar = lembrar
                salvar_sessao(usuario, lembrar)
                st.success("✅ Login feito com sucesso!")
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos")
    
    st.stop()

if st.session_state.lembrar:
    salvar_sessao(st.session_state.usuario, True)

# ==============================================================================
# 📱 INTERFACE PRINCIPAL
# ==============================================================================
st.title(f"⚖️ Painel Jurídico")

with st.sidebar:
    with st.container(border=True):
        st.write(f"👤 **{st.session_state.usuario}**")
        if st.session_state.lembrar:
            st.success("🍪 30 dias")
        else:
            st.warning("⚠️ Temporário")
    
    if st.button("🚪 Sair", use_container_width=True):
        limpar_sessao(st.session_state.usuario)
        st.session_state.logado = False
        st.rerun()
    
    st.markdown("---")
    pagina = st.radio("📱 Menu", ["🔍 Processos", "📜 Histórico", "👥 Contas"])

# ==============================================================================
# 🔄 FUNÇÕES COMPLETAS
# ==============================================================================
async def buscar_telegram(comando, identificador):
    try:
        session = StringSession(STRING_SESSION) if STRING_SESSION else 'sessao'
        client = TelegramClient(session, API_ID, API_HASH)
        await client.start()
        grupo = await client.get_entity(GRUPO_ID)
        msg_enviada = await client.send_message(grupo, comando)
        
        for _ in range(30):
            await asyncio.sleep(1)
            async for msg in client.iter_messages(grupo, limit=10):
                if msg.file and msg.id > msg_enviada.id:
                    if (msg.reply_to_msg_id == msg_enviada.id or 
                        identificador in str(msg.text or "").lower()):
                        arquivo = await client.download_media(msg.file, file=bytes)
                        await client.disconnect()
                        return arquivo
        
        await client.disconnect()
        return None
    except Exception as e:
        st.error(f"Erro Telegram: {e}")
        return None

def extrair_campo(padrao, texto, padrao_padrao="Não informado"):
    match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else padrao_padrao

def extrair_telefones(bloco):
    telefones = []
    match_tel = re.search(r'TELEFONES:\s*(.*?)(?=- ADVOGADO:|- NOME:|\Z)', bloco, re.DOTALL)
    if match_tel:
        texto_tel = match_tel.group(1)
        padroes = re.findall(r'\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})', texto_tel)
        for ddd, p1, p2 in padroes:
            num_limpo = f"55{ddd}{p1}{p2}"
            telefones.append(num_limpo)
    
    if not telefones:
        padroes = re.findall(r'\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})', bloco)
        for ddd, p1, p2 in padroes:
            num_limpo = f"55{ddd}{p1}{p2}"
            telefones.append(num_limpo)
    
    return list(set(telefones))

def extrair_dados_advogado(texto):
    nome = re.search(r'NOME:\s*(.+?)(?:\n|$)', texto)
    oab = re.search(r'OAB:\s*(.+?)(?:\n|$)', texto)
    email = re.search(r'EMAIL:\s*(.+?)(?:\n|$)', texto)
    telefone = re.search(r'TELEFONE:\s*\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})', texto)
    
    if nome:
        adv = {
            "nome": nome.group(1).strip(),
            "oab": oab.group(1).strip() if oab else "Não informado",
            "email": email.group(1).strip() if email else "Não informado",
            "telefone": None,
            "whatsapp": None
        }
        
        if telefone:
            ddd, num1, num2 = telefone.groups()
            adv["telefone"] = f"({ddd}) {num1}-{num2}"
            adv["whatsapp"] = f"55{ddd}{num1}{num2}"
        
        return adv
    return None

def extrair_advogados(bloco):
    advogados_ativos = []
    advogados_passivos = []
    
    polo_ativo_texto = ""
    polo_passivo_texto = ""
    
    match_ativo = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
    match_passivo = re.search(r'POLO PASSIVO:(.*?)(?=PROCESSO:|\Z)', bloco, re.DOTALL)
    
    if match_ativo:
        polo_ativo_texto = match_ativo.group(1)
    if match_passivo:
        polo_passivo_texto = match_passivo.group(1)
    
    padrao_adv = r'ADVOGADO:(.*?)(?=ADVOGADO:|PROCESSO:|$)'
    
    if polo_ativo_texto:
        matches = re.findall(padrao_adv, polo_ativo_texto, re.DOTALL)
        for match in matches:
            adv = extrair_dados_advogado(match)
            if adv:
                adv["polo"] = "ATIVO"
                advogados_ativos.append(adv)
    
    if polo_passivo_texto:
        matches = re.findall(padrao_adv, polo_passivo_texto, re.DOTALL)
        for match in matches:
            adv = extrair_dados_advogado(match)
            if adv:
                adv["polo"] = "PASSIVO"
                advogados_passivos.append(adv)
    
    if not advogados_ativos and not advogados_passivos:
        matches = re.findall(padrao_adv, bloco, re.DOTALL)
        for match in matches:
            adv = extrair_dados_advogado(match)
            if adv:
                adv["polo"] = "Não especificado"
                advogados_ativos.append(adv)
    
    return advogados_ativos + advogados_passivos

def verificar_processo_restrito(texto):
    restrito = ["ocultada", "ocultado", "res. 121", "segredo de justiça", "sigilo", "restrito", "confidencial"]
    texto_lower = texto.lower()
    return any(termo in texto_lower for termo in restrito)

def processar_relatorio_completo(texto):
    if "PROCESSO:" in texto:
        partes = texto.split("PROCESSO:", 1)
        cabecalho = partes[0]
        corpo = "PROCESSO:" + partes[1]
    else:
        cabecalho = ""
        corpo = texto
    
    processos = []
    blocos = re.split(r'\n(?=PROCESSO:)', corpo)
    
    for idx, bloco in enumerate(blocos):
        if not bloco.strip():
            continue
        
        processo = {
            "id": idx,
            "numero": extrair_campo(r'PROCESSO:\s*(.+?)(?:\n|$)', bloco),
            "tribunal": extrair_campo(r'TRIBUNAL:\s*(.+?)(?:\n|$)', bloco),
            "classe": extrair_campo(r'CLASSE:\s*(.+?)(?:\n|$)', bloco),
            "valor": extrair_campo(r'VALOR:\s*(.+?)(?:\n|$)', bloco),
            "polo_ativo": extrair_campo(r'POLO ATIVO:[\s\S]*?NOME:\s*(.+?)(?:\n|$)', bloco, "Não informado"),
            "doc_ativo": extrair_campo(r'POLO ATIVO:[\s\S]*?DOC:\s*(.+?)(?:\n|$)', bloco, "Não informado"),
            "renda_ativo": extrair_campo(r'POLO ATIVO:[\s\S]*?RENDA:\s*(.+?)(?:\n|$)', bloco, "Não informado"),
            "polo_passivo": extrair_campo(r'POLO PASSIVO:[\s\S]*?NOME:\s*(.+?)(?:\n|$)', bloco, "Não informado"),
            "doc_passivo": extrair_campo(r'POLO PASSIVO:[\s\S]*?DOC:\s*(.+?)(?:\n|$)', bloco, "Não informado"),
            "telefones": extrair_telefones(bloco),
            "advogados": extrair_advogados(bloco),
            "restrito": verificar_processo_restrito(bloco),
            "texto_completo": bloco
        }
        
        processos.append(processo)
    
    return cabecalho, processos

def salvar_consulta(origem, conteudo):
    historicos = carregar_dados("historicos.json")
    usuario = st.session_state.usuario
    
    if usuario not in historicos:
        historicos[usuario] = []
    
    consulta = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "origem": origem,
        "processos": len(processar_relatorio_completo(conteudo)[1]),
        "conteudo": conteudo
    }
    
    if not historicos[usuario] or historicos[usuario][0]["conteudo"] != conteudo:
        historicos[usuario].insert(0, consulta)
        salvar_dados("historicos.json", historicos)

# ==============================================================================
# 📄 PÁGINAS
# ==============================================================================
if pagina == "🔍 Processos":
    st.markdown("---")
    
    # Upload de arquivo
    with st.expander("📂 Upload de Arquivo .txt", expanded=True):
        arquivo = st.file_uploader("Escolha um arquivo", type="txt")
        
        if arquivo:
            conteudo = arquivo.read().decode('utf-8', errors='ignore')
            if st.button("📥 Processar", use_container_width=True, type="primary"):
                st.session_state.conteudo = conteudo
                st.session_state.origem = f"Upload ({arquivo.name})"
                salvar_consulta(st.session_state.origem, conteudo)
                st.success("✅ Arquivo processado!")
                st.rerun()
    
    # Consulta Telegram com dados do advogado
    with st.expander("📡 Consultar Telegram", expanded=False):
        st.markdown("### 👤 Dados do Advogado")
        
        col_nome, col_whats, col_insta = st.columns(3)
        with col_nome:
            nome_adv = st.text_input("Nome do Advogado:", key="nome_adv")
        with col_whats:
            whats_adv = st.text_input("WhatsApp:", key="whats_adv")
            if whats_adv.strip():
                limpo = re.sub(r'\D', '', whats_adv)
                st.link_button("💬 WhatsApp", f"https://wa.me/55{limpo}", use_container_width=True)
            else:
                st.caption("Digite o número")
        with col_insta:
            insta_adv = st.text_input("Instagram:", key="insta_adv")
            if insta_adv.strip():
                limpo = insta_adv.strip().replace("@", "")
                st.link_button("📸 Instagram", f"https://instagram.com/{limpo}", use_container_width=True)
            else:
                st.caption("Digite o @")
        
        st.markdown("---")
        st.markdown("### 🔍 Consultar OAB")
        
        col1, col2 = st.columns(2)
        with col1:
            uf = st.selectbox("UF", ["SP","RJ","MG","PE","BA","CE","PR","RS","SC","GO","DF","ES","AM","PA","MA","MT","MS","PB","RN","AL","SE","PI","RO","TO","AC","AP","RR"])
        with col2:
            oab = st.text_input("OAB (5 dígitos)", max_chars=5)
        
        if st.button("🚀 Consultar", use_container_width=True, type="primary"):
            if len(re.sub(r'\D', '', oab)) != 5:
                st.error("❌ OAB deve ter 5 números")
            else:
                with st.spinner("🔄 Consultando..."):
                    comando = f"/oab {uf.lower()}{re.sub(r'\D', '', oab)}"
                    resultado = asyncio.run(buscar_telegram(comando, re.sub(r'\D', '', oab)))
                    
                    if resultado:
                        texto = resultado.decode('utf-8', errors='ignore')
                        st.session_state.conteudo = texto
                        st.session_state.origem = f"Telegram ({uf}{re.sub(r'\D', '', oab)})"
                        salvar_consulta(st.session_state.origem, texto)
                        st.success("✅ Consulta realizada!")
                        st.rerun()
                    else:
                        st.error("❌ Sem resposta")
    
    # Mostrar processos
    if "conteudo" in st.session_state:
        st.markdown("---")
        st.subheader(f"📊 {st.session_state.origem}")
        
        cabecalho, processos = processar_relatorio_completo(st.session_state.conteudo)
        
        if processos:
            # Métricas
            total = len(processos)
            restritos = sum(1 for p in processos if p["restrito"])
            visiveis = total - restritos
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total", total)
            col_m2.metric("Visíveis", visiveis)
            col_m3.metric("Restritos", restritos)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                mostrar_restritos = st.checkbox("👁️ Mostrar processos restritos", value=False)
            with col2:
                busca = st.text_input("🔍 Buscar por nome, CPF ou número", placeholder="Digite para filtrar...")
            
            # Filtrar processos
            processos_filtrados = []
            for p in processos:
                if p["restrito"] and not mostrar_restritos:
                    continue
                if busca and busca.lower() not in p["texto_completo"].lower():
                    continue
                processos_filtrados.append(p)
            
            st.markdown(f"### 📋 Mostrando {len(processos_filtrados)} de {visiveis} processos visíveis")
            
            # Exibir cada processo - SEMPRE ABERTO
            for p in processos_filtrados:
                with st.container(border=True):
                    # Cabeçalho do processo
                    if p["restrito"]:
                        st.warning("⚠️ PROCESSO RESTRITO - Res. 121")
                    
                    st.markdown(f"### 📌 {p['numero']}")
                    
                    # Informações principais em 2 colunas
                    col_info, col_contatos = st.columns([3, 2])
                    
                    with col_info:
                        st.markdown("#### ⚖️ Informações do Processo")
                        st.write(f"**Tribunal:** {p['tribunal']}")
                        st.write(f"**Classe:** {p['classe']}")
                        st.write(f"**Valor:** {p['valor']}")
                        
                        st.markdown("#### 👤 Polo Ativo")
                        st.write(f"**Nome:** {p['polo_ativo']}")
                        st.write(f"**Documento:** {p['doc_ativo']}")
                        if p['renda_ativo'] != "Não informado":
                            st.write(f"**Renda:** {p['renda_ativo']}")
                        
                        st.markdown("#### 🏛️ Polo Passivo")
                        st.write(f"**Nome:** {p['polo_passivo']}")
                        st.write(f"**Documento:** {p['doc_passivo']}")
                    
                    with col_contatos:
                        # Telefones RETRÁTEIS com botões na mesma linha
                        st.markdown("#### 📞 Telefones")
                        if p["telefones"]:
                            with st.expander(f"📞 {len(p['telefones'])} telefone(s)", expanded=False):
                                for tel in p["telefones"]:
                                    # Formatar telefone
                                    if len(tel) >= 12:
                                        ddd = tel[2:4]
                                        num = tel[4:]
                                        if len(num) == 9:
                                            tel_formatado = f"({ddd}) {num[:5]}-{num[5:]}"
                                        else:
                                            tel_formatado = f"({ddd}) {num[:4]}-{num[4:]}"
                                    else:
                                        tel_formatado = tel
                                    
                                    # Número e botões na mesma linha
                                    col_num, col_copy, col_whats = st.columns([3, 1, 1])
                                    with col_num:
                                        st.code(tel_formatado, language=None)
                                    with col_copy:
                                        if st.button("📋", key=f"copy_{p['id']}_{tel}", help="Copiar número"):
                                            st.toast("✅ Copiado!")
                                    with col_whats:
                                        st.link_button("💬", f"https://wa.me/{tel}", key=f"whats_{p['id']}_{tel}")
                        else:
                            st.info("Nenhum telefone")
                        
                        # Advogados separados por polo ATIVO e PASSIVO
                        st.markdown("#### 👨‍⚖️ Advogados")
                        
                        # Separar por polo
                        adv_ativos = [a for a in p["advogados"] if a.get("polo") == "ATIVO"]
                        adv_passivos = [a for a in p["advogados"] if a.get("polo") == "PASSIVO"]
                        adv_outros = [a for a in p["advogados"] if a.get("polo") not in ["ATIVO", "PASSIVO"]]
                        
                        # Advogados do Polo ATIVO
                        if adv_ativos:
                            with st.expander(f"👨‍⚖️ Polo ATIVO ({len(adv_ativos)})", expanded=False):
                                for adv in adv_ativos:
                                    with st.container(border=True):
                                        st.write(f"**{adv['nome']}**")
                                        st.caption(f"OAB: {adv['oab']} | Email: {adv['email']}")
                                        if adv["whatsapp"]:
                                            col_tel, col_btn = st.columns([4, 1])
                                            with col_tel:
                                                st.code(adv["telefone"], language=None)
                                            with col_btn:
                                                st.link_button("💬", f"https://wa.me/{adv['whatsapp']}", key=f"adv_at_{p['id']}_{adv['nome']}")
                        
                        # Advogados do Polo PASSIVO
                        if adv_passivos:
                            with st.expander(f"👨‍⚖️ Polo PASSIVO ({len(adv_passivos)})", expanded=False):
                                for adv in adv_passivos:
                                    with st.container(border=True):
                                        st.write(f"**{adv['nome']}**")
                                        st.caption(f"OAB: {adv['oab']} | Email: {adv['email']}")
                                        if adv["whatsapp"]:
                                            col_tel, col_btn = st.columns([4, 1])
                                            with col_tel:
                                                st.code(adv["telefone"], language=None)
                                            with col_btn:
                                                st.link_button("💬", f"https://wa.me/{adv['whatsapp']}", key=f"adv_pass_{p['id']}_{adv['nome']}")
                        
                        # Outros advogados (se não identificou polo)
                        if adv_outros:
                            with st.expander(f"👨‍⚖️ Outros ({len(adv_outros)})", expanded=False):
                                for adv in adv_outros:
                                    with st.container(border=True):
                                        st.write(f"**{adv['nome']}**")
                                        st.caption(f"OAB: {adv['oab']} | Email: {adv['email']}")
                                        if adv["whatsapp"]:
                                            col_tel, col_btn = st.columns([4, 1])
                                            with col_tel:
                                                st.code(adv["telefone"], language=None)
                                            with col_btn:
                                                st.link_button("💬", f"https://wa.me/{adv['whatsapp']}", key=f"adv_out_{p['id']}_{adv['nome']}")
                        
                        if not p["advogados"]:
                            st.info("Nenhum advogado")
                    
                    # Texto completo (recolhível)
                    with st.expander("📄 Ver texto completo do processo"):
                        st.code(p["texto_completo"], language=None)
                    
                    st.markdown("---")
            
            # Downloads
            st.markdown("---")
            st.markdown("### 📥 Downloads")
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                texto_visiveis = cabecalho + "\n".join([p["texto_completo"] for p in processos_filtrados])
                st.download_button(
                    "📥 Baixar Visíveis",
                    texto_visiveis,
                    f"visiveis_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    use_container_width=True
                )
            
            with col_d2:
                st.download_button(
                    "📄 Baixar Completo",
                    st.session_state.conteudo,
                    f"completo_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    use_container_width=True
                )
        else:
            st.warning("Nenhum processo encontrado")
    
    elif "conteudo" not in st.session_state:
        st.info("👆 Use as opções acima para carregar um relatório")

elif pagina == "📜 Histórico":
    st.markdown("---")
    st.subheader("📜 Histórico de Consultas")
    
    historicos = carregar_dados("historicos.json")
    usuario = st.session_state.usuario
    
    if usuario in historicos and historicos[usuario]:
        st.info(f"💾 {len(historicos[usuario])} consultas salvas")
        
        for i, h in enumerate(historicos[usuario]):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📅 **{h['data']}**")
                    st.write(f"📌 {h['origem']}")
                    st.write(f"📊 {h['processos']} processos")
                with col2:
                    if st.button("🔄 Carregar", key=f"hist_{i}", use_container_width=True):
                        st.session_state.conteudo = h["conteudo"]
                        st.session_state.origem = h["origem"]
                        st.rerun()
        
        if st.button("🗑️ Limpar Histórico", use_container_width=True):
            historicos[usuario] = []
            salvar_dados("historicos.json", historicos)
            st.rerun()
    else:
        st.info("Nenhuma consulta salva ainda")

elif pagina == "👥 Contas":
    if st.session_state.usuario != "admin":
        st.error("🔒 Apenas o admin pode gerenciar contas")
    else:
        st.markdown("---")
        st.subheader("👥 Gerenciar Contas")
        
        usuarios = carregar_dados("usuarios.json")
        
        # Listar contas
        with st.expander("📋 Contas Existentes", expanded=True):
            for u in usuarios:
                st.write(f"👤 **{u}**")
        
        # Criar conta
        with st.expander("➕ Criar Nova Conta"):
            novo = st.text_input("Usuário", key="novo")
            senha = st.text_input("Senha", type="password", key="senha")
            
            if st.button("Criar Conta", use_container_width=True, type="primary"):
                if novo and senha:
                    if novo not in usuarios:
                        usuarios[novo] = senha
                        salvar_dados("usuarios.json", usuarios)
                        st.success(f"✅ Conta '{novo}' criada!")
                        st.rerun()
                    else:
                        st.error("❌ Usuário já existe")
        
        # Excluir conta
        if len(usuarios) > 1:
            with st.expander("🗑️ Excluir Conta"):
                user_del = st.selectbox("Selecionar", [u for u in usuarios if u != "admin"])
                if st.button("Excluir Conta", use_container_width=True):
                    del usuarios[user_del]
                    salvar_dados("usuarios.json", usuarios)
                    st.success(f"✅ Conta '{user_del}' excluída!")
                    st.rerun()