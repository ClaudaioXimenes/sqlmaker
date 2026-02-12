import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="SQL Maker RM - Totvs", layout="wide", page_icon="🚀")

# --- FUNÇÃO DE CARREGAMENTO (Com Cache) ---
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

# Botão de Reset na Barra Lateral
if st.sidebar.button("➕ Iniciar Novo Script"):
    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0
    st.session_state.reset_counter += 1
    st.rerun()

seed = st.session_state.get("reset_counter", 0)

df_campos, df_sistemas, df_relacoes = load_data()

if df_campos is not None:
    # Normalização de Colunas
    df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
    df_campos.columns = df_campos.columns.str.strip().str.upper()
    df_relacoes.columns = df_relacoes.columns.str.strip().str.upper()

    # 1. Seleção do Sistema
    df_sistemas["LABEL"] = df_sistemas["CODSISTEMA"].astype(str) + " - " + df_sistemas["DESCRICAO"]
    sistema_sel = st.sidebar.selectbox("Selecione o Sistema", df_sistemas["LABEL"], key=f"sis_{seed}")
    cod_sistema = df_sistemas[df_sistemas["LABEL"] == sistema_sel]["CODSISTEMA"].values[0]

    # 2. Seleção da Tabela Pai
    tab_disponiveis = df_campos[df_campos["TABELA"].fillna("").str.startswith(str(cod_sistema))]["TABELA"].unique()
    tabela_pai = st.selectbox("Selecione a Tabela Pai", sorted(tab_disponiveis), key=f"pai_{seed}")

    # 3. Seleção de Colunas da Tabela Pai
    col_nome_campo = df_campos.columns[1] 
    todos_campos_pai = df_campos[df_campos["TABELA"] == tabela_pai][col_nome_campo].dropna().tolist()
    
    campos_pai_sel = st.multiselect(
        f"Colunas de {tabela_pai}", 
        options=todos_campos_pai, 
        default=todos_campos_pai[:8] if len(todos_campos_pai) > 8 else todos_campos_pai,
        key=f"cols_pai_{seed}"
    )

    # 4. Seleção de Tabelas Filhas (Joins)
    filhas_sug = df_relacoes[df_relacoes["MASTERTABLE"] == tabela_pai]["CHILDTABLE"].unique()
    tabelas_filhas = st.multiselect("Adicionar Joins (Tabelas Filhas)", filhas_sug, key=f"fil_{seed}")

    # --- NOVO: SELEÇÃO DINÂMICA DE CAMPOS DAS FILHAS ---
    campos_por_filha = {}
    if tabelas_filhas:
        st.write("### Seleção de campos para Joins")
        for filha in tabelas_filhas:
            campos_da_filha = df_campos[df_campos["TABELA"] == filha][col_nome_campo].dropna().tolist()
            sel = st.multiselect(
                f"Escolha colunas de: {filha}", 
                options=campos_da_filha,
                key=f"cols_{filha}_{seed}"
            )
            campos_por_filha[filha] = sel

    # 5. Filtro WHERE
    st.write("---")
    filtro_where = st.text_area("Filtro WHERE (Opcional)", placeholder="Ex: CODCOLIGADA = 1 AND ATIVO = 1", key=f"w_{seed}")

    # --- GERAÇÃO DO SCRIPT ---
    if st.button("✨ Gerar Script SQL", use_container_width=True):
        if not campos_pai_sel and not any(campos_por_filha.values()):
            st.warning("Selecione ao menos uma coluna de qualquer tabela!")
        else:
            # Montando a lista de colunas do SELECT
            colunas_sql = [f"  {tabela_pai}.{c}" for c in campos_pai_sel]
            
            # Adiciona colunas das filhas no SELECT
            for filha, colunas in campos_por_filha.items():
                for c in colunas:
                    colunas_sql.append(f"  {filha}.{c}")

            # Script Base
            script = f"-- Script Gerado para {tabela_pai}\nSELECT\n"
            script += ",\n".join(colunas_sql)
            script += f"\nFROM {tabela_pai} (NOLOCK)"
            
            # Adicionando os JOINs
            for filha in tabelas_filhas:
                rel_filtrada = df_relacoes[(df_relacoes["MASTERTABLE"] == tabela_pai) & (df_relacoes["CHILDTABLE"] == filha)]
                condicoes = []
                for _, r in rel_filtrada.iterrows():
                    cp_list = str(r["MASTERFIELD"]).split(",")
                    cf_list = str(r["CHILDFIELD"]).split(",")
                    for cp, cf in zip(cp_list, cf_list):
                        condicoes.append(f"{tabela_pai}.{cp.strip()} = {filha}.{cf.strip()}")
                
                if condicoes:
                    script += f"\nINNER JOIN {filha} (NOLOCK) ON\n  " + " AND\n  ".join(condicoes)

            # Cláusula WHERE final
            if filtro_where.strip():
                script += f"\nWHERE {filtro_where.strip()}"

            # Resultado
            st.code(script, language="sql")
            st.download_button("📥 Baixar arquivo .sql", script, file_name=f"query_{tabela_pai}.sql")
            st.success("Script gerado com sucesso!")

# --- RODAPÉ ---
st.markdown("---")
email_suporte = "csenemix@gmail.com"
link_email = f"mailto:{email_suporte}?subject=Feedback%20SQL%20Maker"

st.markdown(
    f"""
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
        <p>Desenvolvido por <strong>CarlosClaudio Ximenes Pereira</strong></p>
        <p><a href='{link_email}' style='color: #ff4b4b; text-decoration: none;'>📧 Clique aqui para enviar um e-mail</a></p>
    </div>
    """, 
    unsafe_allow_html=True
)
