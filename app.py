import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="SQL Maker RM - Totvs", layout="wide", page_icon="🚀")

# --- FUNÇÃO DE CARREGAMENTO ---
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

# --- INTERFACE PRINCIPAL ---
st.title("🚀 SQL Maker - Gerador de Scripts RM")
st.markdown("---")

# Botão de Reset
if st.sidebar.button("➕ Iniciar Novo Script"):
    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0
    st.session_state.reset_counter += 1
    st.rerun()

seed = st.session_state.get("reset_counter", 0)
df_campos, df_sistemas, df_relacoes = load_data()

if df_campos is not None:
    df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
    df_campos.columns = df_campos.columns.str.strip().str.upper()
    df_relacoes.columns = df_relacoes.columns.str.strip().str.upper()

    # 1. Seleção do Sistema e Tabela Pai
    df_sistemas["LABEL"] = df_sistemas["CODSISTEMA"].astype(str) + " - " + df_sistemas["DESCRICAO"]
    sistema_sel = st.sidebar.selectbox("Selecione o Sistema", df_sistemas["LABEL"], key=f"sis_{seed}")
    cod_sistema = df_sistemas[df_sistemas["LABEL"] == sistema_sel]["CODSISTEMA"].values[0]

    tab_disponiveis = df_campos[df_campos["TABELA"].fillna("").str.startswith(str(cod_sistema))]["TABELA"].unique()
    tabela_pai = st.selectbox("Selecione a Tabela Pai", sorted(tab_disponiveis), key=f"pai_{seed}")

    col_nome_campo = df_campos.columns[1]
    todos_campos_pai = df_campos[df_campos["TABELA"] == tabela_pai][col_nome_campo].dropna().tolist()
    
    campos_pai_sel = st.multiselect(f"Colunas de {tabela_pai}", options=todos_campos_pai, key=f"cols_pai_{seed}")

    # 2. Joins e Campos das Filhas
    filhas_sug = df_relacoes[df_relacoes["MASTERTABLE"] == tabela_pai]["CHILDTABLE"].unique()
    tabelas_filhas = st.multiselect("Adicionar Joins (Tabelas Filhas)", filhas_sug, key=f"fil_{seed}")

    campos_por_filha = {}
    if tabelas_filhas:
        for filha in tabelas_filhas:
            campos_da_filha = df_campos[df_campos["TABELA"] == filha][col_nome_campo].dropna().tolist()
            campos_por_filha[filha] = st.multiselect(f"Colunas de: {filha}", options=campos_da_filha, key=f"cols_{filha}_{seed}")

    # --- NOVO: SEÇÃO DE AGRUPAMENTO (CAMINHO A) ---
    st.markdown("### 📊 Agrupamentos e Métricas (Opcional)")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        op_agregacao = st.selectbox("Operação", ["NENHUMA", "SOMA (SUM)", "CONTAGEM (COUNT)", "MÉDIA (AVG)", "MÁXIMO (MAX)", "MÍNIMO (MIN)"], key=f"op_{seed}")
    
    campo_metrica = None
    if op_agregacao != "NENHUMA":
        with col2:
            # Junta todos os campos selecionados acima para escolher qual será calculado
            todos_escolhidos = campos_pai_sel + [c for sub in campos_por_filha.values() for c in sub]
            campo_metrica = st.selectbox("Calcular sobre qual campo?", [""] + todos_escolhidos, key=f"met_{seed}")
        with col3:
            st.info("💡 Campos não calculados serão agrupados automaticamente (GROUP BY).")

    # 3. Filtro WHERE
    filtro_where = st.text_area("Filtro WHERE (Opcional)", placeholder="Ex: CODCOLIGADA = 1", key=f"w_{seed}")

    # --- GERAÇÃO DO SCRIPT ---
    if st.button("✨ Gerar Script SQL", use_container_width=True):
        if not campos_pai_sel and not any(campos_por_filha.values()):
            st.warning("Selecione ao menos uma coluna!")
        else:
            # Mapeamento de colunas com seus aliases (Tabela.Coluna)
            colunas_select = [f"{tabela_pai}.{c}" for c in campos_pai_sel]
            for filha, cols in campos_por_filha.items():
                for c in cols:
                    colunas_select.append(f"{filha}.{c}")

            # Lógica de Agrupamento
            if op_agregacao != "NENHUMA" and campo_metrica:
                map_op = {"SOMA (SUM)": "SUM", "CONTAGEM (COUNT)": "COUNT", "MÉDIA (AVG)": "AVG", "MÁXIMO (MAX)": "MAX", "MÍNIMO (MIN)": "MIN"}
                func = map_op[op_agregacao]
                
                # Identifica qual a tabela do campo de métrica (Pai ou Filha?)
                prefixo_metrica = ""
                if campo_metrica in campos_pai_sel:
                    prefixo_metrica = tabela_pai
                else:
                    for f, cs in campos_por_filha.items():
                        if campo_metrica in cs:
                            prefixo_metrica = f
                            break
                
                campo_final_metrica = f"{func}({prefixo_metrica}.{campo_metrica}) AS {func}_{campo_metrica}"
                
                # Campos do SELECT (Todos exceto o que vai ser calculado)
                campos_group_by = [c for c in colunas_select if not c.endswith(f".{campo_metrica}")]
                select_final = ",\n  ".join(campos_group_by + [campo_final_metrica])
                group_by_sql = f"\nGROUP BY\n  " + ",\n  ".join(campos_group_by)
            else:
                select_final = ",\n  ".join(colunas_select)
                group_by_sql = ""

            # Montagem Final
            script = f"SELECT\n  {select_final}\nFROM {tabela_pai} (NOLOCK)"
            
            for filha in tabelas_filhas:
                rel = df_relacoes[(df_relacoes["MASTERTABLE"] == tabela_pai) & (df_relacoes["CHILDTABLE"] == filha)]
                conds = []
                for _, r in rel.iterrows():
                    cp_l, cf_l = str(r["MASTERFIELD"]).split(","), str(r["CHILDFIELD"]).split(",")
                    for cp, cf in zip(cp_l, cf_l):
                        conds.append(f"{tabela_pai}.{cp.strip()} = {filha}.{cf.strip()}")
                if conds:
                    script += f"\nINNER JOIN {filha} (NOLOCK) ON\n  " + " AND\n  ".join(conds)

            if filtro_where.strip():
                script += f"\nWHERE {filtro_where.strip()}"
            
            script += group_by_sql

            st.code(script, language="sql")
            st.download_button("📥 Baixar .sql", script, file_name=f"query_agrupada_{tabela_pai}.sql")

# --- RODAPÉ ---
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: gray;'>Desenvolvido por Claudio Ximenes | <a href='mailto:csenemix@gmail.com' style='color: #ff4b4b;'>Suporte</a></div>", unsafe_allow_html=True)
