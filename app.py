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
# 🔄 FUNÇÕES DE EXTRAÇÃO - FORMATO REAL
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

def extrair_telefones_do_bloco(bloco):
    """Extrai telefones no formato (XX) XXXX-XXXX ou (XX) XXXXX-XXXX"""
    telefones = []
    
    # Padrão: (87) 3856-1266 ou (87) 99638-2559
    padrao = r'\(?(\d{2})\)?\s*(\d{4,5})-?(\d{4})'
    matches = re.findall(padrao, bloco)
    
    for ddd, num1, num2 in matches:
        numero_limpo = f"55{ddd}{num1}{num2}"
        if numero_limpo not in telefones:
            telefones.append(numero_limpo)
    
    return telefones

def extrair_advogados_do_bloco(bloco, polo=""):
    """Extrai advogados no formato: NOME (CPF: XXXX)"""
    advogados = []
    
    # Padrão: Advogado: NOME (CPF: 123456789)
    # ou: - ADVOGADO: NOME (CPF: 123456789)
    padrao = r'Advogado:\s*([^;(]+?)\s*\(CPF:\s*(\d+)\)'
    matches = re.findall(padrao, bloco, re.IGNORECASE)
    
    for nome, cpf in matches:
        nome = nome.strip()
        # Remover duplicados
        if not any(a["nome"] == nome for a in advogados):
            advogados.append({
                "nome": nome,
                "cpf": cpf,
                "polo": polo
            })
    
    return advogados

def extrair_partes_passivo(bloco):
    """Extrai múltiplas partes do polo passivo"""
    partes = []
    
    # Encontrar todas as partes no polo passivo
    padrao_partes = r'- NOME:\s*(.+?)\n(.*?)(?=- NOME:|- ADVOGADO:|PROCESSO:|$)'
    matches = re.findall(padrao_partes, bloco, re.DOTALL)
    
    for nome, detalhes in matches:
        parte = {
            "nome": nome.strip(),
            "doc": "",
            "renda": "",
            "idade": "",
            "telefones": []
        }
        
        # Extrair DOC
        doc_match = re.search(r'DOC:\s*(\d+)', detalhes)
        if doc_match:
            parte["doc"] = doc_match.group(1)
        
        # Extrair RENDA
        renda_match = re.search(r'RENDA:\s*(.+?)(?:\n|$)', detalhes)
        if renda_match:
            parte["renda"] = renda_match.group(1).strip()
        
        # Extrair IDADE
        idade_match = re.search(r'IDADE:\s*(\d+)', detalhes)
        if idade_match:
            parte["idade"] = idade_match.group(1)
        
        # Extrair TELEFONES
        parte["telefones"] = extrair_telefones_do_bloco(detalhes)
        
        partes.append(parte)
    
    return partes

