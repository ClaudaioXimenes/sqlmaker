import streamlit as st
import pandas as pd
import os

# 1. Configuração visual (Sempre a primeira linha)
st.set_page_config(page_title="SQL Maker RM", layout="wide")

# --- FUNÇÃO DE CARREGAMENTO ---
@st.cache_data
def load_data():
    # Carrega as planilhas
    df_campos = pd.read_excel("CAMPOS.xlsx")
    df_sistemas = pd.read_excel("SISTEMAS.xlsx")
    df_relacoes = pd.read_excel("RELACIONAMENTOS.xlsx")
    return df_campos, df_sistemas, df_relacoes

# --- APLICAÇÃO PRINCIPAL ---
# Removida a autenticação manual para usar a do Streamlit Cloud
st.title("🚀 SQL Maker - Gerador de Scripts RM")

# Botão para Iniciar Novo Script na barra lateral
if st.sidebar.button("➕ Iniciar Novo Script"):
    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0
    st.session_state.reset_counter += 1
    st.rerun()

seed = st.session_state.get("reset_counter", 0)

try:
    df_campos, df_sistemas, df_relacoes = load_data()

    # Normalizar nomes de colunas para evitar erros de case
    df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
    df_campos.columns = df_campos.columns.str.strip().str.upper()
    df_relacoes.columns = df_relacoes.columns.str.strip().str.upper()

    # Criar label amigável para o sistema
    df_sistemas["SISTEMA_LABEL"] = (
        df_sistemas["CODSISTEMA"].astype(str).str.strip()
        + " - "
        + df_sistemas["DESCRICAO"].astype(str).str.strip()
    )

    # 1. Seleção do Sistema
    sistema_label = st.sidebar.selectbox(
        "Selecione o Sistema",
        df_sistemas["SISTEMA_LABEL"], key=f"sistema_{seed}"
    )

    prefixo = df_sistemas[df_sistemas["SISTEMA_LABEL"] == sistema_label]["CODSISTEMA"].values[0]

    # 2. Seleção da Tabela Pai
    col_tab_campos = "TABELA"
    tabelas_disponiveis = df_campos[
        df_campos[col_tab_campos].fillna("").str.startswith(prefixo)
    ][col_tab_campos].unique()

    tabela_pai = st.selectbox(
        "Selecione a Tabela Pai",
        sorted(tabelas_disponiveis), key=f"pai_{seed}"
    )

    # 3. Seleção de Colunas da Tabela Pai
    col_nome_campo = df_campos.columns[1] 
    todos_campos_pai = df_campos[df_campos[col_tab_campos] == tabela_pai][col_nome_campo].tolist()

    campos_selecionados = st.multiselect(
        f"Selecione as colunas da {tabela_pai}",
        options=todos_campos_pai,
        default=todos_campos_pai[:10] if len(todos_campos_pai) > 10 else todos_campos_pai,
        key=f"campos_pai_{seed}"
    )

    # 4. Seleção de Tabelas Filhas (Joins)
    col_rel_pai = "MASTERTABLE"
    col_rel_filha = "CHILDTABLE"
    
    filhas_sugeridas = df_relacoes[df_relacoes[col_rel_pai] == tabela_pai][col_rel_filha].unique()
    
    tabelas_filhas = st.multiselect(
        "Selecione as Tabelas Filhas (Joins)", 
        filhas_sugeridas, 
        key=f"filhas_{seed}"
    )

    # 5. Campo de Filtro WHERE
    filtro_where = st.text_area(
        "Filtros adicionais (Opcional)", 
        placeholder="Ex: CODCOLIGADA = 1 AND CHAPA = '00001'",
        key=f"where_{seed}"
    )

    # --- GERAÇÃO DO SCRIPT ---
    if st.button("Gerar Script SQL"):
        st.divider()
        
        if not campos_selecionados:
            st.warning("⚠️ Selecione pelo menos uma coluna.")
        else:
            # Inicia o SELECT
            script = f"-- Script Gerado para {tabela_pai}\nSELECT\n"
            script += ",\n".join([f"  {tabela_pai}.{c}" for c in campos_selecionados])
            script += f"\nFROM {tabela_pai} (NOLOCK)"
            
            # Adiciona os JOINs
            for filha in tabelas_filhas:
                relacoes = df_relacoes[
                    (df_relacoes["MASTERTABLE"] == tabela_pai) &
                    (df_relacoes["CHILDTABLE"] == filha)
                ]
                join_conditions = []
                for _, rel in relacoes.iterrows():
                    campos_pai_rel = str(rel["MASTERFIELD"]).split(",")
                    campos_filha_rel = str(rel["CHILDFIELD"]).split(",")
                    for cp, cf in zip(campos_pai_rel, campos_filha_rel):
                        join_conditions.append(
                            f"{tabela_pai}.{cp.strip()} = {filha}.{cf.strip()}"
                        )
                
                if join_conditions:
                    join_sql = " AND\n  ".join(join_conditions)
                    script += f"\nINNER JOIN {filha} (NOLOCK) ON\n  {join_sql}"
            
            # A CORREÇÃO: WHERE fora do loop das filhas
            if filtro_where.strip():
                script += f"\nWHERE {filtro_where.strip()}"
                
            # Exibe o código final
            st.code(script, language="sql")
            st.success("Cópia e cola no seu editor de SQL e faça os ajustes finais!")

except Exception as e:
    st.error(f"Erro ao processar a aplicação: {e}")
