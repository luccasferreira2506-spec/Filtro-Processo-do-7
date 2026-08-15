import streamlit as st
import json
import os
from datetime import datetime, timedelta
import hashlib
import re
from pathlib import Path

# ============= CONFIG =============
st.set_page_config(
    page_title="Painel Supremo do Sete V2.2",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============= ESTILOS CSS =============
st.markdown("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    :root {
        --primary: #1e3a8a;
        --accent: #dc2626;
        --success: #16a34a;
        --warning: #ea580c;
        --bg: #f8fafc;
        --card: #ffffff;
        --border: #e2e8f0;
        --text: #1e293b;
        --muted: #64748b;
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
        background-color: var(--bg);
        color: var(--text);
    }
    
    .main {
        background-color: var(--bg);
        padding: 0 !important;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: var(--bg);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 2px solid var(--border);
    }
    
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid var(--primary);
    }
    
    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    
    .card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        border-color: var(--primary);
    }
    
    .card-header {
        font-size: 18px;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 12px;
        border-bottom: 2px solid var(--border);
        padding-bottom: 8px;
    }
    
    .info-group {
        background: var(--bg);
        border-left: 4px solid var(--primary);
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    
    .info-label {
        font-weight: 600;
        color: var(--muted);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    
    .info-value {
        font-size: 15px;
        color: var(--text);
        word-break: break-all;
        font-family: 'Courier New', monospace;
        font-weight: 500;
    }
    
    .badge-danger {
        display: inline-block;
        background: #fee2e2;
        color: var(--accent);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    
    .processo-container {
        border: 2px solid var(--border);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        background: var(--card);
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .processo-container:hover {
        border-color: var(--primary);
        background: #f9fafb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .filtro-container {
        background: var(--card);
        border: 2px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin: 20px;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .stats-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
    }
    
    .stat-box {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 4px solid var(--primary);
        padding: 12px;
        border-radius: 6px;
        text-align: center;
    }
    
    .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary);
    }
    
    .stat-label {
        font-size: 12px;
        color: var(--muted);
        font-weight: 600;
        margin-top: 4px;
    }
    
    .parte-item {
        background: var(--bg);
        border-left: 3px solid var(--accent);
        padding: 12px;
        margin-bottom: 12px;
        border-radius: 6px;
    }
    
    .success-msg {
        background: #dcfce7;
        border-left: 4px solid var(--success);
        color: var(--success);
        padding: 12px;
        border-radius: 6px;
        font-weight: 500;
        margin-bottom: 16px;
    }
    
    .restricted-alert {
        background: #fee2e2;
        border-left: 4px solid var(--accent);
        color: var(--accent);
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 12px;
        font-size: 13px;
        font-weight: 500;
    }
    
    .back-button-container {
        display: flex;
        gap: 12px;
        margin-bottom: 20px;
        margin-left: 20px;
        margin-right: 20px;
    }
    
    .consulta-header {
        text-align: center;
        padding: 40px 20px;
        background: linear-gradient(135deg, #f0f9ff 0%, #f8fafc 100%);
    }
    
    .consulta-header h1 {
        color: var(--primary);
        margin-bottom: 10px;
        font-size: 32px;
    }
    
    .consulta-header p {
        color: var(--muted);
        font-size: 16px;
    }
    
    .tab-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 12px;
        margin: 30px 20px;
    }
    
    .tab-card {
        background: var(--card);
        border: 2px solid var(--border);
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .tab-card:hover {
        border-color: var(--primary);
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2);
        transform: translateY(-2px);
    }
    
    .tab-card h3 {
        color: var(--primary);
        margin-bottom: 8px;
        font-size: 18px;
    }
    
    .tab-card p {
        color: var(--muted);
        font-size: 13px;
    }
    
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        background: linear-gradient(135deg, #f0f9ff 0%, #f8fafc 100%);
    }
    
    .login-card {
        background: var(--card);
        border: 2px solid var(--border);
        border-radius: 16px;
        padding: 40px;
        width: 100%;
        max-width: 400px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 30px;
    }
    
    .login-header h1 {
        color: var(--primary);
        font-size: 28px;
        margin-bottom: 8px;
    }
    
    .login-header p {
        color: var(--muted);
        font-size: 14px;
    }
    
    @media (max-width: 768px) {
        .tab-container {
            grid-template-columns: 1fr;
        }
        
        .login-card {
            margin: 20px;
            padding: 24px;
        }
        
        .consulta-header {
            padding: 24px 12px;
        }
        
        .consulta-header h1 {
            font-size: 24px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============= DIRETÓRIOS E ARQUIVOS =============
DATA_DIR = Path("dados")
DATA_DIR.mkdir(exist_ok=True)

USUARIOS_FILE = DATA_DIR / "usuarios.json"
HISTORICOS_FILE = DATA_DIR / "historicos.json"
SESSOES_FILE = DATA_DIR / "sessoes.json"

# ============= FUNÇÕES DE AUTENTICAÇÃO =============
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_usuarios():
    if USUARIOS_FILE.exists():
        with open(USUARIOS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_usuarios(usuarios):
    with open(USUARIOS_FILE, 'w') as f:
        json.dump(usuarios, f, indent=2)

def load_historicos():
    if HISTORICOS_FILE.exists():
        with open(HISTORICOS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_historicos(historicos):
    with open(HISTORICOS_FILE, 'w') as f:
        json.dump(historicos, f, indent=2, ensure_ascii=False)

def load_sessoes():
    if SESSOES_FILE.exists():
        with open(SESSOES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_sessoes(sessoes):
    with open(SESSOES_FILE, 'w') as f:
        json.dump(sessoes, f, indent=2)

def criar_sessao(username):
    sessoes = load_sessoes()
    sessoes[username] = {
        "criada": datetime.now().isoformat(),
        "expira": (datetime.now() + timedelta(days=30)).isoformat()
    }
    save_sessoes(sessoes)

def limpar_sessoes_expiradas():
    sessoes = load_sessoes()
    agora = datetime.now()
    sessoes_ativas = {}
    
    for username, sessao in sessoes.items():
        expira = datetime.fromisoformat(sessao["expira"])
        if expira > agora:
            sessoes_ativas[username] = sessao
    
    save_sessoes(sessoes_ativas)

def get_senha_padrao():
    """Obtém senha padrão do secrets ou usa fallback"""
    try:
        return st.secrets.get("SENHA_APP", "admin123")
    except:
        return "admin123"

# ============= PARSE DO ARQUIVO =============
def extrair_cpf(texto):
    match = re.search(r'\(CPF:\s*(\d+)\)', texto)
    return match.group(1) if match else None

def extrair_processo(texto):
    lines = texto.split('\n')
    processo = {
        'numero': '',
        'link': '',
        'tribunal': '',
        'classe': '',
        'assunto': '',
        'valor': '',
        'data_inicio': '',
        'orgao_julgador': '',
        'ultima_movimentacao': '',
        'polo_ativo': [],
        'polo_passivo': [],
        'restrito': False
    }
    
    modo = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if 'ocultada' in line.lower() or 'res. 121' in line.lower():
            processo['restrito'] = True
        
        if line.startswith('PROCESSO:'):
            processo['numero'] = line.replace('PROCESSO:', '').strip()
        elif line.startswith('LINK:'):
            processo['link'] = line.replace('LINK:', '').strip()
        elif line.startswith('TRIBUNAL:'):
            processo['tribunal'] = line.replace('TRIBUNAL:', '').strip()
        elif line.startswith('CLASSE:'):
            processo['classe'] = line.replace('CLASSE:', '').strip()
        elif line.startswith('ASSUNTO:'):
            processo['assunto'] = line.replace('ASSUNTO:', '').strip()
        elif line.startswith('VALOR:'):
            processo['valor'] = line.replace('VALOR:', '').strip()
        elif line.startswith('DATA INICIO:'):
            processo['data_inicio'] = line.replace('DATA INICIO:', '').strip()
        elif line.startswith('ORGAO JULGADOR:'):
            processo['orgao_julgador'] = line.replace('ORGAO JULGADOR:', '').strip()
        elif line.startswith('ULTIMA MOVIMENTACAO:'):
            modo = 'movimentacao'
        elif line.startswith('POLO ATIVO:'):
            modo = 'polo_ativo'
        elif line.startswith('POLO PASSIVO:'):
            modo = 'polo_passivo'
        elif line.startswith('- NOME:'):
            nome = line.replace('- NOME:', '').strip()
            if modo == 'polo_ativo':
                processo['polo_ativo'].append({'nome': nome, 'cpf': None, 'advogados': []})
            elif modo == 'polo_passivo':
                processo['polo_passivo'].append({'nome': nome, 'cpf': None, 'advogados': []})
        elif line.startswith('- ADVOGADO:') or (line.startswith('- ') and 'ADVOGADO:' in line):
            cpf = extrair_cpf(line)
            nome_adv = re.sub(r'\s*\(CPF:\s*\d+\)\s*', '', line.replace('- ADVOGADO:', '').replace('- ', '').replace('Advogado:', '')).strip()
            
            if modo == 'polo_ativo' and processo['polo_ativo']:
                processo['polo_ativo'][-1]['advogados'].append({'nome': nome_adv, 'cpf': cpf})
            elif modo == 'polo_passivo' and processo['polo_passivo']:
                processo['polo_passivo'][-1]['advogados'].append({'nome': nome_adv, 'cpf': cpf})
    
    return processo if processo['numero'] else None

def parsear_arquivo(conteudo):
    blocos = conteudo.split('----------------------------------------------')
    processos = []
    
    for bloco in blocos[1:]:
        p = extrair_processo(bloco)
        if p:
            processos.append(p)
    
    return processos

# ============= FUNÇÕES DE PROCESSAMENTO =============
def filtrar_processos(processos, termo_busca, mostrar_restritos):
    resultado = []
    
    for p in processos:
        if p['restrito'] and not mostrar_restritos:
            continue
        
        if termo_busca:
            termo = termo_busca.lower()
            encontrou = (
                termo in p['numero'].lower() or
                termo in p['classe'].lower() or
                termo in p['assunto'].lower() or
                termo in p['tribunal'].lower()
            )
            
            if not encontrou:
                for parte in p['polo_ativo'] + p['polo_passivo']:
                    if termo in parte['nome'].lower():
                        encontrou = True
                    for adv in parte['advogados']:
                        if termo in adv['nome'].lower() or (adv['cpf'] and termo in adv['cpf']):
                            encontrou = True
            
            if not encontrou:
                continue
        
        resultado.append(p)
    
    return resultado

def formatar_cpf(cpf_str):
    if not cpf_str:
        return ""
    cpf_limpo = ''.join(filter(str.isdigit, cpf_str))
    if len(cpf_limpo) == 11:
        return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
    return cpf_limpo

# ============= STATE MANAGEMENT =============
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.pagina = "login"
    st.session_state.processos_carregados = None
    st.session_state.processo_aberto_idx = None
    st.session_state.arquivo_nome = None

# ============= LOGIN PAGE =============
if not st.session_state.autenticado:
    limpar_sessoes_expiradas()
    
    st.markdown("""
    <div class="login-container">
        <div style="width: 100%; max-width: 400px; padding: 20px;">
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="login-header">
        <h1>⚖️ PAINEL SUPREMO</h1>
        <p>Sistema de Limpeza de Processos Judiciais</p>
    </div>
    """, unsafe_allow_html=True)
    
    usuario = st.text_input("👤 Usuário", placeholder="Digite seu usuário", key="login_user")
    senha = st.text_input("🔐 Senha", type="password", placeholder="Digite sua senha", key="login_pass")
    
    if st.button("🔓 ACESSAR", use_container_width=True, type="primary"):
        usuarios = load_usuarios()
        
        if not usuarios:
            senha_padrao = get_senha_padrao()
            usuarios["admin"] = hash_password(senha_padrao)
            save_usuarios(usuarios)
        
        if usuario in usuarios and usuarios[usuario] == hash_password(senha):
            st.session_state.autenticado = True
            st.session_state.usuario = usuario
            st.session_state.pagina = "consulta"
            criar_sessao(usuario)
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos")
    
    st.markdown("</div></div>", unsafe_allow_html=True)

else:
    # ============= SIDEBAR =============
    with st.sidebar:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 8px; padding: 16px; border-left: 4px solid #1e3a8a; margin-bottom: 20px;'>
            <p style='margin: 0; color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Usuário</p>
            <p style='margin: 8px 0 0 0; font-size: 16px; font-weight: 700; color: #1e3a8a;'>{st.session_state.usuario}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        if st.session_state.usuario == "admin":
            if st.button("⚙️ Admin Panel", use_container_width=True):
                st.session_state.pagina = "admin"
                st.rerun()
        
        if st.button("🚪 SAIR", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario = None
            st.session_state.pagina = "login"
            st.rerun()
    
    # ============= PÁGINA: CONSULTA =============
    if st.session_state.pagina == "consulta":
        st.markdown("""
        <div class='consulta-header'>
            <h1>⚖️ CONSULTA DE PROCESSOS</h1>
            <p>Escolha uma opção para começar</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class='tab-card' style='margin-bottom: 20px;'>
                <h3>📥 Upload .txt</h3>
                <p>Envie arquivo com processos judiciais</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class='tab-card' style='margin-bottom: 20px;'>
                <h3>📡 Telegram Bot</h3>
                <p>Consulte via bot do Telegram</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class='tab-card' style='margin-bottom: 20px;'>
                <h3>📜 Histórico</h3>
                <p>Carregue consultas anteriores</p>
            </div>
            """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📥 UPLOAD", "📡 TELEGRAM", "📜 HISTÓRICO"])
        
        with tab1:
            st.markdown('<div class="card"><div class="card-header">📥 Upload de Arquivo</div>', unsafe_allow_html=True)
            
            arquivo = st.file_uploader("Selecione arquivo .txt", type="txt", key="upload_main")
            
            if arquivo is not None:
                conteudo = arquivo.read().decode('utf-8')
                processos = parsear_arquivo(conteudo)
                
                if processos:
                    st.markdown(f"""
                    <div class="success-msg">
                        ✓ {len(processos)} processo(s) encontrado(s)
                    </div>
                    """, unsafe_allow_html=True)
                    
                    historicos = load_historicos()
                    if st.session_state.usuario not in historicos:
                        historicos[st.session_state.usuario] = []
                    
                    historicos[st.session_state.usuario].append({
                        "data": datetime.now().isoformat(),
                        "origem": "upload",
                        "arquivo": arquivo.name,
                        "processos_count": len(processos),
                        "dados": processos
                    })
                    
                    save_historicos(historicos)
                    
                    st.session_state.processos_carregados = processos
                    st.session_state.arquivo_nome = arquivo.name
                    st.session_state.pagina = "analise"
                    st.rerun()
                else:
                    st.error("❌ Nenhum processo encontrado")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown('<div class="card"><div class="card-header">📡 Consulta via Telegram</div>', unsafe_allow_html=True)
            st.info("🔧 Funcionalidade será implementada em breve")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab3:
            st.markdown('<div class="card"><div class="card-header">📜 Histórico de Consultas</div>', unsafe_allow_html=True)
            
            historicos = load_historicos()
            
            if st.session_state.usuario not in historicos or not historicos[st.session_state.usuario]:
                st.info("📂 Nenhuma consulta no histórico")
            else:
                consultas = historicos[st.session_state.usuario]
                
                for idx, consulta in enumerate(reversed(consultas), 1):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        data = datetime.fromisoformat(consulta['data']).strftime("%d/%m/%Y %H:%M:%S")
                        st.write(f"**📅 {data}**")
                    
                    with col2:
                        origem = "📤 Upload" if consulta['origem'] == 'upload' else "📡 Telegram"
                        st.write(f"{origem} | {consulta['processos_count']} processos")
                    
                    with col3:
                        if st.button("📂 Carregar", key=f"load_{idx}"):
                            st.session_state.processos_carregados = consulta['dados']
                            st.session_state.arquivo_nome = consulta.get('arquivo', 'Consulta anterior')
                            st.session_state.pagina = "analise"
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # ============= PÁGINA: ANÁLISE =============
    elif st.session_state.pagina == "analise":
        if st.session_state.processos_carregados is None:
            st.error("❌ Nenhum processo carregado")
            if st.button("← Voltar"):
                st.session_state.pagina = "consulta"
                st.rerun()
        else:
            processos = st.session_state.processos_carregados
            
            # BOTÃO VOLTAR
            st.markdown('<div class="back-button-container">', unsafe_allow_html=True)
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("← Voltar", use_container_width=True, key="btn_voltar"):
                    st.session_state.pagina = "consulta"
                    st.session_state.processos_carregados = None
                    st.session_state.processo_aberto_idx = None
                    st.rerun()
            with col2:
                st.title(f"📊 Análise - {st.session_state.arquivo_nome}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # ============= FILTROS =============
            st.markdown('<div class="filtro-container">', unsafe_allow_html=True)
            st.markdown('<div class="card-header" style="border: none; padding-bottom: 0; margin-bottom: 16px;">🔍 BUSCAR E FILTRAR</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                termo_busca = st.text_input("🔎 Buscar (CPF, processo, advogado, termo)", placeholder="Digite para filtrar...", key="search_input")
            
            with col2:
                mostrar_restritos = st.checkbox("🔒 Mostrar Restritos", value=False, key="show_restricted")
            
            processos_filtrados = filtrar_processos(processos, termo_busca, mostrar_restritos)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ============= ESTATÍSTICAS =============
            st.markdown('<div class="stats-row">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-value">{len(processos_filtrados)}</div>
                    <div class="stat-label">Processos</div>
                </div>
                """, unsafe_allow_html=True)
            
            restritos_count = sum(1 for p in processos_filtrados if p['restrito'])
            with col2:
                st.markdown(f"""
                <div class="stat-box" style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-left-color: #dc2626;">
                    <div class="stat-value" style="color: #dc2626;">{restritos_count}</div>
                    <div class="stat-label">Restritos</div>
                </div>
                """, unsafe_allow_html=True)
            
            partes_count = sum(len(p['polo_ativo']) + len(p['polo_passivo']) for p in processos_filtrados)
            with col3:
                st.markdown(f"""
                <div class="stat-box" style="background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%); border-left-color: #16a34a;">
                    <div class="stat-value" style="color: #16a34a;">{partes_count}</div>
                    <div class="stat-label">Partes</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ============= LISTA DE PROCESSOS =============
            st.markdown("---")
            st.markdown("### 📋 PROCESSOS")
            
            if not processos_filtrados:
                st.warning("❌ Nenhum processo encontra os critérios")
            else:
                for idx, p in enumerate(processos_filtrados):
                    is_open = st.session_state.processo_aberto_idx == idx
                    
                    st.markdown(f'<div class="processo-container">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([0.9, 0.1])
                    
                    with col1:
                        if st.button(
                            f"{'▼' if is_open else '▶'} {p['numero']} | {p['polo_ativo'][0]['nome'] if p['polo_ativo'] else 'N/A'}",
                            key=f"toggle_{idx}",
                            use_container_width=True
                        ):
                            if is_open:
                                st.session_state.processo_aberto_idx = None
                            else:
                                st.session_state.processo_aberto_idx = idx
                            st.rerun()
                    
                    with col2:
                        if p['restrito']:
                            st.markdown('<span class="badge-danger">🔒</span>', unsafe_allow_html=True)
                    
                    # CONTEÚDO EXPANDIDO
                    if is_open:
                        st.markdown('<div style="margin-top: 16px; padding-top: 16px; border-top: 2px solid #e2e8f0;">', unsafe_allow_html=True)
                        
                        # Informações básicas
                        st.markdown('<div class="info-group">', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label">Tribunal</div><div class="info-value">{p["tribunal"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label" style="margin-top: 8px;">Classe</div><div class="info-value">{p["classe"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label" style="margin-top: 8px;">Assunto</div><div class="info-value">{p["assunto"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label" style="margin-top: 8px;">Órgão Julgador</div><div class="info-value">{p["orgao_julgador"]}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        if p['link']:
                            st.markdown(f'<a href="{p["link"]}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #1e3a8a; color: white; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 12px;">🔗 Abrir Processo</a>', unsafe_allow_html=True)
                        
                        # POLO ATIVO
                        st.markdown('<div class="polo-section">', unsafe_allow_html=True)
                        st.markdown('<div class="card-header" style="border: none; font-size: 15px;">📍 POLO ATIVO</div>', unsafe_allow_html=True)
                        
                        for parte in p['polo_ativo']:
                            st.markdown('<div class="parte-item">', unsafe_allow_html=True)
                            st.markdown(f'<div class="info-label">Parte</div><div class="info-value">{parte["nome"]}</div>', unsafe_allow_html=True)
                            
                            if parte['advogados']:
                                st.markdown('<div class="info-label" style="margin-top: 8px;">Advogados</div>', unsafe_allow_html=True)
                                for adv in parte['advogados']:
                                    col_a, col_b = st.columns([4, 1])
                                    with col_a:
                                        st.markdown(f'<div class="info-value">{adv["nome"]}</div>', unsafe_allow_html=True)
                                    with col_b:
                                        if adv['cpf']:
                                            if st.button("📋", key=f"copy_adv_{adv['cpf']}_ativo", help="Copiar CPF", use_container_width=True):
                                                st.session_state.clipboard = formatar_cpf(adv['cpf'])
                                                st.success(f"✓ {formatar_cpf(adv['cpf'])}")
                                    st.markdown(f'<div class="info-value" style="font-size: 12px; color: #64748b; margin-top: 4px;">{formatar_cpf(adv["cpf"])}</div>', unsafe_allow_html=True)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # POLO PASSIVO (RECOLHIDO)
                        if p['polo_passivo']:
                            with st.expander("📍 POLO PASSIVO", expanded=False):
                                for parte in p['polo_passivo']:
                                    st.markdown('<div class="parte-item">', unsafe_allow_html=True)
                                    st.markdown(f'<div class="info-label">Parte</div><div class="info-value">{parte["nome"]}</div>', unsafe_allow_html=True)
                                    
                                    if parte['advogados']:
                                        st.markdown('<div class="info-label" style="margin-top: 8px;">Advogados</div>', unsafe_allow_html=True)
                                        for adv in parte['advogados']:
                                            col_a, col_b = st.columns([4, 1])
                                            with col_a:
                                                st.markdown(f'<div class="info-value">{adv["nome"]}</div>', unsafe_allow_html=True)
                                            with col_b:
                                                if adv['cpf']:
                                                    if st.button("📋", key=f"copy_adv_{adv['cpf']}_passivo", help="Copiar CPF", use_container_width=True):
                                                        st.session_state.clipboard = formatar_cpf(adv['cpf'])
                                                        st.success(f"✓ {formatar_cpf(adv['cpf'])}")
                                            st.markdown(f'<div class="info-value" style="font-size: 12px; color: #64748b; margin-top: 4px;">{formatar_cpf(adv["cpf"])}</div>', unsafe_allow_html=True)
                                    
                                    st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # ============= EXPORTAÇÃO =============
            st.markdown("---")
            st.markdown("### 📥 EXPORTAÇÃO")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Copiar CPFs", use_container_width=True):
                    cpfs = []
                    for p in processos_filtrados:
                        for parte in p['polo_ativo'] + p['polo_passivo']:
                            for adv in parte['advogados']:
                                if adv['cpf']:
                                    cpfs.append(formatar_cpf(adv['cpf']))
                    
                    if cpfs:
                        st.success(f"✓ {len(cpfs)} CPFs")
                        st.code("\n".join(cpfs))
            
            with col2:
                if st.button("👨‍⚖️ Advogados Únicos", use_container_width=True):
                    advogados_unicos = {}
                    for p in processos_filtrados:
                        for parte in p['polo_ativo'] + p['polo_passivo']:
                            for adv in parte['advogados']:
                                if adv['cpf']:
                                    advogados_unicos[adv['cpf']] = adv['nome']
                    
                    st.markdown("**Advogados Únicos:**")
                    for cpf, nome in sorted(advogados_unicos.items()):
                        st.code(f"{formatar_cpf(cpf)} | {nome}")
            
            with col3:
                if st.button("📄 Download TXT", use_container_width=True):
                    txt = "RELATÓRIO - PAINEL SUPREMO DO SETE\n"
                    txt += "=" * 80 + "\n\n"
                    
                    for p in processos_filtrados:
                        if not p['restrito']:
                            txt += f"PROCESSO: {p['numero']}\n"
                            txt += f"TRIBUNAL: {p['tribunal']}\n"
                            txt += f"CLASSE: {p['classe']}\n"
                            txt += f"ASSUNTO: {p['assunto']}\n\n"
                            
                            txt += "POLO ATIVO:\n"
                            for parte in p['polo_ativo']:
                                txt += f"  PARTE: {parte['nome']}\n"
                                for adv in parte['advogados']:
                                    txt += f"    ADVOGADO: {adv['nome']} | CPF: {formatar_cpf(adv['cpf'])}\n"
                            
                            if p['polo_passivo']:
                                txt += "\nPOLO PASSIVO:\n"
                                for parte in p['polo_passivo']:
                                    txt += f"  PARTE: {parte['nome']}\n"
                                    for adv in parte['advogados']:
                                        txt += f"    ADVOGADO: {adv['nome']} | CPF: {formatar_cpf(adv['cpf'])}\n"
                            
                            txt += "\n" + "-" * 80 + "\n\n"
                    
                    st.download_button(
                        "⬇️ Download",
                        txt,
                        f"processos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "text/plain"
                    )
    
    # ============= PÁGINA: ADMIN =============
    elif st.session_state.pagina == "admin":
        if st.button("← Voltar"):
            st.session_state.pagina = "consulta"
            st.rerun()
        
        st.title("⚙️ ADMIN PANEL")
        st.divider()
        
        acao = st.radio("Ação", ["Criar Usuário", "Deletar Usuário", "Listar Usuários"])
        
        if acao == "Criar Usuário":
            novo_user = st.text_input("Novo usuário")
            nova_senha = st.text_input("Senha", type="password")
            
            if st.button("✅ CRIAR"):
                usuarios = load_usuarios()
                if novo_user in usuarios:
                    st.error("Usuário já existe")
                else:
                    usuarios[novo_user] = hash_password(nova_senha)
                    save_usuarios(usuarios)
                    st.success(f"✓ Usuário '{novo_user}' criado")
        
        elif acao == "Deletar Usuário":
            usuarios = load_usuarios()
            user_list = [u for u in usuarios.keys() if u != "admin"]
            
            if user_list:
                user_delete = st.selectbox("Selecione usuário", user_list)
                
                if st.button("❌ DELETAR"):
                    del usuarios[user_delete]
                    save_usuarios(usuarios)
                    st.success(f"✓ Usuário '{user_delete}' deletado")
            else:
                st.info("Apenas admin existe")
        
        elif acao == "Listar Usuários":
            usuarios = load_usuarios()
            st.write("**Usuários cadastrados:**")
            for u in usuarios.keys():
                badge = "🔒 ADMIN" if u == "admin" else "👤"
                st.write(f"{badge} {u}")