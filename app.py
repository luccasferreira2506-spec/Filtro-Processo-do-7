import streamlit as st
import re

# Configuração da página em modo amplo (wide)
st.set_page_config(page_title="Painel de Processos", page_icon="⚖️", layout="wide")

def extrair_campo(padrao, texto, padrao_padrao="Não informado"):
    match = re.search(padrao, texto, re.IGNORECASE)
    return match.group(1).strip() if match else padrao_padrao

def processar_relatorio(conteudo_texto):
    pos_primeiro = conteudo_texto.find('PROCESSO:')
    if pos_primeiro != -1:
        cabecalho = conteudo_texto[:pos_primeiro]
        corpo = conteudo_texto[pos_primeiro:]
    else:
        cabecalho = ""
        corpo = conteudo_texto

    blocos = re.split(r'\n(?=PROCESSO:)', corpo)
    processos_validos = []
    txt_filtrado_blocos = []
    removidos = 0

    for bloco in blocos:
        if not bloco.strip():
            continue
        
        # Filtra se o Polo Ativo estiver ocultado
        polo_ativo_match = re.search(r'POLO ATIVO:(.*?)(?=POLO PASSIVO:|\Z)', bloco, re.DOTALL)
        if polo_ativo_match:
            trecho_ativo = polo_ativo_match.group(1).lower()
            if any(termo in trecho_ativo for termo in ["ocultada", "ocultado", "res. 121"]):
                removidos += 1
                continue

        txt_filtrado_blocos.append(bloco)
        
        # Extrai campos para a interface visual
        proc = {
            "numero": extrair_campo(r'PROCESSO:\s*(.*)', bloco),
            "link": extrair_campo(r'LINK:\s*(.*)', bloco, ""),
            "tribunal": extrair_campo(r'TRIBUNAL:\s*(.*)', bloco),
            "classe": extrair_campo(r'CLASSE:\s*(.*)', bloco),
            "valor": extrair_campo(r'VALOR:\s*(.*)', bloco),
            "polo_ativo_nome": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "polo_ativo_doc": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*DOC:\s*(.*?)\n', bloco, "Sem CPF/DOC"),
            "polo_ativo_renda": extrair_campo(r'POLO ATIVO:\s*[\s\S]*?-\s*RENDA:\s*(.*?)\n', bloco),
            "polo_passivo_nome": extrair_campo(r'POLO PASSIVO:\s*[\s\S]*?-\s*NOME:\s*(.*?)\n', bloco),
            "bloco_completo": bloco
        }
        processos_validos.append(proc)

    texto_final = cabecalho + "".join(txt_filtrado_blocos)
    return texto_final, processos_validos, len(blocos), len(processos_validos), removidos

# --- INTERFACE ---
st.title("⚖️ Painel Interativo de Processos")
st.write("Faça upload do relatório em `.txt` para filtrar polos ocultados e gerenciar a lista de forma visual.")

arquivo_enviado = st.file_uploader("Selecione o arquivo de texto (.txt)", type=["txt"])

if arquivo_enviado is not None:
    conteudo = arquivo_enviado.read().decode('utf-8', errors='ignore')
    txt_filtrado, processos, total, mantidos, removidos = processar_relatorio(conteudo)

    # Dashboard de Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Processos", total)
    c2.metric("Mantidos (Visíveis)", mantidos)
    c3.metric("Removidos (Ocultados)", removidos)

    st.markdown("---")

    # Controles: Download e Busca
    col_dl, col_search = st.columns([1, 2])
    with col_dl:
        st.download_button(
            label="📥 Baixar TXT Filtrado",
            data=txt_filtrado,
            file_name=f"filtrado_{arquivo_enviado.name}",
            mime="text/plain",
            type="primary",
            use_container_width=True
        )
    
    with col_search:
        busca = st.text_input("🔍 Pesquisar por Nome, CPF ou Nº do Processo", "")

    # Filtragem em tempo real pela barra de busca
    if busca:
        processos_exibidos = [
            p for p in processos 
            if busca.lower() in p["numero"].lower() 
            or busca.lower() in p["polo_ativo_nome"].lower() 
            or busca.lower() in p["polo_ativo_doc"].lower()
        ]
    else:
        processos_exibidos = processos

    st.subheader(f"📋 Exibindo {len(processos_exibidos)} processos")

    # Renderização dos Cards
    for p in processos_exibidos:
        with st.container(border=True):
            col_info, col_valores, col_copiar = st.columns([2.5, 2, 1.2])
            
            with col_info:
                st.markdown(f"**📌 Processo:** `{p['numero']}`")
                st.markdown(f"**👤 Polo Ativo:** {p['polo_ativo_nome']}")
                st.markdown(f"**🏢 Polo Passivo:** {p['polo_passivo_nome']}")

            with col_valores:
                st.markdown(f"**⚖️ Classe:** {p['classe']}")
                st.markdown(f"**💰 Valor da Causa:** {p['valor']}")
                st.markdown(f"**💵 Renda:** {p['polo_ativo_renda']}")

            with col_copiar:
                st.caption("📋 **Copiar CPF / DOC:**")
                # O bloco st.code cria um campo visual com botão nativo de cópia em 1 clique
                st.code(p['polo_ativo_doc'], language=None)
                if p['link']:
                    st.link_button("🔗 Abrir Processo", p['link'], use_container_width=True)

            # Sanfona com todos os detalhes originais (Telefones, Advogado, Movimentações)
            with st.expander("🔍 Ver detalhes completos do processo"):
                st.text(p['bloco_completo'])
