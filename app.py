import streamlit as st
import json
import os
from datetime import datetime, timedelta
import hashlib
import re
from pathlib import Path

# ============= CONFIG =============
st.set_page_config(
    page_title="Painel Supremo do Sete V2.1",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= ESTILOS CSS =============
st.markdown("""
<style>
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
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: var(--bg);
    }
    
    .main {
        background-color: var(--bg);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
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
    }
    
    .card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        border-color: var(--primary);
        transition: all 0.3s ease;
    }
    
    .card-header {
        font-size: 18px;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 12px;
        border-bottom: 2px solid var(--border);
        padding-bottom: 8px;
    }
    
    .card-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 12px;
    }
    
    @media (max-width: 768px) {
        .card-row {
            grid-template-columns: 1fr;
        }
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
        font-size: 16px;
        color: var(--text);
        word-break: break-all;
        font-family: 'Courier New', monospace;
    }
    
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    
    .badge-success {
        background: #dcfce7;
        color: var(--success);
    }
    
    .badge-warning {
        background: #fef3c7;
        color: var(--warning);
    }
    
    .badge-danger {
        background: #fee2e2;
        color: var(--accent);
    }
    
    .processo-container {
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        background: var(--card);
        transition: all 0.3s ease;
    }
    
    .processo-container:hover {
        border-color: var(--primary);
        background: #f9fafb;
    }
    
    .processo-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        padding: 8px;
        margin: -8px;
        padding: 8px;
        border-radius: 6px;
    }
    
    .processo-header:hover {
        background: var(--bg);
    }
    
    .processo-numero {
        font-family: 'Courier New', monospace;
        font-weight: 700;
        color: var(--primary);
        font-size: 15px;
    }
    
    .processo-polo {
        color: var(--muted);
        font-size: 13px;
        font-weight: 500;
    }
    
    .action-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 12px;
    }
    
    .btn-copy {
        padding: 8px 12px;
        border: 1px solid var(--border);
        border-radius: 6px;
        background: var(--bg);
        color: var(--primary);
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        font-family: monospace;
    }
    
    .btn-copy:hover {
        background: var(--primary);
        color: white;
        border-color: var(--primary);
    }
    
    .filtro-container {
        background: var(--card);
        border: 2px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .search-box {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
        flex-wrap: wrap;
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
    
    .polo-section {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 2px solid var(--border);
    }
    
    .parte-item {
        background: var(--bg);
        border-left: 3px solid var(--accent);
        padding: 12px;
        margin-bottom: 12px;
        border-radius: 6px;
    }
    
    .advogado-list {
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 12px;
        max-height: 200px;
        overflow-y: auto;
    }
    
    .advogado-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px;
        border-bottom: 1px solid var(--border);
        font-size: 13px;
    }
    
    .advogado-item:last-child {
        border-bottom: none;
    }
    
    .cp-button {
        background: #e0f2fe;
        color: var(--primary);
        border: 1px solid var(--primary);
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 11px;
        cursor: pointer;
        font-weight: 600;
    }
    
    .cp-button:hover {
        background: var(--primary);
        color: white;
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
    
    .success-msg {
        background: #dcfce7;
        border-left: 4px solid var(--success);
        color: var(--success);
        padding: 12px;
        border-radius: 6px;
        font-weight: 500;
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

# ============= PARSE DO ARQUIVO =============
def extrair_cpf(texto):
    """Extrai CPF do formato (CPF: XXXXX)"""
    match = re.search(r'\(CPF:\s*(\d+)\)', texto)
    return match.group(1) if match else None

def extrair_processo(texto):
    """Extrai dados estruturados de um bloco de processo"""
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
        
        # Detectar restrição
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
        elif line.startswith('-') and line.startswith('- NOME:'):
            nome = line.replace('- NOME:', '').strip()
            if modo == 'polo_ativo':
                processo['polo_ativo'].append({'nome': nome, 'cpf': None, 'advogados': []})
            elif modo == 'polo_passivo':
                processo['polo_passivo'].append({'nome': nome, 'cpf': None, 'advogados': []})
        elif line.startswith('- ADVOGADO:') or line.startswith('- ') and 'ADVOGADO:' in line:
            cpf = extrair_cpf(line)
            nome_adv = re.sub(r'\s*\(CPF:\s*\d+\)\s*', '', line.replace('- ADVOGADO:', '').replace('- ', '').replace('Advogado:', '')).strip()
            
            if modo == 'polo_ativo' and processo['polo_ativo']:
                processo['polo_ativo'][-1]['advogados'].append({'nome': nome_adv, 'cpf': cpf})
            elif modo == 'polo_passivo' and processo['polo_passivo']:
                processo['polo_passivo'][-1]['advogados'].append({'nome': nome_adv, 'cpf': cpf})
    
    return processo if processo['numero'] else None

def parsear_arquivo(conteudo):
    """Parse completo do arquivo de processos"""
    blocos = conteudo.split('----------------------------------------------')
    processos = []
    
    for bloco in blocos[1:]:
        p = extrair_processo(bloco)
        if p:
            processos.append(p)
    
    return processos

# ============= FUNÇÕES DE PROCESSAMENTO =============
def detectar_cpfs_duplicados(processos):
    """Agrupa CPFs e mostra quantas vezes aparecem"""
    cpf_map = {}
    
    for p in processos:
        for parte in p['polo_ativo'] + p['polo_passivo']:
            for adv in parte['advogados']:
                if adv['cpf']:
                    if adv['cpf'] not in cpf_map:
                        cpf_map[adv['cpf']] = {'nome': adv['nome'], 'processos': 0}
                    cpf_map[adv['cpf']]['processos'] += 1
    
    return cpf_map

def filtrar_processos(processos, termo_busca, mostrar_restritos, filtro_advogado):
    """Filtra processos baseado em critérios"""
    resultado = []
    
    for p in processos:
        # Filtro de restritos
        if p['restrito'] and not mostrar_restritos:
            continue
        
        # Filtro de advogado
        if filtro_advogado:
            encontrou = False
            for parte in p['polo_ativo'] + p['polo_passivo']:
                for adv in parte['advogados']:
                    if filtro_advogado.lower() in adv['nome'].lower():
                        encontrou = True
                        break
            if not encontrou:
                continue
        
        # Busca geral
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
                    if parte['cpf'] and termo in parte['cpf'].lower():
                        encontrou = True
                    for adv in parte['advogados']:
                        if termo in adv['nome'].lower() or (adv['cpf'] and termo in adv['cpf']):
                            encontrou = True
            
            if not encontrou:
                continue
        
        resultado.append(p)
    
    return resultado

def formatar_cpf(cpf_str):
    """Formata CPF como XXX.XXX.XXX-XX"""
    if not cpf_str:
        return ""
    cpf_limpo = ''.join(filter(str.isdigit, cpf_str))
    if len(cpf_limpo) == 11:
        return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
    return cpf_limpo

# ============= UI - LOGIN =============
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None

if not st.session_state.autenticado:
    limpar_sessoes_expiradas()
    
    st.markdown("""
    <div style='text-align: center; padding: 60px 20px;'>
        <h1 style='color: #1e3a8a; margin-bottom: 10px;'>⚖️ PAINEL SUPREMO DO SETE</h1>
        <p style='color: #64748b; font-size: 16px; margin-bottom: 40px;'>v2.1 - Sistema de Limpeza de Processos Judiciais</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        usuario = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("🔐 Senha", type="password", placeholder="Digite sua senha")
        
        if st.button("🔓 ACESSAR", use_container_width=True, type="primary"):
            usuarios = load_usuarios()
            
            if not usuarios:
                usuarios["admin"] = hash_password("admin123")
                save_usuarios(usuarios)
            
            if usuario in usuarios and usuarios[usuario] == hash_password(senha):
                st.session_state.autenticado = True
                st.session_state.usuario = usuario
                criar_sessao(usuario)
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos")
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # ============= SIDEBAR =============
    with st.sidebar:
        st.markdown(f"""
        <div style='background: #f0f9ff; border-radius: 8px; padding: 16px; border-left: 4px solid #1e3a8a; margin-bottom: 20px;'>
            <p style='margin: 0; color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase;'>Usuário Conectado</p>
            <p style='margin: 8px 0 0 0; font-size: 18px; font-weight: 700; color: #1e3a8a;'>{st.session_state.usuario}</p>
            {f'<p style="margin: 4px 0 0 0; color: #16a34a; font-size: 11px;">✓ Admin</p>' if st.session_state.usuario == 'admin' else ''}
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        if st.button("🚪 SAIR", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario = None
            st.rerun()
        
        st.divider()
        
        if st.session_state.usuario == "admin":
            st.markdown("### ⚙️ ADMIN")
            
            with st.expander("👥 Gerenciar Usuários", expanded=False):
                acao = st.radio("Ação", ["Criar Usuário", "Excluir Usuário", "Listar Usuários"])
                
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
                
                elif acao == "Excluir Usuário":
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
    
    # ============= MAIN =============
    st.markdown('<h1 style="text-align: center; color: #1e3a8a; margin-bottom: 30px;">⚖️ PAINEL SUPREMO DO SETE - v2.1</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📥 UPLOAD", "📊 ANÁLISE", "📜 HISTÓRICO"])
    
    # ============= TAB 1: UPLOAD =============
    with tab1:
        st.markdown('<div class="card"><div class="card-header">📥 Upload de Arquivo .txt</div>', unsafe_allow_html=True)
        
        arquivo = st.file_uploader("Selecione o arquivo de processos", type="txt", key="upload_main")
        
        if arquivo is not None:
            conteudo = arquivo.read().decode('utf-8')
            processos = parsear_arquivo(conteudo)
            
            if processos:
                st.markdown(f"""
                <div class="success-msg">
                    ✓ Arquivo processado com sucesso! {len(processos)} processo(s) encontrado(s)
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
                
                st.info("Vá para a aba **ANÁLISE** para visualizar e processar os dados")
            else:
                st.error("❌ Nenhum processo encontrado. Verifique o formato do arquivo.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ============= TAB 2: ANÁLISE =============
    with tab2:
        if "processos_carregados" not in st.session_state or not st.session_state.processos_carregados:
            st.info("📂 Nenhum arquivo carregado. Use a aba **UPLOAD** para enviar um arquivo.")
        else:
            processos = st.session_state.processos_carregados
            
            # ============= FILTROS =============
            st.markdown('<div class="filtro-container">', unsafe_allow_html=True)
            st.markdown('<div class="card-header" style="border: none; padding-bottom: 0;">🔍 FILTROS E BUSCA</div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 1.5, 1])
            
            with col1:
                termo_busca = st.text_input("🔎 Buscar (CPF, processo, advogado, termo)", placeholder="Digite para filtrar...")
            
            with col2:
                advogados = set()
                for p in processos:
                    for parte in p['polo_ativo'] + p['polo_passivo']:
                        for adv in parte['advogados']:
                            advogados.add(adv['nome'])
                
                advogados_sorted = sorted(list(advogados))
                filtro_advogado = st.selectbox("👨‍⚖️ Advogado", ["[Todos]"] + advogados_sorted)
                if filtro_advogado == "[Todos]":
                    filtro_advogado = None
            
            with col3:
                col_a, col_b = st.columns(2)
                with col_a:
                    mostrar_restritos = st.checkbox("🔒 Restritos", value=False)
                with col_b:
                    col_ba, col_bb = st.columns(2)
            
            processos_filtrados = filtrar_processos(processos, termo_busca, mostrar_restritos, filtro_advogado)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ============= ESTATÍSTICAS =============
            st.markdown('<div class="stats-row">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
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
            
            cpf_duplicados = detectar_cpfs_duplicados(processos_filtrados)
            cpfs_unicos = len(cpf_duplicados)
            
            with col3:
                st.markdown(f"""
                <div class="stat-box" style="background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%); border-left-color: #16a34a;">
                    <div class="stat-value" style="color: #16a34a;">{cpfs_unicos}</div>
                    <div class="stat-label">CPFs Únicos</div>
                </div>
                """, unsafe_allow_html=True)
            
            partes_count = sum(len(p['polo_ativo']) + len(p['polo_passivo']) for p in processos_filtrados)
            with col4:
                st.markdown(f"""
                <div class="stat-box" style="background: linear-gradient(135deg, #fef3c7 0%, #fcd34d 100%); border-left-color: #ea580c;">
                    <div class="stat-value" style="color: #ea580c;">{partes_count}</div>
                    <div class="stat-label">Partes</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ============= LISTA DE PROCESSOS =============
            st.markdown("---")
            st.markdown("### 📋 PROCESSOS ENCONTRADOS")
            
            if not processos_filtrados:
                st.warning("❌ Nenhum processo encontra os critérios de filtro")
            else:
                for idx, p in enumerate(processos_filtrados, 1):
                    st.markdown(f'<div class="processo-container">', unsafe_allow_html=True)
                    
                    # Header
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown(f'<div class="processo-numero">#{idx} {p["numero"]}</div>', unsafe_allow_html=True)
                    
                    with col2:
                        if p['restrito']:
                            st.markdown('<span class="badge badge-danger">🔒 Res. 121 / Sigilo</span>', unsafe_allow_html=True)
                    
                    with col3:
                        if st.button("📖 Abrir", key=f"open_{idx}", use_container_width=True):
                            st.session_state[f"expand_{idx}"] = not st.session_state.get(f"expand_{idx}", False)
                    
                    # Conteúdo expandido
                    if st.session_state.get(f"expand_{idx}", False):
                        # Informações básicas
                        st.markdown('<div class="info-group">', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label">Tribunal</div><div class="info-value">{p["tribunal"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label" style="margin-top: 8px;">Classe</div><div class="info-value">{p["classe"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label" style="margin-top: 8px;">Assunto</div><div class="info-value">{p["assunto"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-label" style="margin-top: 8px;">Órgão Julgador</div><div class="info-value">{p["orgao_julgador"]}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        if p['link']:
                            st.markdown(f'<a href="{p["link"]}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #1e3a8a; color: white; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 12px;">🔗 Abrir Processo no STJ</a>', unsafe_allow_html=True)
                        
                        # POLO ATIVO
                        st.markdown('<div class="polo-section">', unsafe_allow_html=True)
                        st.markdown('<div class="card-header" style="border: none; font-size: 16px;">📍 POLO ATIVO</div>', unsafe_allow_html=True)
                        
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
                                            if st.button("📋", key=f"copy_adv_{adv['cpf']}_ativo", help="Copiar CPF"):
                                                st.session_state.clipboard = formatar_cpf(adv['cpf'])
                                                st.success(f"✓ Copiado: {formatar_cpf(adv['cpf'])}")
                                    st.markdown(f'<div class="info-value" style="font-size: 12px; color: #64748b; margin-top: 4px;">{formatar_cpf(adv["cpf"])}</div>', unsafe_allow_html=True)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # POLO PASSIVO
                        if p['polo_passivo']:
                            st.markdown('<div class="polo-section">', unsafe_allow_html=True)
                            st.markdown('<div class="card-header" style="border: none; font-size: 16px;">📍 POLO PASSIVO</div>', unsafe_allow_html=True)
                            
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
                                                if st.button("📋", key=f"copy_adv_{adv['cpf']}_passivo", help="Copiar CPF"):
                                                    st.session_state.clipboard = formatar_cpf(adv['cpf'])
                                                    st.success(f"✓ Copiado: {formatar_cpf(adv['cpf'])}")
                                        st.markdown(f'<div class="info-value" style="font-size: 12px; color: #64748b; margin-top: 4px;">{formatar_cpf(adv["cpf"])}</div>', unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # ============= EXPORTAÇÃO =============
            st.markdown("---")
            st.markdown("### 📥 EXPORTAÇÃO DE DADOS")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Copiar Todos CPFs", use_container_width=True):
                    cpfs = []
                    for p in processos_filtrados:
                        for parte in p['polo_ativo'] + p['polo_passivo']:
                            for adv in parte['advogados']:
                                if adv['cpf']:
                                    cpfs.append(formatar_cpf(adv['cpf']))
                    
                    if cpfs:
                        st.session_state.clipboard_cpfs = "\n".join(cpfs)
                        st.success(f"✓ {len(cpfs)} CPFs copiados para clipboard")
                        st.code("\n".join(cpfs))
            
            with col2:
                if st.button("👨‍⚖️ Lista Advogados Únicos", use_container_width=True):
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
                if st.button("📄 Download .txt Filtrado", use_container_width=True):
                    txt = "RELATÓRIO FILTRADO - PAINEL SUPREMO DO SETE\n"
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
                        "⬇️ Download Relatório",
                        txt,
                        f"processos_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "text/plain"
                    )
    
    # ============= TAB 3: HISTÓRICO =============
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
                    st.markdown(f"**📅 {data}**")
                
                with col2:
                    origem = "📤 Upload" if consulta['origem'] == 'upload' else "📡 Telegram"
                    st.markdown(f"{origem} | {consulta['processos_count']} processos")
                
                with col3:
                    if st.button("📂 Carregar", key=f"load_{idx}"):
                        st.session_state.processos_carregados = consulta['dados']
                        st.session_state.arquivo_nome = consulta.get('arquivo', 'Consulta anterior')
                        st.switch_to("📊 ANÁLISE")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if historicos.get(st.session_state.usuario):
            if st.button("🗑️ LIMPAR TODO HISTÓRICO"):
                historicos[st.session_state.usuario] = []
                save_historicos(historicos)
                st.success("✓ Histórico limpo")
                st.rerun()
