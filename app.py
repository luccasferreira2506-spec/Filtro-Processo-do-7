import streamlit as st
import re
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
import extra_streamlit_components as stx

# ==============================================================================
# ⚙️ CONFIGURAÇÃO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="Painel Jurídico",
    page_icon="⚖️",
    layout="wide"
)

# Inicializar gerenciador de cookies
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# ==============================================================================
# 💾 PERSISTÊNCIA DE DADOS
# ==============================================================================
def criar_pasta_dados():
    Path("dados").mkdir(exist_ok=True)

def carregar_dados(arquivo, padrao={}):
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
# 🍪 SISTEMA DE COOKIES PARA LOGIN PERSISTENTE
# ==============================================================================
def salvar_cookie_login(usuario, lembrar=True):
    """Salva o login em cookie por 30 dias"""
    if lembrar:
        cookie_manager.set(
            "usuario_logado",
            usuario,
            expires_at=datetime.now() + timedelta(days=30)
        )
        cookie_manager.set(
            "sessao_ativa",
            "true",
            expires_at=datetime.now() + timedelta(days=30)
        )
    else:
        # Cookie de sessão (some quando fecha o navegador)
        cookie_manager.set("usuario_logado", usuario)
        cookie_manager.set("sessao_ativa", "true")

def limpar_cookie_login():
    """Remove os cookies de login"""
    cookie_manager.delete("usuario_logado")
    cookie_manager.delete("sessao_ativa")

def verificar_cookie_login():
    """Verifica se existe cookie de login válido"""
    try:
        usuario_cookie = cookie_manager.get("usuario_logado")
        sessao_ativa = cookie_manager.get("sessao_ativa")
        
        if usuario_cookie and sessao_ativa == "true":
            # Verificar se o usuário ainda existe
            usuarios = carregar_dados("usuarios.json", {"admin": "admin123"})
            if usuario_cookie in usuarios:
                return usuario_cookie
    except:
        pass
    return None

# ==============================================================================
# 🔒 SISTEMA DE LOGIN COM COOKIE
# ==============================================================================
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.lembrar = False

# Tentar login automático via cookie
if not st.session_state.logado:
    usuario_cookie = verificar_cookie_login()
    if usuario_cookie:
        st.session_state.logado = True
        st.session_state.usuario = usuario_cookie
        st.session_state.lembrar = True
        st.rerun()

if not st.session_state.logado:
    st.title("⚖️ Painel Jurídico")
    st.markdown("---")
    
    # Container de login
    with st.container(border=True):
        st.markdown("### 🔐 Faça seu login")
        
        usuario = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            lembrar = st.checkbox("🍪 Manter conectado", value=True, 
                                 help="Seu login será salvo por 30 dias")
        
        if st.button("🔓 Entrar", use_container_width=True, type="primary"):
            usuarios = carregar_dados("usuarios.json", {"admin": "admin123"})
            
            if usuario in usuarios and usuarios[usuario] == senha:
                st.session_state.logado = True
                st.session_state.usuario = usuario
                st.session_state.lembrar = lembrar
                
                # Salvar cookie
                salvar_cookie_login(usuario, lembrar)
                
                st.success("✅ Login feito com sucesso!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos")
        
        st.caption("💡 Use admin/admin123 para primeiro acesso")
    
    st.stop()

# ==============================================================================
# CONFIGURAÇÕES DO TELEGRAM
# ==============================================================================
try:
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    BOT_USERNAME = st.secrets.get("BOT_USERNAME", "")
    GRUPO_ID = int(st.secrets.get("GRUPO_IDENTIFICADOR", 0))
    STRING_SESSION = st.secrets.get("TELEGRAM_STRING_SESSION", "")
except:
    st.warning("⚠️ Configure as credenciais do Telegram no secrets.toml")

# ==============================================================================
# 📱 INTERFACE PRINCIPAL
# ==============================================================================
st.title(f"⚖️ Painel Jurídico")

