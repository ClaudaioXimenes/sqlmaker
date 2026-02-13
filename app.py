import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# 1. Configuração da Página
st.set_page_config(page_title="SQL Maker RM - Totvs", layout="wide", page_icon="🚀")

# --- DEFINIÇÃO GLOBAL DA URL ---
LINKEDIN_URL = "https://www.linkedin.com/in/claudio-ximenes-pereira-bb090036/"

# --- FUNÇÃO DA SIDEBAR ESTABILIZADA (Sem tremedeira) ---
def adicionar_sidebar_linkedin():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤝 Conecte-se Comigo")
    st.sidebar.write("Gostou da ferramenta? Vamos ampliar nossa rede no LinkedIn!")
    
    # Botão estático e limpo para evitar conflito de renderização
    st.sidebar.markdown(
        f"""
        <a href="{LINKEDIN_URL}" target="_blank" style="text-decoration: none;">
            <div style="
                background-color: #0077b5;
                color: white;
                padding: 12px;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                border: none;
                margin-bottom: 10px;">
                🔗 Ver Perfil no LinkedIn
            </div>
        </a>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.markdown("---")

# --- FUNÇÃO DE CARREGAMENTO COM CACHE ---
@st.cache_data
def load_data():
    try:
        df_campos = pd.read_excel("CAMPOS.xlsx")
        df_sistemas = pd.read_excel("SISTEMAS.xlsx")
        df_relacoes = pd.read_excel("RELACIONAMENTOS.xlsx")
        return df_campos, df_sistemas, df_relacoes
    except Exception as e:
        st.error(f"Erro ao carregar planilhas: {e}")
        return None, None, None

# --- FUNÇÕES DE HISTÓRICO ---
def inicializar_historico():
    """Inicializa o histórico na sessão se não existir"""
    if "historico_queries" not in st.session_state:
        st.session_state.historico_queries = []

def adicionar_ao_historico(sql, tabela_principal, campos_count, tem_join=False, tem_calculo=False):
    """Adiciona uma query ao histórico da sessão"""
    inicializar_historico()
    
    timestamp = datetime.now()
    
    # Cria descrição resumida
    descricao_parts = [f"SELECT de {tabela_principal}"]
    if tem_join:
        descricao_parts.append("com JOINs")
    if tem_calculo:
        descricao_parts.append("com cálculos")
    
    descricao = " ".join(descricao_parts)
    
    item_historico = {
        "sql": sql,
        "timestamp": timestamp,
        "timestamp_str": timestamp.strftime("%d/%m/%Y %H:%M"),
        "descricao": descricao,
        "tabela": tabela_principal,
        "campos_count": campos_count,
        "favorito": False,
        "editada": False
    }
    
    # Adiciona no início da lista
    st.session_state.historico_queries.insert(0, item_historico)
    
    # Mantém apenas as últimas 10 queries (se não forem favoritas)
    queries_nao_favoritas = [q for q in st.session_state.historico_queries if not q["favorito"]]
    queries_favoritas = [q for q in st.session_state.historico_queries if q["favorito"]]
    
    if len(queries_nao_favoritas) > 10:
        queries_nao_favoritas = queries_nao_favoritas[:10]
    
    st.session_state.historico_queries = queries_favoritas + queries_nao_favoritas

def salvar_query_em_arquivo(sql, tabela_principal):
    """Salva a query em um arquivo de texto com timestamp"""
    try:
        # Cria pasta de histórico se não existir
        if not os.path.exists("historico_queries"):
            os.makedirs("historico_queries")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"historico_queries/query_{tabela_principal}_{timestamp}.sql"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"-- Query gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"-- Tabela principal: {tabela_principal}\n")
            f.write(f"-- Gerado por: SQL Maker RM\n\n")
            f.write(sql)
        
        return filename
    except Exception as e:
        st.warning(f"Não foi possível salvar automaticamente: {e}")
        return None

def toggle_favorito(index):
    """Marca/desmarca uma query como favorita"""
    if "historico_queries" in st.session_state and index < len(st.session_state.historico_queries):
        st.session_state.historico_queries[index]["favorito"] = not st.session_state.historico_queries[index]["favorito"]

def carregar_query_do_historico(index):
    """Carrega uma query do histórico para edição"""
    if "historico_queries" in st.session_state and index < len(st.session_state.historico_queries):
        query = st.session_state.historico_queries[index]
        st.session_state.sql_gerada = query["sql"]
        st.session_state.sql_editada = query["sql"]
        st.session_state.aba_ativa = "gerador"  # Muda para a aba do gerador

def atualizar_query_editada(sql_editada):
    """Atualiza a query mais recente do histórico com a versão editada"""
    inicializar_historico()
    
    if st.session_state.historico_queries and sql_editada != st.session_state.get("sql_gerada", ""):
        # Atualiza a query mais recente (primeira da lista)
        st.session_state.historico_queries[0]["sql"] = sql_editada
        st.session_state.historico_queries[0]["editada"] = True
        
        # Salva a versão editada em arquivo também
        if "tabela_atual" in st.session_state:
            arquivo_salvo = salvar_query_em_arquivo(sql_editada, st.session_state.tabela_atual)
            return arquivo_salvo
    return None

# --- CSS CUSTOMIZADO PARA SYNTAX HIGHLIGHTING E EDITOR ---
def add_custom_css():
    st.markdown("""
    <style>
    /* Editor SQL com syntax highlighting */
    .sql-editor {
        background-color: #0e1117;
        border: 1px solid #3d3d4d;
        border-radius: 8px;
        padding: 20px;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.6;
        color: #fafafa;
        margin: 10px 0;
        min-height: 200px;
    }
    
    .sql-keyword {
        color: #569cd6;
        font-weight: 600;
    }
    
    .sql-table {
        color: #4ec9b0;
    }
    
    .sql-field {
        color: #9cdcfe;
    }
    
    .sql-string {
        color: #ce9178;
    }
    
    .sql-comment {
        color: #6a9955;
        font-style: italic;
    }
    
    /* Botões de ação */
    .action-buttons {
        display: flex;
        gap: 10px;
        margin: 15px 0;
    }
    
    /* Info box */
    .info-box {
        background: #1a2332;
        border-left: 3px solid #569cd6;
        padding: 12px;
        border-radius: 4px;
        margin: 15px 0;
        font-size: 13px;
    }
    
    .success-box {
        background: #1a3326;
        border-left: 3px solid #4ec9b0;
        padding: 12px;
        border-radius: 4px;
        margin: 15px 0;
        font-size: 13px;
    }
    
    /* Estilo para o text_area SQL */
    .stTextArea textarea {
        font-family: 'Courier New', monospace !important;
        font-size: 14px !important;
        background-color: #0e1117 !important;
        color: #fafafa !important;
        border: 1px solid #3d3d4d !important;
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Função para aplicar syntax highlighting básico em SQL
def highlight_sql(sql_text):
    keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 
                'ON', 'AND', 'OR', 'GROUP BY', 'ORDER BY', 'HAVING', 'AS', 'SUM', 
                'COUNT', 'AVG', 'MAX', 'MIN', 'NOLOCK']
    
    highlighted = sql_text
    for kw in keywords:
        highlighted = highlighted.replace(kw, f'<span class="sql-keyword">{kw}</span>')
    
    return f'<div class="sql-editor">{highlighted}</div>'

# --- CABEÇALHO ---
st.title("🚀 SQL Maker - Assistente de Relatórios RM")
st.markdown("---")

# Adiciona CSS customizado
add_custom_css()

# Criando as Abas
tab_tutorial, tab_gerador, tab_historico = st.tabs(["📖 Como Usar", "🛠️ Criar minha Sentença", "🕐 Histórico"])

adicionar_sidebar_linkedin()

df_campos, df_sistemas, df_relacoes = load_data()

# --- ABA 1: TUTORIAL ---
with tab_tutorial:
    st.header("Seja bem-vindo!")
    st.markdown("""
    Esta ferramenta permite que você extraia informações do RM de forma visual.
    
    ### 📝 O Passo a Passo:
    1. **Módulo:** Escolha o sistema (Ex: P - RH).
    2. **Tabela:** Escolha o assunto (Ex: Funcionários).
    3. **Colunas:** Marque o que você quer ver no relatório.
    4. **Tabelas Relacionadas [Joins]:** Use se precisar buscar informações de outras tabelas.
    5. **Cálculos:** Use se precisar somar valores ou contar registros.
    6. **Filtros:** Use se precisar filtrar o que é mostrado.
    7. **Revise:** Uma vez gerado o script, revise-o e baixe-o, retire ou adicione informações. Lembre-se esse App é uma ferramenta de ajuda!
    """)
    st.success("Tudo pronto? Agora clique na aba **'Criar minha Sentença'** lá no topo!")
    st.markdown("---")
    st.markdown("### 🤝 Comunidade e Suporte")
    st.write("Tem alguma dúvida, encontrou um erro ou quer sugerir uma nova tabela?")
    st.link_button("🤖 Falar com o Assistente no Telegram", "https://t.me/+HC1B2Grb0UdhNzlh", use_container_width=True)

# --- ABA 2: GERADOR ---
with tab_gerador:
    if df_campos is not None:
        if st.sidebar.button("➕ Novo Script"):
            if "reset_counter" not in st.session_state:
                st.session_state.reset_counter = 0
            st.session_state.reset_counter += 1
            # Limpar a query editada ao criar novo script
            if "sql_editada" in st.session_state:
                del st.session_state.sql_editada
            st.rerun()

        seed = st.session_state.get("reset_counter", 0)

        # Normalização de nomes de colunas
        df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
        df_campos.columns = df_campos.columns.str.strip().str.upper()
        df_relacoes.columns = df_relacoes.columns.str.strip().str.upper()

        # 1. Seleção do Sistema
        df_sistemas["LABEL"] = df_sistemas["CODSISTEMA"].astype(str) + " - " + df_sistemas["DESCRICAO"]
        sistema_sel = st.selectbox("1. Qual o Módulo do RM?", df_sistemas["LABEL"], key=f"sis_{seed}")
        cod_sistema = str(df_sistemas[df_sistemas["LABEL"] == sistema_sel]["CODSISTEMA"].values[0])

        # 2. Tabela Pai
        tab_disponiveis = df_campos[df_campos["TABELA"].fillna("").str.startswith(cod_sistema)]["TABELA"].unique()
        tabela_pai = st.selectbox("2. Escolha a Tabela Principal", sorted(tab_disponiveis), key=f"pai_{seed}")

        col_nome_campo = df_campos.columns[1]
        todos_campos_pai = df_campos[df_campos["TABELA"] == tabela_pai][col_nome_campo].dropna().tolist()
        campos_pai_sel = st.multiselect(f"Quais informações de {tabela_pai} você quer?", options=todos_campos_pai, key=f"cols_pai_{seed}")

        # 3. Joins
        filhas_relacao = df_relacoes[df_relacoes["MASTERTABLE"] == tabela_pai]["CHILDTABLE"].unique().tolist()
        filhas_finais = sorted(list(set(filhas_relacao)))
        if tabela_pai in filhas_finais: filhas_finais.remove(tabela_pai)

        tabelas_filhas = st.multiselect("Deseja buscar dados em tabelas relacionadas? (Joins)", filhas_finais, key=f"fil_{seed}")

        campos_por_filha = {}
        for filha in tabelas_filhas:
            campos_da_filha = df_campos[df_campos["TABELA"] == filha][col_nome_campo].dropna().tolist()
            campos_por_filha[filha] = st.multiselect(f"Colunas de: {filha}", options=campos_da_filha, key=f"cols_{filha}_{seed}")

        # 4. Agrupamento
        st.markdown("### 📊 Adicionar Cálculos (Opcional)")
        col1, col2 = st.columns(2)
        with col1:
            op_agregacao = st.selectbox("Deseja fazer algum cálculo?", ["NENHUM", "SOMA (SUM)", "CONTAGEM (COUNT)", "MÉDIA (AVG)", "MÁXIMO (MAX)", "MÍNIMO (MIN)"], key=f"op_{seed}")
        with col2:
            if op_agregacao != "NENHUM":
                todos_escolhidos = campos_pai_sel + [item for sublist in campos_por_filha.values() for item in sublist]
                campo_metrica = st.selectbox("Calcular sobre qual coluna?", [""] + todos_escolhidos, key=f"met_{seed}")

        # 5. Filtro WHERE
        filtro_where = st.text_area("Filtros Adicionais [Tabela].[Campo] (Ex: PFUNC.CODCOLIGADA = 1 AND PFUNC.NOME LIKE '%XIMENES%')", placeholder="Digite seus filtros...", key=f"w_{seed}")

        st.markdown("---")

        # --- GERAÇÃO DA SQL ---
        if st.button("✨ GERAR MINHA SENTENÇA SQL", use_container_width=True):
            if not campos_pai_sel and not any(campos_por_filha.values()):
                st.warning("Selecione ao menos uma coluna!")
            else:
                colunas_select = [f"{tabela_pai}.{c}" for c in campos_pai_sel]
                for filha, cols in campos_por_filha.items():
                    for c in cols:
                        colunas_select.append(f"{filha}.{c}")

                if op_agregacao != "NENHUM" and 'campo_metrica' in locals() and campo_metrica:
                    map_op = {"SOMA (SUM)": "SUM", "CONTAGEM (COUNT)": "COUNT", "MÉDIA (AVG)": "AVG", "MÁXIMO (MAX)": "MAX", "MÍNIMO (MIN)": "MIN"}
                    func = map_op[op_agregacao]
                    prefixo_met = tabela_pai if campo_metrica in campos_pai_sel else ""
                    if not prefixo_met:
                        for f, cs in campos_por_filha.items():
                            if campo_metrica in cs:
                                prefixo_met = f
                                break
                    campo_final_met = f"{func}({prefixo_met}.{campo_metrica}) AS {func}_{campo_metrica}"
                    campos_gb = [c for c in colunas_select if not c.endswith(f".{campo_metrica}")]
                    select_final = ",\n  ".join(campos_gb + [campo_final_met])
                    group_by_sql = f"\nGROUP BY\n  " + ",\n  ".join(campos_gb)
                else:
                    select_final = ",\n  ".join(colunas_select)
                    group_by_sql = ""

                script = f"SELECT\n  {select_final}\nFROM {tabela_pai} (NOLOCK)"
                
                for filha in tabelas_filhas:
                    rel = df_relacoes[(df_relacoes["MASTERTABLE"] == tabela_pai) & (df_relacoes["CHILDTABLE"] == filha)]
                    if not rel.empty:
                        conds = []
                        for _, r in rel.iterrows():
                            cp_l, cf_l = str(r["MASTERFIELD"]).split(","), str(r["CHILDFIELD"]).split(",")
                            for cp, cf in zip(cp_l, cf_l):
                                conds.append(f"{tabela_pai}.{cp.strip()} = {filha}.{cf.strip()}")
                        script += f"\nINNER JOIN {filha} (NOLOCK) ON\n  " + " AND\n  ".join(conds)
                    else:
                        script += f"\nINNER JOIN {filha} (NOLOCK) ON\n  -- AJUSTE O JOIN: {tabela_pai}.ID = {filha}.ID"

                if filtro_where.strip():
                    script += f"\nWHERE {filtro_where.strip()}"
                script += group_by_sql

                # Armazena a SQL gerada no session_state
                st.session_state.sql_gerada = script
                st.session_state.sql_editada = script
                st.session_state.tabela_atual = tabela_pai  # Salva nome da tabela para uso posterior
                
                # Adiciona ao histórico
                tem_join = len(tabelas_filhas) > 0
                tem_calculo = op_agregacao != "NENHUM"
                total_campos = len(campos_pai_sel) + sum(len(cols) for cols in campos_por_filha.values())
                adicionar_ao_historico(script, tabela_pai, total_campos, tem_join, tem_calculo)
                
                # Salva em arquivo automaticamente
                arquivo_salvo = salvar_query_em_arquivo(script, tabela_pai)
                if arquivo_salvo:
                    st.session_state.ultimo_arquivo_salvo = arquivo_salvo

        # --- EXIBIÇÃO E EDIÇÃO DA SQL ---
        if "sql_editada" in st.session_state:
            st.markdown("---")
            st.markdown("### ✅ Sua Sentença SQL")
            
            st.markdown("""
            <div class="success-box">
                ✓ <strong>Tudo pronto!</strong> Você pode editar a query abaixo antes de copiar ou baixar.<br>
                💾 <em>Query salva automaticamente no histórico e em arquivo local.</em>
            </div>
            """, unsafe_allow_html=True)
            
            # Tabs para visualizar/editar
            tab_view, tab_edit = st.tabs(["👁️ Visualizar (com botão copiar)", "✏️ Editar SQL"])
            
            with tab_view:
                # Exibe SQL com botão de copiar nativo do Streamlit
                st.code(st.session_state.sql_editada, language="sql", line_numbers=True)
                st.caption("💡 Use o botão 📋 no canto superior direito do código para copiar")
            
            with tab_edit:
                # Editor de SQL (text_area editável)
                sql_editada = st.text_area(
                    "Editor SQL (você pode editar livremente):",
                    value=st.session_state.sql_editada,
                    height=300,
                    key=f"editor_sql_{seed}",
                    label_visibility="collapsed"
                )
                
                # Detecta se houve edição e atualiza
                if sql_editada != st.session_state.sql_editada:
                    st.session_state.sql_editada = sql_editada
                    
                    # Auto-save da versão editada
                    arquivo_salvo = atualizar_query_editada(sql_editada)
                    
                    # Mostra indicador de salvamento
                    st.success("✓ Edição salva automaticamente no histórico!", icon="💾")
                    if arquivo_salvo:
                        st.caption(f"📁 Arquivo atualizado: {arquivo_salvo}")
                
                # Botão manual de salvar (opcional, para garantir)
                if st.button("💾 Salvar Edição Manualmente", key="save_edit_manual"):
                    atualizar_query_editada(sql_editada)
                    st.success("✓ Versão editada salva com sucesso!")
            
            # Botão de Download (agora usa sempre a versão editada)
            st.download_button(
                "💾 Baixar .sql",
                st.session_state.sql_editada,  # Sempre pega a versão editada
                file_name=f"sentenca_{st.session_state.get('tabela_atual', 'query')}.sql",
                use_container_width=True
            )
            
            st.markdown("""
            <div class="info-box">
                💡 <strong>Dica:</strong> Edite o SQL diretamente no campo acima. Use os botões para copiar ou baixar sua query personalizada.
            </div>
            """, unsafe_allow_html=True)

# --- ABA 3: HISTÓRICO ---
with tab_historico:
    st.header("🕐 Histórico de Queries")
    
    inicializar_historico()
    
    if not st.session_state.historico_queries:
        st.info("📭 Nenhuma query gerada ainda. Vá para a aba 'Criar minha Sentença' e gere sua primeira query!")
    else:
        # Estatísticas do histórico
        total_queries = len(st.session_state.historico_queries)
        favoritas = len([q for q in st.session_state.historico_queries if q["favorito"]])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Queries", total_queries)
        with col2:
            st.metric("Favoritas", favoritas)
        with col3:
            if st.button("🗑️ Limpar Histórico"):
                st.session_state.historico_queries = []
                st.rerun()
        
        st.markdown("---")
        
        # Filtros
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            mostrar_apenas_favoritas = st.checkbox("⭐ Mostrar apenas favoritas")
        with col_filtro2:
            ordenar_por = st.selectbox("Ordenar por", ["Mais recentes", "Mais antigas", "Tabela (A-Z)"])
        
        # Filtra e ordena
        queries_exibir = st.session_state.historico_queries.copy()
        
        if mostrar_apenas_favoritas:
            queries_exibir = [q for q in queries_exibir if q["favorito"]]
        
        if ordenar_por == "Mais antigas":
            queries_exibir = list(reversed(queries_exibir))
        elif ordenar_por == "Tabela (A-Z)":
            queries_exibir = sorted(queries_exibir, key=lambda x: x["tabela"])
        
        if not queries_exibir:
            st.info("Nenhuma query encontrada com os filtros aplicados.")
        else:
            # Lista de queries
            for idx, query in enumerate(queries_exibir):
                # Encontra o índice real na lista original
                idx_real = st.session_state.historico_queries.index(query)
                
                with st.container():
                    # Título da query com badges
                    col_titulo, col_badge = st.columns([4, 1])
                    with col_titulo:
                        titulo = query['descricao']
                        if query['favorito']:
                            titulo = "⭐ " + titulo
                        if query.get('editada', False):
                            titulo = "✏️ " + titulo
                        st.markdown(f"**{titulo}**")
                    
                    # Informações da query
                    info_text = f"{query['timestamp_str']} • Tabela: {query['tabela']} • {query['campos_count']} campos"
                    if query.get('editada', False):
                        info_text += " • 🟢 Editada"
                    st.caption(info_text)
                    
                    # Botões de ação
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 4])
                    
                    with col_btn1:
                        if st.button("📋 Copiar", key=f"copy_{idx_real}", help="Copiar SQL para área de transferência"):
                            # Mostra a SQL em um code block temporário para copiar
                            st.session_state[f"show_copy_{idx_real}"] = True
                            st.session_state[f"show_sql_{idx_real}"] = True
                    
                    with col_btn2:
                        if st.button("👁️ Ver SQL", key=f"view_{idx_real}"):
                            st.session_state[f"show_sql_{idx_real}"] = not st.session_state.get(f"show_sql_{idx_real}", False)
                    
                    with col_btn3:
                        st.download_button(
                            "💾 Baixar",
                            query["sql"],
                            file_name=f"query_{query['tabela']}_{query['timestamp'].strftime('%Y%m%d_%H%M%S')}.sql",
                            key=f"download_{idx_real}"
                        )
                    
                    with col_btn4:
                        emoji_fav = "★" if query["favorito"] else "☆"
                        if st.button(f"{emoji_fav} Favoritar", key=f"fav_{idx_real}"):
                            toggle_favorito(idx_real)
                            st.rerun()
                    
                    # Mostra SQL se solicitado
                    if st.session_state.get(f"show_sql_{idx_real}", False):
                        st.code(query["sql"], language="sql", line_numbers=True)
                        if st.session_state.get(f"show_copy_{idx_real}", False):
                            st.success("✓ SQL exibida acima! Use o botão 📋 no canto superior direito do código para copiar.")
                            st.session_state[f"show_copy_{idx_real}"] = False
                    
                    st.divider()  # Separador visual entre queries
        
        st.markdown("---")
        st.markdown("""
        <div class="info-box">
            💡 <strong>Dicas:</strong><br>
            • Clique em <strong>📋 Copiar</strong> para exibir a SQL e usar o botão de copiar nativo<br>
            • Use <strong>☆/★ Favoritar</strong> para marcar queries importantes (favoritas não são removidas automaticamente)<br>
            • Queries editadas são marcadas com <strong>✏️</strong> e salvam automaticamente a versão final<br>
            • Queries são salvas automaticamente em arquivos na pasta <code>historico_queries</code><br>
            • O histórico mantém até 10 queries não-favoritas na sessão atual
        </div>
        """, unsafe_allow_html=True)

# --- RODAPÉ ---
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: gray;'>Desenvolvido por Claudio Ximenes | <a href='mailto:csenemix@gmail.com' style='color: #ff4b4b; text-decoration: none;'>Suporte</a></div>", unsafe_allow_html=True)