def processar_relatorio_completo(texto):
    """Processa o relatório no formato real"""
    # Separar processos pelo separador
    blocos_processos = re.split(r'-{3,}', texto)
    
    processos = []
    
    for idx, bloco in enumerate(blocos_processos):
        if not bloco.strip() or "PROCESSO:" not in bloco:
            continue
        
        # Extrair campos básicos
        processo = {
            "id": idx,
            "numero": extrair_campo_simples(r'PROCESSO:\s*([\d\-\.]+)', bloco),
            "link": extrair_campo_simples(r'LINK:\s*(.+)', bloco),
            "tribunal": extrair_campo_simples(r'TRIBUNAL:\s*(.+)', bloco),
            "classe": extrair_campo_simples(r'CLASSE:\s*(.+)', bloco),
            "assunto": extrair_campo_simples(r'ASSUNTO:\s*(.+)', bloco),
            "valor": extrair_campo_simples(r'VALOR:\s*(.+)', bloco),
            "data_inicio": extrair_campo_simples(r'DATA INICIO:\s*(.+)', bloco),
            "orgao_julgador": extrair_campo_simples(r'ORGAO JULGADOR:\s*(.+)', bloco),
        }
        
        # Separar polos
        polo_ativo_texto = ""
        polo_passivo_texto = ""
        
        match_ativo = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:)', bloco, re.DOTALL)
        match_passivo = re.search(r'POLO PASSIVO:(.*?)$', bloco, re.DOTALL)
        
        if match_ativo:
            polo_ativo_texto = match_ativo.group(1)
        if match_passivo:
            polo_passivo_texto = match_passivo.group(1)
        
        # POLO ATIVO
        processo["polo_ativo"] = {
            "nome": extrair_campo_simples(r'NOME:\s*(.+)', polo_ativo_texto),
            "doc": extrair_campo_simples(r'DOC:\s*(\d+)', polo_ativo_texto),
            "renda": extrair_campo_simples(r'RENDA:\s*(.+)', polo_ativo_texto),
            "idade": extrair_campo_simples(r'IDADE:\s*(\d+)', polo_ativo_texto),
            "telefones": extrair_telefones_do_bloco(polo_ativo_texto),
            "advogados": extrair_advogados_do_bloco(polo_ativo_texto, "ATIVO")
        }
        
        # POLO PASSIVO (pode ter múltiplas partes)
        processo["partes_passivo"] = extrair_partes_passivo(polo_passivo_texto)
        processo["advogados_passivo"] = extrair_advogados_do_bloco(polo_passivo_texto, "PASSIVO")
        
        # Telefones consolidados
        todos_telefones = processo["polo_ativo"]["telefones"][:]
        for parte in processo["partes_passivo"]:
            todos_telefones.extend(parte["telefones"])
        processo["todos_telefones"] = list(set(todos_telefones))
        
        # Advogados consolidados
        processo["todos_advogados"] = processo["polo_ativo"]["advogados"] + processo["advogados_passivo"]
        
        # Verificar restrito
        processo["restrito"] = any(
            termo in bloco.lower() 
            for termo in ["ocultada", "ocultado", "res. 121", "segredo de justiça", "sigilo"]
        )
        
        processo["texto_completo"] = bloco
        processos.append(processo)
    
    return processos

def extrair_campo_simples(padrao, texto, padrao_padrao="Não informado"):
    match = re.search(padrao, texto, re.IGNORECASE)
    return match.group(1).strip() if match else padrao_padrao

