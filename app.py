import streamlit as st
import pandas as pd

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

# --- CABEÇALHO ---
st.title("🚀 SQL Maker - Assistente de Relatórios RM")
st.markdown("---")

# Chama a função da barra lateral
adicionar_sidebar_linkedin()

# Carregamento dos dados
df_campos, df_sistemas, df_relacoes = load_data()

# Criando as Abas
tab_tutorial, tab_gerador = st.tabs(["📖 Como Usar", "🛠️ Criar minha Sentença"])

# --- ABA 1: TUTORIAL ---
with tab_tutorial:
    st.header("Seja bem-vindo!")
    st.markdown("""
    Esta ferramenta permite que você extraia informações do RM de forma visual.
    
    ### 📝 O Passo a Passo:
    1. **Módulo:** Escolha o sistema.
    2. **Tabela:** Escolha o assunto.
    3. **Colunas:** Marque o que você quer ver.
    4. **Joins:** Busque dados em outras tabelas.
    5. **Cálculos:** Some ou conte registros.
    6. **Filtros:** Refine seu resultado.
    """)
    st.success("Tudo pronto? Clique na aba **'Criar minha Sentença'**!")
    st.markdown("---")
    st.markdown("### 🤝 Comunidade e Suporte")
    st.link_button("🤖 Falar com o Assistente no Telegram", "https://t.me/+HC1B2Grb0UdhNzlh", use_container_width=True)

# --- ABA 2: GERADOR ---
with tab_gerador:
    if df_campos is not None:
        if st.sidebar.button("➕ Novo Script"):
            if "reset_counter" not in st.session_state:
                st.session_state.reset_counter = 0
            st.session_state.reset_counter += 1
            st.rerun()

        seed = st.session_state.get("reset_counter", 0)

        # Normalização
        df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
        df_campos.columns = df_campos.columns.str.strip().str.upper()
        df_relacoes.columns = df_relacoes.columns.str.strip().str.upper()

        # Interface do Gerador
        df_sistemas["LABEL"] = df_sistemas["CODSISTEMA"].astype(str) + " - " + df_sistemas["DESCRICAO"]
        sistema_sel = st.selectbox("1. Qual o Módulo do RM?", df_sistemas["LABEL"], key=f"sis_{seed}")
        cod_sistema = str(df_sistemas[df_sistemas["LABEL"] == sistema_sel]["CODSISTEMA"].values[0])

        tab_disponiveis = df_campos[df_campos["TABELA"].fillna("").str.startswith(cod_sistema)]["TABELA"].unique()
        tabela_pai = st.selectbox("2. Escolha a Tabela Principal", sorted(tab_disponiveis), key=f"pai_{seed}")

        col_nome_campo = df_campos.columns[1]
        todos_campos_pai = df_campos[df_campos["TABELA"] == tabela_pai][col_nome_campo].dropna().tolist()
        campos_pai_sel = st.multiselect(f"Campos de {tabela_pai}:", options=todos_campos_pai, key=f"cols_pai_{seed}")

        # Joins
        filhas_relacao = df_relacoes[df_relacoes["MASTERTABLE"] == tabela_pai]["CHILDTABLE"].unique().tolist()
        filhas_finais = sorted([f for f in filhas_relacao if f != tabela_pai])
        tabelas_filhas = st.multiselect("Deseja fazer Joins?", filhas_finais, key=f"fil_{seed}")

        campos_por_filha = {}
        for filha in tabelas_filhas:
            campos_da_filha = df_campos[df_campos["TABELA"] == filha][col_nome_campo].dropna().tolist()
            campos_por_filha[filha] = st.multiselect(f"Colunas de {filha}:", options=campos_da_filha, key=f"cols_{filha}_{seed}")

        # Agregadores e Filtros
        st.markdown("### 📊 Cálculos e Filtros")
        op_agregacao = st.selectbox("Cálculo:", ["NENHUM", "SOMA (SUM)", "CONTAGEM (COUNT)", "MÉDIA (AVG)", "MÁXIMO (MAX)", "MÍNIMO (MIN)"], key=f"op_{seed}")
        
        campo_metrica = ""
        if op_agregacao != "NENHUM":
            todos_escolhidos = campos_pai_sel + [item for sublist in campos_por_filha.values() for item in sublist]
            campo_metrica = st.selectbox("Sobre qual coluna?", [""] + todos_escolhidos, key=f"met_{seed}")

        filtro_where = st.text_area("Filtros (Ex: CODCOLIGADA = 1)", key=f"w_{seed}")

        # Lógica de Geração SQL
        if st.button("✨ GERAR MINHA SENTENÇA SQL", use_container_width=True):
            if not campos_pai_sel and not any(campos_por_filha.values()):
                st.warning("Selecione ao menos uma coluna!")
            else:
                colunas_select = [f"{tabela_pai}.{c}" for c in campos_pai_sel]
                for filha, cols in campos_por_filha.items():
                    for c in cols:
                        colunas_select.append(f"{filha}.{c}")

                if op_agregacao != "NENHUM" and campo_metrica:
                    map_op = {"SOMA (SUM)": "SUM", "CONTAGEM (COUNT)": "COUNT", "MÉDIA (AVG)": "AVG", "MÁXIMO (MAX)": "MAX", "MÍNIMO (MIN)": "MIN"}
                    func = map_op[op_agregacao]
                    prefixo_met = tabela_pai if campo_metrica in campos_pai_sel else next((f for f, cs in campos_por_filha.items() if campo_metrica in cs), "")
                    
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
                        conds = [f"{tabela_pai}.{str(r['MASTERFIELD']).strip()} = {filha}.{str(r['CHILDFIELD']).strip()}" for _, r in rel.iterrows()]
                        script += f"\nINNER JOIN {filha} (NOLOCK) ON " + " AND ".join(conds)
                    else:
                        script += f"\nINNER JOIN {filha} (NOLOCK) ON {tabela_pai}.ID = {filha}.ID"

                if filtro_where.strip():
                    script += f"\nWHERE {filtro_where.strip()}"
                script += group_by_sql

                st.success("Sentença Gerada!")
                st.code(script, language="sql")
                st.download_button("📥 Baixar .sql", script, file_name=f"sentenca_{tabela_pai}.sql")

# --- RODAPÉ ---
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: gray;'>Desenvolvido por <a href='{LINKEDIN_URL}' style='color: #0077b5; text-decoration: none; font-weight: bold;'>Claudio Ximenes</a> | <a href='mailto:csenemix@gmail.com' style='color: #ff4b4b; text-decoration: none;'>Suporte</a></div>", unsafe_allow_html=True)