# Menu na sidebar
with st.sidebar:
    # Info do usuário
    with st.container(border=True):
        st.write(f"👤 **{st.session_state.usuario}**")
        
        if st.session_state.lembrar:
            st.caption("🍪 Login salvo por 30 dias")
        else:
            st.caption("⚠️ Login válido apenas nesta sessão")
    
    # Botão de sair
    if st.button("🚪 Sair", use_container_width=True):
        limpar_cookie_login()
        st.session_state.logado = False
        st.session_state.usuario = None
        st.session_state.lembrar = False
        st.rerun()
    
    st.markdown("---")
    pagina = st.radio("📱 Menu", ["🔍 Processos", "📜 Histórico", "👥 Contas"])
    
    # Status do sistema
    with st.expander("💾 Status do Sistema"):
        if Path("dados/usuarios.json").exists():
            st.success("✅ Contas salvas")
        if Path("dados/historicos.json").exists():
            st.success("✅ Históricos salvos")
        
        # Status do cookie
        try:
            cookie_usuario = cookie_manager.get("usuario_logado")
            if cookie_usuario:
                st.success(f"🍪 Cookie ativo: {cookie_usuario}")
            else:
                st.warning("🍪 Sem cookie salvo")
        except:
            st.error("❌ Erro nos cookies")

# ==============================================================================
# 🔄 FUNÇÕES
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

def extrair_telefones(texto):
    """Extrai todos os telefones do texto"""
    telefones = []
    padroes = [
        r'\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})',
        r'(\d{2})\s*(\d{4,5})\s*(\d{4})',
        r'(\d{4,5})-?(\d{4})',
    ]
    
    for padrao in padroes:
        encontrados = re.findall(padrao, texto)
        for tel in encontrados:
            if len(tel) == 3:
                telefones.append(f"55{tel[0]}{tel[1]}{tel[2]}")
            elif len(tel) == 2:
                telefones.append(f"55{tel[0]}{tel[1]}")
    
    return list(set(telefones))

def extrair_cpf(texto):
    """Extrai CPF do texto"""
    cpf_padrao = r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'
    cpfs = re.findall(cpf_padrao, texto)
    return cpfs[0] if cpfs else None

def extrair_advogados(texto):
    """Extrai informações dos advogados"""
    advogados = []
    padrao_adv = r'ADVOGADO:.*?(?=ADVOGADO:|PROCESSO:|$)'
    matches = re.findall(padrao_adv, texto, re.DOTALL)
    
    for match in matches:
        adv = {}
        nome = re.search(r'NOME:\s*(.+?)(?:\n|$)', match)
        oab = re.search(r'OAB:\s*(.+?)(?:\n|$)', match)
        email = re.search(r'EMAIL:\s*(.+?)(?:\n|$)', match)
        telefone = re.search(r'TELEFONE:\s*(.+?)(?:\n|$)', match)
        
        if nome:
            adv["nome"] = nome.group(1).strip()
            adv["oab"] = oab.group(1).strip() if oab else "Não informado"
            adv["email"] = email.group(1).strip() if email else "Não informado"
            adv["telefone"] = telefone.group(1).strip() if telefone else None
            advogados.append(adv)
    
    return advogados

def verificar_processo_restrito(texto):
    """Verifica se o processo é restrito"""
    restrito = [
        "ocultada", "ocultado", "res. 121", "segredo de justiça",
        "sigilo", "restrito", "confidencial"
    ]
    texto_lower = texto.lower()
    return any(termo in texto_lower for termo in restrito)

def processar_relatorio_completo(texto):
    """Processamento completo com todas as informações"""
    cabecalho = ""
    if "PROCESSO:" in texto:
        partes = texto.split("PROCESSO:", 1)
        cabecalho = partes[0]
        corpo = "PROCESSO:" + partes[1]
    else:
        corpo = texto
    
    processos = []
    blocos = re.split(r'\n(?=PROCESSO:)', corpo)
    
    for bloco in blocos:
        if not bloco.strip():
            continue
        
        processo = {
            "numero": extrair_campo(r'PROCESSO:\s*(.+?)(?:\n|$)', bloco),
            "tribunal": extrair_campo(r'TRIBUNAL:\s*(.+?)(?:\n|$)', bloco),
            "classe": extrair_campo(r'CLASSE:\s*(.+?)(?:\n|$)', bloco),
            "valor": extrair_campo(r'VALOR:\s*(.+?)(?:\n|$)', bloco),
            "polo_ativo": extrair_campo(r'POLO ATIVO:.*?NOME:\s*(.+?)(?:\n|$)', bloco, "Não informado"),
            "cpf_ativo": extrair_cpf(bloco),
            "polo_passivo": extrair_campo(r'POLO PASSIVO:.*?NOME:\s*(.+?)(?:\n|$)', bloco, "Não informado"),
            "cpf_passivo": extrair_cpf(bloco.split("POLO PASSIVO:")[1] if "POLO PASSIVO:" in bloco else ""),
            "telefones": extrair_telefones(bloco),
            "advogados": extrair_advogados(bloco),
            "restrito": verificar_processo_restrito(bloco),
            "texto_completo": bloco,
            "bloco_completo": bloco
        }
        
        processos.append(processo)
    
    return cabecalho, processos

