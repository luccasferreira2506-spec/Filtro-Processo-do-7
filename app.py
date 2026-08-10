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
    # Telegram
    API_ID = int(st.secrets["API_ID"])
    API_HASH = st.secrets["API_HASH"]
    BOT_USERNAME = st.secrets.get("BOT_USERNAME", "")
    GRUPO_ID = int(st.secrets.get("GRUPO_IDENTIFICADOR", 0))
    STRING_SESSION = st.secrets.get("TELEGRAM_STRING_SESSION", "")
    
    # Senhas
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
            
            # Se não existir usuários, criar admin com senha do secrets
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

# Renovar sessão
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
    telefones = []
    padroes = [
        r'\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})',
        r'(\d{2})\s*(\d{4,5})\s*(\d{4})',
    ]
    
    for padrao in padroes:
        encontrados = re.findall(padrao, texto)
        for tel in encontrados:
            if len(tel) == 2:
                telefones.append(f"55{tel[0]}{tel[1]}")
    
    return list(set(telefones))

def extrair_cpf(texto):
    cpf_padrao = r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'
    cpfs = re.findall(cpf_padrao, texto)
    return cpfs[0] if cpfs else None

def extrair_advogados(texto):
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
    restrito = ["ocultada", "ocultado", "res. 121", "segredo de justiça", "sigilo"]
    texto_lower = texto.lower()
    return any(termo in texto_lower for termo in restrito)

def processar_relatorio(texto):
    if "PROCESSO:" in texto:
        partes = texto.split("PROCESSO:", 1)
        cabecalho = partes[0]
        corpo = "PROCESSO:" + partes[1]
    else:
        cabecalho = ""
        corpo = texto
    
    processos = []
    blocos = re.split(r'\n(?=PROCESSO:)', corpo)
    
    for bloco in blocos:
        if not bloco.strip():
            continue
        
        numero = re.search(r'PROCESSO:\s*([\d\-\.]+)', bloco)
        tribunal = re.search(r'TRIBUNAL:\s*(.+?)(?:\n|$)', bloco)
        classe = re.search(r'CLASSE:\s*(.+?)(?:\n|$)', bloco)
        valor = re.search(r'VALOR:\s*(.+?)(?:\n|$)', bloco)
        
        processo = {
            "numero": numero.group(1).strip() if numero else "Não informado",
            "tribunal": tribunal.group(1).strip() if tribunal else "Não informado",
            "classe": classe.group(1).strip() if classe else "Não informado",
            "valor": valor.group(1).strip() if valor else "Não informado",
            "telefones": extrair_telefones(bloco),
            "cpf": extrair_cpf(bloco),
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
        "processos": len(processar_relatorio(conteudo)[1]),
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
    
    # Upload
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
    
    # Telegram
    with st.expander("📡 Consultar Telegram", expanded=False):
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
        
        cabecalho, processos = processar_relatorio(st.session_state.conteudo)
        
        if processos:
            col1, col2 = st.columns(2)
            with col1:
                mostrar_restritos = st.checkbox("👁️ Mostrar restritos", value=False)
            with col2:
                busca = st.text_input("🔍 Buscar", placeholder="Número, nome...")
            
            processos_filtrados = []
            for p in processos:
                if p["restrito"] and not mostrar_restritos:
                    continue
                if busca and busca.lower() not in p["texto_completo"].lower():
                    continue
                processos_filtrados.append(p)
            
            st.success(f"📋 {len(processos_filtrados)} processos")
            
            for i, p in enumerate(processos_filtrados):
                with st.expander(f"📌 {p['numero']}", expanded=(i==0)):
                    if p["restrito"]:
                        st.warning("⚠️ RESTRITO")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"⚖️ **Tribunal:** {p['tribunal']}")
                        st.write(f"📋 **Classe:** {p['classe']}")
                        st.write(f"💰 **Valor:** {p['valor']}")
                        
                        if p["cpf"]:
                            st.code(f"CPF: {p['cpf']}")
                    
                    with col2:
                        if p["telefones"]:
                            st.write("📞 **Contatos:**")
                            for tel in p["telefones"]:
                                col_tel, col_btn = st.columns([3, 1])
                                with col_tel:
                                    st.code(tel)
                                with col_btn:
                                    st.link_button("💬", f"https://wa.me/{tel}")
                        
                        if p["advogados"]:
                            st.write("👨‍⚖️ **Advogados:**")
                            for adv in p["advogados"]:
                                with st.container(border=True):
                                    st.write(f"**{adv['nome']}**")
                                    st.caption(f"OAB: {adv['oab']}")
                                    if adv["telefone"]:
                                        st.caption(f"📞 {adv['telefone']}")
                    
                    with st.expander("📄 Texto completo"):
                        st.code(p["texto_completo"])
            
            st.markdown("---")
            st.download_button(
                "📥 Baixar",
                st.session_state.conteudo,
                f"processos_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                use_container_width=True
            )
        else:
            st.warning("Nenhum processo encontrado")

elif pagina == "📜 Histórico":
    st.markdown("---")
    st.subheader("📜 Histórico")
    
    historicos = carregar_dados("historicos.json")
    usuario = st.session_state.usuario
    
    if usuario in historicos and historicos[usuario]:
        for i, h in enumerate(historicos[usuario]):
            with st.container(border=True):
                st.write(f"📅 {h['data']} | 📊 {h['processos']} processos")
                st.caption(f"📌 {h['origem']}")
                
                if st.button("🔄 Carregar", key=f"hist_{i}", use_container_width=True):
                    st.session_state.conteudo = h["conteudo"]
                    st.session_state.origem = h["origem"]
                    st.rerun()
        
        if st.button("🗑️ Limpar Histórico", use_container_width=True):
            historicos[usuario] = []
            salvar_dados("historicos.json", historicos)
            st.rerun()
    else:
        st.info("Nenhuma consulta salva")

elif pagina == "👥 Contas":
    if st.session_state.usuario != "admin":
        st.error("🔒 Apenas admin")
    else:
        st.markdown("---")
        st.subheader("👥 Contas")
        
        usuarios = carregar_dados("usuarios.json")
        
        # Criar conta
        with st.expander("➕ Nova Conta"):
            novo = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.button("Criar", use_container_width=True):
                if novo and senha:
                    usuarios[novo] = senha
                    salvar_dados("usuarios.json", usuarios)
                    st.success(f"✅ {novo} criado!")
                    st.rerun()
        
        # Listar contas
        with st.expander("📋 Contas Existentes"):
            for u in usuarios:
                st.write(f"👤 **{u}**")
        
        # Excluir conta
        if len(usuarios) > 1:
            with st.expander("🗑️ Excluir Conta"):
                user_del = st.selectbox("Selecionar", [u for u in usuarios if u != "admin"])
                if st.button("Excluir", use_container_width=True):
                    del usuarios[user_del]
                    salvar_dados("usuarios.json", usuarios)
                    st.success(f"✅ {user_del} excluído!")
                    st.rerun()