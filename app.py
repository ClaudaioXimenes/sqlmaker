import streamlit as st
import pandas as pd
import os

# Configuração visual
st.set_page_config(page_title="SQL Maker RM", layout="wide")

# --- FUNÇÃO DE CARREGAMENTO ---
@st.cache_data
def load_data():
    # Carrega as planilhas (ajuste o nome das colunas se necessário)
    df_campos = pd.read_excel("CAMPOS.xlsx")
    df_sistemas = pd.read_excel("SISTEMAS.xlsx")
    df_relacoes = pd.read_excel("RELACIONAMENTOS.xlsx")
    return df_campos, df_sistemas, df_relacoes

# Interface de Login (Simplificada para o protótipo)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 SQL Maker - Login")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if user == "admin" and pwd == "rm123": # Altere sua senha aqui
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
else:
    # --- APLICAÇÃO PRINCIPAL ---
    st.title("🚀 SQL Maker - Gerador de Scripts RM")
    # Botão para Iniciar Novo Script (Limpar Tudo)
    
    if st.sidebar.button("➕ Iniciar Novo Script"):
        # Incrementamos um contador para resetar os widgets que possuem 'key'
        if "reset_counter" not in st.session_state:
            st.session_state.reset_counter = 0
        st.session_state.reset_counter += 1
        st.rerun()

    # Definimos uma semente para as chaves baseada no contador de reset
    seed = st.session_state.get("reset_counter", 0)
    
    try:
        df_campos, df_sistemas, df_relacoes = load_data()

            # Normalizar nomes de colunas
        df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
        df_campos.columns = df_campos.columns.str.strip().str.upper()
        df_relacoes.columns = df_relacoes.columns.str.strip().str.upper()

        # Criar label amigável
        df_sistemas["SISTEMA_LABEL"] = (
            df_sistemas["CODSISTEMA"].astype(str).str.strip()
            + " - "
            + df_sistemas["DESCRICAO"].astype(str).str.strip()
        )

        # Selectbox com label amigável
        sistema_label = st.sidebar.selectbox(
            "Selecione o Sistema",
            df_sistemas["SISTEMA_LABEL"],key=f"sistema_{seed}"
        )

        # Pegar apenas o código do sistema selecionado
        prefixo = df_sistemas[
            df_sistemas["SISTEMA_LABEL"] == sistema_label
        ]["CODSISTEMA"].values[0]

        # Filtrar Tabelas Pai pelo prefixo
        col_tab_campos = "TABELA"

        tabelas_disponiveis = df_campos[
            df_campos[col_tab_campos].fillna("").str.startswith(prefixo)
        ][col_tab_campos].unique()

        tabela_pai = st.selectbox(
            "Selecione a Tabela Pai",
            sorted(tabelas_disponiveis),key=f"pai_{seed}"
        )

        # --- NOVA PARTE: SELEÇÃO DE COLUNAS ---
        # Filtra os campos da tabela pai selecionada
        # Note que usei a coluna de índice 1 (como no seu código original do script)
        col_nome_campo = df_campos.columns[1] 
        todos_campos_pai = df_campos[df_campos[col_tab_campos] == tabela_pai][col_nome_campo].tolist()

        campos_selecionados = st.multiselect(
            f"Selecione as colunas da {tabela_pai}",
            options=todos_campos_pai,
            default=todos_campos_pai[:10] if len(todos_campos_pai) > 10 else todos_campos_pai,
            key=f"campos_pai_{seed}"
        )
        # --------------------------------------

        # 3. Sugestão Automática de Tabelas Filhas... (continua o código)

        df_sistemas["sistema_label"] = (
                    df_sistemas["CODSISTEMA"].astype(str).str.strip()+ " - "+ df_sistemas["DESCRICAO"].astype(str).str.strip()
                    ) 

            # Selectbox com label amigável        

        # 3. Sugestão Automática de Tabelas Filhas (Vindo da Planilha RELACIONAMENTOS)
        # Supondo colunas: 'TABELA_PAI' e 'TABELA_FILHA'
        col_rel_pai = "MASTERTABLE" # <-- AJUSTE COM O NOME NA RELACIONAMENTOS.xlsx
        col_rel_filha = "CHILDTABLE" # <-- AJUSTE COM O NOME NA RELACIONAMENTOS.xlsx # "TABFILHA" # <-- AJUSTE COM O NOME NA RELACIONAMENTOS.xlsx
        
        filhas_sugeridas = df_relacoes[df_relacoes[col_rel_pai] == tabela_pai][col_rel_filha].unique()
        
        tabelas_filhas = st.multiselect("Selecione as Tabelas Filhas (Joins)", filhas_sugeridas,key=f"filhas_{seed}")

        filtro_where = st.text_area(
            "Filtros adicionais (Opcional)", 
            placeholder="Ex: TABELA.CAMPO = 1 [PFUNC.CODCOLIGADA=1 AND PFUNC.NOME LIKE %SILVA%]",
            key=f"where_{seed}",
            help="Digite as condições. O sistema adicionará o 'WHERE' automaticamente."
        )

        # 4. Geração do Script

                
        if st.button("Gerar Script SQL"):
            st.divider()
            
            if not campos_selecionados:
                st.warning("⚠️ Selecione pelo menos uma coluna.")
            else:
                # 1. Inicia o script com as colunas que você selecionou no Multiselect
                script = f"-- Script Gerado para {tabela_pai}\nSELECT\n"
                script += ",\n".join([f"  {tabela_pai}.{c}" for c in campos_selecionados])
                script += f"\nFROM {tabela_pai} (NOLOCK)"
                
                # 2. Montando os JOINs (Sua lógica de iteração está correta)
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
                    
            if filtro_where.strip():
                script += f"\nWHERE {filtro_where.strip()}"
                # ----------------------------------
                
            # 3. Exibe o resultado final
            st.code(script, language="sql")
            st.success("Cópia e cola no seu editor de SQL e faça os ajustes finais!")

    except Exception as e:
        st.error(f"Erro ao ler planilhas: {e}")
        st.info("Dica: Verifique se os nomes das colunas no código batem com os das suas planilhas.")

    if st.sidebar.button("Sair"):
        st.session_state.authenticated = False
        st.rerun()