def salvar_consulta(origem, conteudo):
    historicos = carregar_dados("historicos.json")
    usuario = st.session_state.usuario
    
    if usuario not in historicos:
        historicos[usuario] = []
    
    consulta = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "origem": origem,
        "processos": len(processar_relatorio_completo(conteudo)),
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
        with col_insta:
            insta_adv = st.text_input("Instagram:", key="insta_adv")
            if insta_adv.strip():
                limpo = insta_adv.strip().replace("@", "")
                st.link_button("📸 Instagram", f"https://instagram.com/{limpo}", use_container_width=True)
        
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
        
        processos = processar_relatorio_completo(st.session_state.conteudo)
        
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
            
            # Exibir cada processo
            for p in processos_filtrados:
                with st.container(border=True):
                    if p["restrito"]:
                        st.warning("⚠️ PROCESSO RESTRITO")
                    
                    st.markdown(f"### 📌 Processo: {p['numero']}")
                    
                    # Informações principais
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"⚖️ **Tribunal:** {p['tribunal']}")
                        st.write(f"📋 **Classe:** {p['classe']}")
                        st.write(f"📝 **Assunto:** {p['assunto']}")
                        st.write(f"💰 **Valor:** {p['valor']}")
                        st.write(f"📅 **Início:** {p['data_inicio']}")
                    
                    with col2:
                        if p.get("link"):
                            st.link_button("🔗 Abrir Processo", p["link"], use_container_width=True)
                    
                    st.markdown("---")
                    
                    # POLO ATIVO
                    st.markdown("### 👤 Polo Ativo")
                    pa = p["polo_ativo"]
                    st.write(f"**Nome:** {pa['nome']}")
                    if pa['doc']:
                        st.write(f"**Documento:** {pa['doc']}")
                    if pa['renda']:
                        st.write(f"**Renda:** {pa['renda']}")
                    if pa['idade']:
                        st.write(f"**Idade:** {pa['idade']} anos")
                    
                    # Telefones do Polo Ativo
                    if pa['telefones']:
                        with st.expander(f"📞 Telefones ({len(pa['telefones'])})", expanded=False):
                            for tel in pa['telefones']:
                                ddd = tel[2:4]
                                num = tel[4:]
                                if len(num) == 9:
                                    tel_formatado = f"({ddd}) {num[:5]}-{num[5:]}"
                                else:
                                    tel_formatado = f"({ddd}) {num[:4]}-{num[4:]}"
                                
                                col_tel, col_copy, col_whats = st.columns([3, 1, 1])
                                with col_tel:
                                    st.code(tel_formatado)
                                with col_copy:
                                    if st.button("📋", key=f"copy_at_{p['id']}_{tel}", help="Copiar"):
                                        st.toast("✅ Copiado!")
                                with col_whats:
                                    st.link_button("💬", f"https://wa.me/{tel}", key=f"whats_at_{p['id']}_{tel}")
                    
                    # Advogados do Polo Ativo
                    if pa['advogados']:
                        with st.expander(f"👨‍⚖️ Advogados - Polo Ativo ({len(pa['advogados'])})", expanded=False):
                            for adv in pa['advogados']:
                                st.write(f"• **{adv['nome']}** - CPF: {adv['cpf']}")
                    
                    st.markdown("---")
                    
                    # POLO PASSIVO
                    st.markdown("### 🏛️ Polo Passivo")
                    
                    if p['partes_passivo']:
                        for i, parte in enumerate(p['partes_passivo']):
                            with st.container(border=True):
                                st.write(f"**Parte {i+1}: {parte['nome']}**")
                                if parte['doc']:
                                    st.write(f"📄 Doc: {parte['doc']}")
                                if parte['renda']:
                                    st.write(f"💰 Renda: {parte['renda']}")
                                if parte['idade']:
                                    st.write(f"🎂 Idade: {parte['idade']} anos")
                                
                                if parte['telefones']:
                                    with st.expander(f"📞 Telefones ({len(parte['telefones'])})", expanded=False):
                                        for tel in parte['telefones']:
                                            ddd = tel[2:4]
                                            num = tel[4:]
                                            if len(num) == 9:
                                                tel_formatado = f"({ddd}) {num[:5]}-{num[5:]}"
                                            else:
                                                tel_formatado = f"({ddd}) {num[:4]}-{num[4:]}"
                                            
                                            col_tel, col_copy, col_whats = st.columns([3, 1, 1])
                                            with col_tel:
                                                st.code(tel_formatado)
                                            with col_copy:
                                                if st.button("📋", key=f"copy_pass_{p['id']}_{i}_{tel}", help="Copiar"):
                                                    st.toast("✅ Copiado!")
                                            with col_whats:
                                                st.link_button("💬", f"https://wa.me/{tel}", key=f"whats_pass_{p['id']}_{i}_{tel}")
                    
                    # Advogados do Polo Passivo
                    if p['advogados_passivo']:
                        with st.expander(f"👨‍⚖️ Advogados - Polo Passivo ({len(p['advogados_passivo'])})", expanded=False):
                            for adv in p['advogados_passivo']:
                                st.write(f"• **{adv['nome']}** - CPF: {adv['cpf']}")
                    
                    # Texto completo
                    with st.expander("📄 Ver texto completo do processo"):
                        st.code(p["texto_completo"], language=None)
                    
                    st.markdown("---")
            
            # Downloads
            st.markdown("---")
            st.markdown("### 📥 Downloads")
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                texto_visiveis = "\n----------------------------------------------\n".join([p["texto_completo"] for p in processos_filtrados])
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
        
        with st.expander("📋 Contas Existentes", expanded=True):
            for u in usuarios:
                st.write(f"👤 **{u}**")
        
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
        
        if len(usuarios) > 1:
            with st.expander("🗑️ Excluir Conta"):
                user_del = st.selectbox("Selecionar", [u for u in usuarios if u != "admin"])
                if st.button("Excluir Conta", use_container_width=True):
                    del usuarios[user_del]
                    salvar_dados("usuarios.json", usuarios)
                    st.success(f"✅ Conta '{user_del}' excluída!")
                    st.rerun()