def extrair_campo(padrao, texto, padrao_padrao="Não informado"):
    match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else padrao_padrao

def salvar_consulta(origem, conteudo):
    historicos = carregar_dados("historicos.json", {})
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
        arquivo = st.file_uploader("Escolha um arquivo", type="txt", key="upload1")
        
        if arquivo:
            conteudo = arquivo.read().decode('utf-8', errors='ignore')
            
            if st.button("📥 Processar Arquivo", use_container_width=True, type="primary"):
                st.session_state.conteudo = conteudo
                st.session_state.origem = f"Upload ({arquivo.name})"
                salvar_consulta(st.session_state.origem, conteudo)
                st.success("✅ Arquivo processado!")
                st.rerun()
    
    # Consulta Telegram
    with st.expander("📡 Consultar Telegram", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            uf = st.selectbox("Estado", ["SP","RJ","MG","PE","BA","CE","PR","RS","SC","GO","DF","ES","AM","PA","MA","MT","MS","PB","RN","AL","SE","PI","RO","TO","AC","AP","RR"])
        with col2:
            oab = st.text_input("Nº OAB (5 dígitos)", max_chars=5)
        
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
                        st.error("❌ Sem resposta do bot")
    
    # Mostrar processos
    if "conteudo" in st.session_state:
        st.markdown("---")
        st.subheader(f"📊 {st.session_state.origem}")
        
        cabecalho, processos = processar_relatorio_completo(st.session_state.conteudo)
        
        if processos:
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                mostrar_restritos = st.checkbox("👁️ Mostrar processos restritos", value=False)
            with col2:
                busca = st.text_input("🔍 Filtrar processos", placeholder="Digite para filtrar...")
            with col3:
                total_restritos = sum(1 for p in processos if p["restrito"])
                st.metric("Processos Restritos", total_restritos)
            
            # Filtrar processos
            processos_filtrados = []
            for p in processos:
                if p["restrito"] and not mostrar_restritos:
                    continue
                
                if busca:
                    if busca.lower() in p["texto_completo"].lower():
                        processos_filtrados.append(p)
                else:
                    processos_filtrados.append(p)
            
            # Contadores
            st.markdown(f"### 📋 Mostrando {len(processos_filtrados)} de {len(processos)} processos")
            
            # Exibir processos
            for i, p in enumerate(processos_filtrados):
                with st.expander(f"📌 {p['numero']} - {p['polo_ativo'][:50]}...", expanded=i==0):
                    
                    if p["restrito"]:
                        st.warning("⚠️ PROCESSO RESTRITO - Res. 121")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### ⚖️ Informações do Processo")
                        st.write(f"**Tribunal:** {p['tribunal']}")
                        st.write(f"**Classe:** {p['classe']}")
                        st.write(f"**Valor:** {p['valor']}")
                        
                        st.markdown("### 👤 Polo Ativo")
                        st.write(f"**Nome:** {p['polo_ativo']}")
                        if p["cpf_ativo"]:
                            cpf_col1, cpf_col2 = st.columns([3, 1])
                            with cpf_col1:
                                st.code(p["cpf_ativo"])
                            with cpf_col2:
                                if st.button("📋 Copiar", key=f"cpf_ativo_{i}"):
                                    st.toast("✅ CPF copiado!")
                                    # Aqui você pode usar JavaScript para copiar
                                    st.code(p["cpf_ativo"])
                        
                        st.markdown("### 🏛️ Polo Passivo")
                        st.write(f"**Nome:** {p['polo_passivo']}")
                        if p["cpf_passivo"]:
                            cpf_col1, cpf_col2 = st.columns([3, 1])
                            with cpf_col1:
                                st.code(p["cpf_passivo"])
                            with cpf_col2:
                                if st.button("📋 Copiar", key=f"cpf_passivo_{i}"):
                                    st.toast("✅ CPF copiado!")
                    
                    with col2:
                        st.markdown("### 📞 Contatos")
                        if p["telefones"]:
                            for j, tel in enumerate(p["telefones"]):
                                tel_formatado = tel
                                if tel.startswith("55") and len(tel) >= 12:
                                    ddd = tel[2:4]
                                    num = tel[4:]
                                    tel_formatado = f"({ddd}) {num[:5]}-{num[5:]}" if len(num) > 8 else f"({ddd}) {num[:4]}-{num[4:]}"
                                
                                col_tel1, col_tel2 = st.columns([3, 1])
                                with col_tel1:
                                    st.code(tel_formatado)
                                with col_tel2:
                                    st.link_button("💬", f"https://wa.me/{tel}", key=f"whats_{i}_{j}")
                        else:
                            st.info("📞 Nenhum telefone encontrado")
                        
                        st.markdown("### 👨‍⚖️ Advogados")
                        if p["advogados"]:
                            for adv in p["advogados"]:
                                with st.container(border=True):
                                    st.write(f"**Nome:** {adv['nome']}")
                                    st.write(f"**OAB:** {adv['oab']}")
                                    st.write(f"**Email:** {adv['email']}")
                                    
                                    if adv["telefone"]:
                                        tel_limpo = re.sub(r'\D', '', adv["telefone"])
                                        if tel_limpo:
                                            col_adv1, col_adv2 = st.columns([3, 1])
                                            with col_adv1:
                                                st.code(adv["telefone"])
                                            with col_adv2:
                                                st.link_button("💬", f"https://wa.me/55{tel_limpo}", key=f"adv_whats_{i}_{adv['nome']}")
                        else:
                            st.info("👨‍⚖️ Nenhum advogado encontrado")
                    
                    # Informações completas
                    with st.expander("📄 Ver informações completas"):
                        st.code(p["texto_completo"], language=None)
            
            # Downloads
            st.markdown("---")
            st.markdown("### 📥 Downloads")
            col1, col2 = st.columns(2)
            
            with col1:
                texto_visiveis = cabecalho + "\n".join([
                    p["bloco_completo"] for p in processos_filtrados
                ])
                st.download_button(
                    "📥 Baixar Visíveis",
                    texto_visiveis,
                    f"visiveis_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    use_container_width=True
                )
            
            with col2:
                st.download_button(
                    "📄 Baixar Completo",
                    st.session_state.conteudo,
                    f"completo_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ Nenhum processo encontrado")

elif pagina == "📜 Histórico":
    st.markdown("---")
    st.subheader("📜 Suas Consultas Salvas")
    
    historicos = carregar_dados("historicos.json", {})
    usuario = st.session_state.usuario
    
    if usuario in historicos and historicos[usuario]:
        st.info(f"💾 {len(historicos[usuario])} consultas salvas permanentemente")
        
        for i, h in enumerate(historicos[usuario]):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**📅 {h['data']}**")
                    st.write(f"📌 {h['origem']}")
                    st.write(f"📊 {h['processos']} processos")
                with col2:
                    if st.button("🔄 Carregar", key=f"hist_{i}", use_container_width=True):
                        st.session_state.conteudo = h["conteudo"]
                        st.session_state.origem = h["origem"]
                        st.success("✅ Carregado!")
                        st.rerun()
        
        if st.button("🗑️ Limpar Meu Histórico", use_container_width=True):
            historicos[usuario] = []
            salvar_dados("historicos.json", historicos)
            st.success("✅ Histórico limpo!")
            st.rerun()
    else:
        st.info("📝 Nenhuma consulta salva ainda")

elif pagina == "👥 Contas":
    if st.session_state.usuario != "admin":
        st.error("🔒 Apenas admin pode gerenciar contas")
    else:
        st.markdown("---")
        st.subheader("👥 Gerenciar Contas")
        
        usuarios = carregar_dados("usuarios.json", {"admin": "admin123"})
        
        # Listar contas
        with st.expander("📋 Contas Existentes", expanded=True):
            for user in usuarios:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"👤 **{user}**")
                with col2:
                    st.caption("🔒 Protegido" if user == "admin" else "👤 Usuário")
        
        # Criar conta
        with st.expander("➕ Criar Nova Conta"):
            novo_user = st.text_input("Usuário", key="novo_user")
            nova_senha = st.text_input("Senha", type="password", key="nova_senha")
            
            if st.button("Criar Conta", use_container_width=True, type="primary"):
                if novo_user and nova_senha:
                    if novo_user not in usuarios:
                        usuarios[novo_user] = nova_senha
                        salvar_dados("usuarios.json", usuarios)
                        st.success(f"✅ Conta {novo_user} criada! Já pode fazer login.")
                        st.balloons()
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
                    st.success(f"✅ Conta {user_del} excluída!")
                    st.rerun()