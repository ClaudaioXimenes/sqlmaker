import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="SQL Maker RM - Totvs", layout="wide", page_icon="🚀")

# --- FUNÇÃO DE CARREGAMENTO (Com Cache para ser rápido) ---
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
    # 1. Seleção do Sistema
    df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
    df_sistemas["LABEL"] = df_sistemas["CODSISTEMA"].astype(str) + " - " + df_sistemas["DESCRICAO"]
    
    sistema_sel = st.sidebar.selectbox("Selecione o Sistema", df_sistemas["LABEL"], key=f"sis_{seed}")
    cod_sistema = df_sistemas[df_sistemas["LABEL"] == sistema_sel]["CODSISTEMA"].values[0]

    # 2. Seleção da Tabela Pai
    # Filtra tabelas que começam com o código do sistema (padrão RM)
    tab_disponiveis = df_campos[df_campos["TABELA"].fillna("").str.startswith(str(cod_sistema))]["TABELA"].unique()
    tabela_pai = st.selectbox("Selecione a Tabela Pai", sorted(tab_disponiveis), key=f"pai_{seed}")

    # 3. Seleção de Colunas
    # Pega a segunda coluna da planilha CAMPOS (Nome do Campo)
    col_nome_campo = df_campos.columns[1]
    todos_campos = df_campos[df_campos["TABELA"] == tabela_pai][col_nome_campo].dropna().tolist()
    
    campos_sel = st.multiselect(f"Colunas de {tabela_pai}", options=todos_campos, 
                                default=todos_campos[:8] if len(todos_campos) > 8 else todos_campos,
                                key=f"cols_{seed}")

    # 4. Seleção de Joins (Tabelas Filhas)
    filhas_sug = df_relacoes[df_relacoes["MASTERTABLE"] == tabela_pai]["CHILDTABLE"].unique()
    tabelas_filhas = st.multiselect("Adicionar Joins (Tabelas Filhas)", filhas_sug, key=f"fil_{seed}")

    # 5. Filtro WHERE
    filtro_where = st.text_area("Filtro WHERE (Opcional)", placeholder="Ex: CODCOLIGADA = 1 AND ATIVO = 1", key=f"w_{seed}")

    st.markdown("---")

    # --- GERAÇÃO DO SCRIPT ---
    if st.button("✨ Gerar Script SQL", use_container_width=True):
        if not campos_sel:
            st.warning("Selecione ao menos uma coluna!")
        else:
            # SELECT e FROM
            script = f"-- Script Gerado para {tabela_pai}\nSELECT\n"
            script += ",\n".join([f"  {tabela_pai}.{c}" for c in campos_sel])
            script += f"\nFROM {tabela_pai} (NOLOCK)"
            
            # JOINs
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

            # WHERE
            if filtro_where.strip():
                script += f"\nWHERE {filtro_where.strip()}"

            # Exibição
            st.code(script, language="sql")
            
            # Botão de Download
            st.download_button(
                label="📥 Baixar arquivo .sql",
                data=script,
                file_name=f"query_{tabela_pai}.sql",
                mime="text/plain"
            )
            st.success("Script gerado com sucesso!")

else:
    st.error("Verifique se as planilhas CAMPOS.xlsx, SISTEMAS.xlsx e RELACIONAMENTOS.xlsx estão no repositório.")

# --- RODAPÉ PERSONALIZADO ---
st.markdown("---")
email_suporte = "csenemix@gmail.com"
assunto = "Feedback - SQL Maker RM"
link_email = f"mailto:{email_suporte}?subject={assunto}"

st.markdown(
    f"""
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
        <p>Desenvolvido por <strong>Claudio Ximenes Pereira</strong></p>
        <p>Dúvidas ou sugestões? envie um email para {email_suporte}</p> 
           <a href='{link_email}' style='color: #ff4b4b; text-decoration: none;'>
              📧 Clique aqui para enviar um e-mail
           </a>
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)

