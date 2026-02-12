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

# --- CABEÇALHO ---
st.title("🚀 SQL Maker - Assistente de Relatórios RM")
st.markdown("---")

# Criando as Abas
tab_tutorial, tab_gerador = st.tabs(["📖 Como Usar", "🛠️ Criar minha Sentença"])

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
    st.link_button("🤖 Falar com o Assistente no Telegram", "https://t.me/sqlmaker_bot", use_container_width=True)

# --- ABA 2: GERADOR ---
with tab_gerador:
    if df_campos is not None:
        if st.sidebar.button("➕ Limpar e Iniciar Novo"):
            if "reset_counter" not in st.session_state:
                st.session_state.reset_counter = 0
            st.session_state.reset_counter += 1
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
        tabelas_globais = df_campos[df_campos["TABELA"].fillna("").str.startswith("G")]["TABELA"].unique().tolist()
        filhas_finais = sorted(list(set(filhas_relacao + tabelas_globais)))
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
        filtro_where = st.text_area("Filtros Adicionais (Ex: CODCOLIGADA = 1)", placeholder="Digite seus filtros...", key=f"w_{seed}")

        st.markdown("---")

        # --- AQUI ESTÁ A LÓGICA QUE FALTAVA ---
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

                st.success("Tudo pronto! Veja sua sentença abaixo:")
                st.code(script, language="sql")
                st.download_button("📥 Baixar .sql", script, file_name=f"sentenca_{tabela_pai}.sql")

# --- RODAPÉ ---
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: gray;'>Desenvolvido por Claudio Ximnenes | <a href='mailto:csenemix@gmail.com' style='color: #ff4b4b; text-decoration: none;'>Suporte</a></div>", unsafe_allow_html=True)


