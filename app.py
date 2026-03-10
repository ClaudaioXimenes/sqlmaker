# =============================================================================
#  RM Suite — Ferramentas integradas TOTVS RM
#  Versão  : 2.1.0
#  Autor   : Claudio Ximenes  <csenemix@gmail.com>
#  LinkedIn: https://www.linkedin.com/in/claudio-ximenes-pereira-bb090036/
#
# -----------------------------------------------------------------------------
#  CHANGELOG
# -----------------------------------------------------------------------------
#  v2.1.0  - Pareto de Concentracao da Folha com buckets adaptativos,
#             tabela de alerta com exportacao CSV e slider de faixas.
#  v2.0.1  - Correcoes de compatibilidade Plotly (titlefont -> title=dict).
#  v2.0.0  - Unificacao do SQL Maker e Dashboard Ficha Financeira em app unico
#             com navegacao lateral (RM Suite). Tela Home com cards de acesso.
#  v1.x    - Apps separados: app_dashboard.py e app_sqlmaker.py.
# -----------------------------------------------------------------------------
#
#  DEPENDENCIAS (pip install):
#    streamlit pygwalker pandas plotly zeep requests openpyxl
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import random
import re
import requests
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
from pygwalker.api.streamlit import StreamlitRenderer
from zeep import Client
from zeep.transports import Transport

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="RM Suite — TOTVS",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS GLOBAL
# ============================================================
st.markdown("""
<style>
/* Sidebar branding */
.sidebar-brand {
    text-align: center;
    padding: 18px 10px 10px 10px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 12px;
    margin-bottom: 16px;
}
.sidebar-brand h1 {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    margin: 0;
    letter-spacing: 1px;
}
.sidebar-brand p {
    font-size: 12px;
    color: #8892b0;
    margin: 4px 0 0 0;
}
.sidebar-badge {
    display: inline-block;
    background: linear-gradient(90deg, #667eea, #764ba2);
    color: white;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 8px;
    border-radius: 10px;
    margin-top: 4px;
}

/* Oculta o menu padrão do Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Cards de métricas */
div[data-testid="metric-container"] {
    background: #1e1e2e;
    border: 1px solid #2d2d44;
    border-radius: 10px;
    padding: 12px;
}

/* SQL Editor */
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
.sql-keyword { color: #569cd6; font-weight: 600; }
.sql-table   { color: #4ec9b0; }
.sql-field   { color: #9cdcfe; }
.sql-string  { color: #ce9178; }
.sql-comment { color: #6a9955; font-style: italic; }

.stTextArea textarea {
    font-family: 'Courier New', monospace !important;
    font-size: 14px !important;
    background-color: #0e1117 !important;
    color: #fafafa !important;
    border: 1px solid #3d3d4d !important;
    border-radius: 8px !important;
}

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
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONSTANTES DO DASHBOARD
# ============================================================
WSDL_SUFIXO = "/wsConsultaSQL/MEX?wsdl"
SISTEMA_WS  = "P"
SENTENCA    = "FICHA_FINANCEIRA"
LINKEDIN_URL = "https://www.linkedin.com/in/claudio-ximenes-pereira-bb090036/"

MESES = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun",
         7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}

def fmt(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ============================================================
# SESSION STATE DEFAULTS
# ============================================================
_defaults = {
    "modulo_ativo": "home",
    # Dashboard
    "df": pd.DataFrame(),
    "param_coligada": "1",
    "param_ano": 2024,
    "executar_consulta": False,
    "consultou": False,
    "conexao_ok": False,
    "pag_Nome": 0,
    "pag_Seção": 0,
    "pag_Função": 0,
    "servidor_base": "http://localhost:8051",
    "rm_usuario": "mestre",
    "rm_senha": "",
    "wsdl_url": "",
    # SQLMaker
    "historico_queries": [],
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ============================================================
# SIDEBAR — NAVEGAÇÃO
# ============================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <h1>🧩 RM Suite</h1>
        <p>Ferramentas integradas TOTVS</p>
        <span class="sidebar-badge">by Claudio Ximenes</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Navegação")

    if st.button("🏠  Início",           use_container_width=True):
        st.session_state["modulo_ativo"] = "home"
        st.rerun()
    if st.button("📊  Ficha Financeira", use_container_width=True):
        st.session_state["modulo_ativo"] = "dashboard"
        st.rerun()
    if st.button("🚀  SQL Maker",        use_container_width=True):
        st.session_state["modulo_ativo"] = "sqlmaker"
        st.rerun()

    st.markdown("---")

    # Botão Novo Script só aparece no SQLMaker
    if st.session_state["modulo_ativo"] == "sqlmaker":
        if st.button("➕ Novo Script SQL", use_container_width=True):
            if "reset_counter" not in st.session_state:
                st.session_state.reset_counter = 0
            st.session_state.reset_counter += 1
            if "sql_editada" in st.session_state:
                del st.session_state["sql_editada"]
            st.rerun()

    # Status de conexão
    if st.session_state.get("conexao_ok"):
        st.success("🔗 Conectado ao RM")
        st.caption(f"`{st.session_state.get('wsdl_url','')}`")

    st.markdown("---")
    st.markdown(
        f'<a href="{LINKEDIN_URL}" target="_blank" style="text-decoration:none;">'
        '<div style="background:#0077b5;color:white;padding:10px;border-radius:8px;'
        'text-align:center;font-weight:bold;font-size:13px;">🔗 LinkedIn</div></a>',
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='text-align:center;color:#555;font-size:11px;margin-top:8px;'>"
        "Suporte: <a href='mailto:csenemix@gmail.com' style='color:#ff4b4b;'>csenemix@gmail.com</a></div>",
        unsafe_allow_html=True
    )

# ============================================================
# ██  MÓDULO: HOME
# ============================================================
if st.session_state["modulo_ativo"] == "home":
    st.title("🧩 RM Suite")
    st.markdown("### Bem-vindo à central de ferramentas TOTVS RM")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    border: 1px solid #2d2d44; border-radius: 14px; padding: 28px; height: 280px;">
            <h2 style="color:#f39c12; margin:0;">📊 Ficha Financeira</h2>
            <p style="color:#ccc; margin-top:12px; font-size:15px;">
                Dashboard completo de folha de pagamento integrado ao Web Service RM.<br><br>
                <strong style="color:#fff;">✔</strong> Proventos x Descontos por período<br>
                <strong style="color:#fff;">✔</strong> Índice de comprometimento<br>
                <strong style="color:#fff;">✔</strong> Envelope de pagamento individual<br>
                <strong style="color:#fff;">✔</strong> Análise exploratória com PyGWalker
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📊  Abrir Ficha Financeira", use_container_width=True, type="primary"):
            st.session_state["modulo_ativo"] = "dashboard"
            st.rerun()

    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
                    border: 1px solid #2d2d44; border-radius: 14px; padding: 28px; height: 280px;">
            <h2 style="color:#667eea; margin:0;">🚀 SQL Maker</h2>
            <p style="color:#ccc; margin-top:12px; font-size:15px;">
                Assistente visual para criação de sentenças SQL do RM sem precisar digitar código.<br><br>
                <strong style="color:#fff;">✔</strong> Seleção visual de tabelas e campos<br>
                <strong style="color:#fff;">✔</strong> JOINs automáticos com relacionamentos<br>
                <strong style="color:#fff;">✔</strong> Filtros WHERE, GROUP BY e ORDER BY<br>
                <strong style="color:#fff;">✔</strong> Histórico e exportação .sql
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀  Abrir SQL Maker", use_container_width=True, type="primary"):
            st.session_state["modulo_ativo"] = "sqlmaker"
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#555; font-size:13px;">
        RM Suite v2.0 · Desenvolvido por <strong>Claudio Ximenes</strong>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# ██  MÓDULO: DASHBOARD FICHA FINANCEIRA
# ============================================================
elif st.session_state["modulo_ativo"] == "dashboard":

    # ---------- Funções do dashboard ----------
    def buscar_dados(coligada: int, ano: int) -> pd.DataFrame:
        wsdl_url   = st.session_state.get("wsdl_url")
        rm_usuario = st.session_state.get("rm_usuario")
        rm_senha   = st.session_state.get("rm_senha")
        try:
            session = requests.Session()
            session.auth = (rm_usuario, rm_senha)
            transport = Transport(session=session)
            client = Client(wsdl_url, transport=transport)
            service = client.bind("wsConsultaSQL", "RM_IwsConsultaSQL")
            parameters = f"CODCOLIGADA={coligada};ANO={ano}"
            resultado = service.RealizarConsultaSQL(
                codSentenca=SENTENCA, codColigada=0,
                codSistema=SISTEMA_WS, parameters=parameters
            )
            root = ET.fromstring(resultado)
            registros = []
            for item in root.findall("Resultado"):
                registros.append({
                    "Coligada":    item.findtext("CODCOLIGADA"),
                    "Empresa":     item.findtext("NOMEFANTASIA"),
                    "Nome":        item.findtext("NOME"),
                    "Função":      item.findtext("FUNCAO"),
                    "Seção":       item.findtext("SECAO"),
                    "Tipo Evento": item.findtext("TIPO_EVENTO"),
                    "Evento":      item.findtext("EVENTO"),
                    "Período":     item.findtext("NROPERIODO"),
                    "Mês":         int(item.findtext("MESCOMP") or 0),
                    "Ano":         int(item.findtext("ANOCOMP") or 0),
                    "Valor":       float(item.findtext("VALOR") or 0),
                    "Liquido":     float(item.findtext("VLR_PROV_DESC") or 0)
                })
            return pd.DataFrame(registros)
        except Exception as e:
            st.error(f"Erro ao buscar dados: {e}")
            return pd.DataFrame()

    def grafico_proventos_descontos_saldo(df: pd.DataFrame):
        grp = df.groupby(["Ano", "Mês", "Tipo Evento"])["Valor"].sum().reset_index()
        grp["Período"] = grp["Mês"].astype(str).str.zfill(2) + "/" + grp["Ano"].astype(str)
        pivot = grp.pivot_table(index="Período", columns="Tipo Evento", values="Valor", aggfunc="sum").fillna(0).reset_index()
        pivot = pivot.sort_values("Período")
        provento = pivot.get("Provento", pd.Series([0]*len(pivot)))
        desconto = pivot.get("Desconto", pd.Series([0]*len(pivot)))
        saldo    = provento - desconto
        fig = go.Figure()
        fig.add_trace(go.Bar(x=pivot["Período"], y=provento, name="Proventos", marker_color="#2ecc71",
            text=provento.apply(fmt), textposition="inside"))
        fig.add_trace(go.Bar(x=pivot["Período"], y=desconto, name="Descontos", marker_color="#e74c3c",
            text=desconto.apply(fmt), textposition="inside"))
        fig.add_trace(go.Scatter(x=pivot["Período"], y=saldo, name="Saldo Líquido",
            mode="lines+markers+text", line=dict(color="#f39c12", width=3), marker=dict(size=8),
            text=saldo.apply(fmt), textposition="top center", textfont=dict(color="#f39c12", size=11)))
        fig.update_layout(barmode="stack", title="📊 Proventos x Descontos por Período + Saldo Líquido",
            xaxis_title="Período", yaxis_title="Valor (R$)", height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)"), yaxis=dict(gridcolor="rgba(255,255,255,0.1)"))
        return fig

    def grafico_ranking_eventos(df: pd.DataFrame):
        grp = df.groupby(["Evento", "Tipo Evento"])["Valor"].sum().reset_index()
        grp = grp.sort_values("Valor", ascending=True).tail(10)
        colors = grp["Tipo Evento"].map({"Provento": "#2ecc71", "Desconto": "#e74c3c"}).fillna("#95a5a6")
        fig = go.Figure(go.Bar(x=grp["Valor"], y=grp["Evento"], orientation="h",
            marker_color=colors, text=grp["Valor"].apply(fmt), textposition="outside"))
        fig.update_layout(title="🏆 Top 10 Eventos por Valor Total", xaxis_title="Valor Total (R$)",
            yaxis_title="", height=400, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)"))
        return fig

    def grafico_evolucao_saldo(df: pd.DataFrame):
        grp = df.groupby(["Ano", "Mês", "Tipo Evento"])["Valor"].sum().reset_index()
        pivot = grp.pivot_table(index=["Ano", "Mês"], columns="Tipo Evento", values="Valor", aggfunc="sum").fillna(0).reset_index()
        pivot["Período"] = pivot["Mês"].astype(str).str.zfill(2) + "/" + pivot["Ano"].astype(str)
        pivot = pivot.sort_values(["Ano", "Mês"])
        pivot["Saldo"] = pivot.get("Provento", 0) - pivot.get("Desconto", 0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=pivot["Período"], y=pivot["Saldo"], mode="lines+markers",
            fill="tozeroy", line=dict(color="#f39c12", width=2), marker=dict(size=6),
            fillcolor="rgba(243,156,18,0.2)", name="Saldo Líquido"))
        fig.update_layout(title="📈 Evolução do Saldo Líquido", xaxis_title="Período",
            yaxis_title="Saldo (R$)", height=350, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)"), yaxis=dict(gridcolor="rgba(255,255,255,0.1)"))
        return fig

    def grafico_gastos_funcao(df: pd.DataFrame, coluna: str = "Valor"):
        grp = df.groupby("Função")[coluna].sum().reset_index()
        grp = grp.sort_values(coluna, ascending=True).tail(10)
        label = "Valor Líquido (R$)" if coluna == "Liquido" else "Valor Total (R$)"
        fig = go.Figure(go.Bar(x=grp[coluna], y=grp["Função"], orientation="h",
            marker_color="#3498db", text=grp[coluna].apply(fmt), textposition="outside"))
        fig.update_layout(title="👔 Gastos por Função (Top 10)", xaxis_title=label,
            yaxis_title="", height=400, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)"))
        return fig

    def grafico_gastos_secao(df: pd.DataFrame, coluna: str = "Valor"):
        grp = df.groupby("Seção")[coluna].sum().reset_index()
        grp = grp.sort_values(coluna, ascending=True).tail(10)
        label = "Valor Líquido (R$)" if coluna == "Liquido" else "Valor Total (R$)"
        fig = go.Figure(go.Bar(x=grp[coluna], y=grp["Seção"], orientation="h",
            marker_color="#9b59b6", text=grp[coluna].apply(fmt), textposition="outside"))
        fig.update_layout(title="🏢 Gastos por Seção (Top 10)", xaxis_title=label,
            yaxis_title="", height=400, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)"))
        return fig

    def grafico_pareto_folha(df: pd.DataFrame, limiar_pareto: float = 80.0, n_buckets: int = 20,
                             tipo_valor: str = "Provento", agrupamento: str = "Funcionário"):
        """Pareto de concentração da folha com agrupamento em buckets para grandes quadros."""

        # ── Mapeamento de agrupamento e valor ──────────────────────────────
        col_grupo = {"Funcionário": "Nome", "Seção": "Seção", "Função": "Função"}[agrupamento]
        label_valor = {"Provento": "Proventos", "Desconto": "Descontos", "Base (Líquido)": "Base Líquida"}[tipo_valor]

        if tipo_valor == "Base (Líquido)":
            prov = df[df["Tipo Evento"] == "Provento"].groupby(col_grupo)["Valor"].sum()
            desc = df[df["Tipo Evento"] == "Desconto"].groupby(col_grupo)["Valor"].sum()
            grp_val = (prov.subtract(desc, fill_value=0)).reset_index()
            grp_val.columns = [col_grupo, "Valor"]
        else:
            grp_val = df[df["Tipo Evento"] == tipo_valor].groupby(col_grupo)["Valor"].sum().reset_index()

        grp = grp_val[grp_val["Valor"] > 0].sort_values("Valor", ascending=False).reset_index(drop=True)

        if grp.empty:
            return go.Figure().update_layout(
                title="📊 Sem dados para exibir",
                paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white")), 0, 0, 0, pd.DataFrame()

        total      = grp["Valor"].sum()
        n_total    = len(grp)
        grp["% Acumulado"] = (grp["Valor"].cumsum() / total * 100).round(2)
        grp["Rank"] = range(1, n_total + 1)

        # Corte no limiar
        idx_corte     = grp[grp["% Acumulado"] >= limiar_pareto].index[0]
        n_func_limiar = idx_corte + 1
        pct_func      = round(n_func_limiar / n_total * 100, 1)

        # Tabela de alerta
        df_alerta = grp.iloc[:n_func_limiar][["Rank", col_grupo, "Valor", "% Acumulado"]].copy()
        df_alerta["Valor"] = df_alerta["Valor"].apply(fmt)
        df_alerta["% Acumulado"] = df_alerta["% Acumulado"].apply(lambda v: f"{v:.1f}%")
        df_alerta = df_alerta.rename(columns={"Rank": "#", col_grupo: agrupamento, "Valor": label_valor, "% Acumulado": "% Acum."})

        # ── Agrupamento em buckets ──────────────────────────────────────────
        usar_buckets = n_total > 40
        if usar_buckets:
            tamanho_bucket = max(1, n_total // n_buckets)
            buckets = []
            for i in range(0, n_total, tamanho_bucket):
                fatia = grp.iloc[i:i+tamanho_bucket]
                rank_ini = fatia["Rank"].iloc[0]
                rank_fim = fatia["Rank"].iloc[-1]
                label    = f"{rank_ini}–{rank_fim}"
                valor_bk = fatia["Valor"].sum()
                pct_bk   = fatia["% Acumulado"].iloc[-1]
                n_bk     = len(fatia)
                no_alerta = fatia["Rank"].iloc[-1] <= n_func_limiar
                parcial   = fatia["Rank"].iloc[0] <= n_func_limiar < fatia["Rank"].iloc[-1]
                buckets.append({
                    "label": label, "Valor": valor_bk,
                    "% Acumulado": pct_bk, "n": n_bk,
                    "alerta": no_alerta, "parcial": parcial,
                    "rank_ini": rank_ini, "rank_fim": rank_fim
                })
            df_plot = pd.DataFrame(buckets)
            x_vals  = df_plot["label"]
            y_vals  = df_plot["Valor"]
            y2_vals = df_plot["% Acumulado"]
            cores   = ["#f39c12" if r["alerta"] else ("#f39c12" if r["parcial"] else "#2d2d44")
                       for _, r in df_plot.iterrows()]
            hover   = [
                f"<b>Grupo {r['label']}</b><br>"
                f"{agrupamento}s: {r['n']}<br>"
                f"Total {label_valor}: {fmt(r['Valor'])}<br>"
                f"% Acumulado: {r['% Acumulado']:.1f}%<extra></extra>"
                for _, r in df_plot.iterrows()
            ]
            bucket_corte = df_plot[df_plot["% Acumulado"] >= limiar_pareto].index[0]
            x_vline = df_plot.loc[bucket_corte, "label"]
        else:
            df_plot = grp
            x_vals  = grp["Rank"]
            y_vals  = grp["Valor"]
            y2_vals = grp["% Acumulado"]
            cores   = ["#f39c12" if i <= idx_corte else "#2d2d44" for i in grp.index]
            hover   = [
                f"<b>{r[col_grupo]}</b><br>Rank: {r['Rank']}º<br>"
                f"{label_valor}: {fmt(r['Valor'])}<br>"
                f"% Acumulado: {r['% Acumulado']:.1f}%<extra></extra>"
                for _, r in grp.iterrows()
            ]
            x_vline = n_func_limiar

        # ── Figura ──────────────────────────────────────────────────────────
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=x_vals, y=y_vals,
            name=f"Custo ({label_valor})",
            marker_color=cores,
            customdata=hover,
            hovertemplate="%{customdata}",
            showlegend=True
        ))

        _n   = len(list(y2_vals))
        _passo = max(1, _n // 8)
        _textos = [
            f"{v:.0f}%" if (i % _passo == 0 or i == _n - 1) else ""
            for i, v in enumerate(y2_vals)
        ]

        fig.add_trace(go.Scatter(
            x=x_vals, y=y2_vals,
            name="% Acumulado",
            mode="lines+markers+text",
            yaxis="y2",
            line=dict(color="#3498db", width=2),
            marker=dict(size=5 if not usar_buckets else 7),
            text=_textos,
            textposition="top center",
            textfont=dict(color="#3498db", size=10),
            hovertemplate="%{y:.1f}% acumulado<extra></extra>"
        ))

        fig.add_hline(
            y=limiar_pareto, yref="y2",
            line_dash="dash", line_color="#e74c3c", line_width=1.5,
            annotation_text=f"  {limiar_pareto:.0f}%",
            annotation_font_color="#e74c3c",
            annotation_position="top right"
        )

        if usar_buckets:
            x_vline_num = float(bucket_corte)
        else:
            x_vline_num = float(x_vline)

        fig.add_vline(
            x=x_vline_num,
            line_dash="dot", line_color="#f39c12", line_width=1.5,
            annotation_text=f"  {n_func_limiar} {agrupamento.lower()}(s).",
            annotation_font_color="#f39c12",
            annotation_position="top right"
        )

        modo = f" — agrupado em {len(df_plot)} faixas" if usar_buckets else ""
        eixo_x_label = f"{agrupamento}s (ordenados por custo)" + (" — faixas agrupadas" if usar_buckets else "")

        fig.update_layout(
            title=f"📊 Concentração da Folha{modo} — {n_func_limiar} {agrupamento.lower()}(s). ({pct_func}% do total) = {limiar_pareto:.0f}% do custo",
            xaxis=dict(
                title=eixo_x_label,
                tickfont=dict(color="rgba(255,255,255,0.5)", size=9),
                gridcolor="rgba(255,255,255,0.05)",
                tickangle=-45 if usar_buckets else 0
            ),
            yaxis=dict(
                title=dict(text=f"{label_valor} (R$)", font=dict(color="#f39c12")),
                tickfont=dict(color="#f39c12"),
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis2=dict(
                title=dict(text="% Acumulado", font=dict(color="#3498db")),
                overlaying="y", side="right",
                range=[0, 105], ticksuffix="%",
                tickfont=dict(color="#3498db"),
                gridcolor="rgba(0,0,0,0)"
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=500,
            margin=dict(t=80, b=80)
        )
        return fig, n_func_limiar, pct_func, n_total, df_alerta

    def grafico_comprometimento(df: pd.DataFrame, limiar: float, agrupamento: str):
        col = agrupamento
        prov = df[df["Tipo Evento"] == "Provento"].groupby(col)["Valor"].sum().rename("Proventos")
        desc = df[df["Tipo Evento"] == "Desconto"].groupby(col)["Valor"].sum().rename("Descontos")
        grp  = pd.concat([prov, desc], axis=1).fillna(0).reset_index()
        grp  = grp[grp["Proventos"] > 0].copy()
        grp["Índice (%)"] = (grp["Descontos"] / grp["Proventos"] * 100).round(1)
        grp = grp.sort_values("Índice (%)", ascending=False)
        if col == "Nome":
            info = df[["Nome", "Seção", "Função"]].drop_duplicates("Nome").set_index("Nome")
            grp["Seção"]  = grp["Nome"].map(info["Seção"]).fillna("-")
            grp["Função"] = grp["Nome"].map(info["Função"]).fillna("-")
            customdata = grp[["Proventos", "Descontos", "Seção", "Função"]].values
            hovertemplate = (
                "<b>%{y}</b><br>Seção: %{customdata[2]}<br>Função: %{customdata[3]}<br>"
                "Índice: %{x:.1f}%<br>Proventos: R$ %{customdata[0]:,.2f}<br>"
                "Descontos: R$ %{customdata[1]:,.2f}<extra></extra>"
            )
        else:
            customdata = grp[["Proventos", "Descontos"]].values
            hovertemplate = (
                "<b>%{y}</b><br>Índice: %{x:.1f}%<br>"
                "Proventos: R$ %{customdata[0]:,.2f}<br>"
                "Descontos: R$ %{customdata[1]:,.2f}<extra></extra>"
            )
        colors = ["#e74c3c" if v >= limiar else "#2ecc71" for v in grp["Índice (%)"]]
        texto  = grp["Índice (%)"].apply(lambda v: f"{v:.1f}%")
        fig = go.Figure(go.Bar(
            x=grp["Índice (%)"], y=grp[col], orientation="h",
            marker_color=colors, text=texto, textposition="outside",
            customdata=customdata, hovertemplate=hovertemplate
        ))
        fig.add_vline(x=limiar, line_dash="dash", line_color="#f39c12",
            annotation_text=f"  Limiar {limiar:.0f}%",
            annotation_font_color="#f39c12", annotation_position="top right")
        alertas = (grp["Índice (%)"] >= limiar).sum()
        titulo  = f"🚨 Índice de Comprometimento por {col} — {alertas} acima do limiar"
        fig.update_layout(title=titulo, xaxis_title="Descontos / Proventos (%)", yaxis_title="",
            height=max(400, len(grp) * 28), plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)", ticksuffix="%"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)", autorange="reversed"))
        return fig, alertas, grp

    # ---------- Layout do Dashboard ----------
    st.title("📊 Ficha Financeira — RM TOTVS")
    st.markdown("---")

    conexao_ok = st.session_state.get("conexao_ok", False)

    with st.expander("⚙️ Configurações de Conexão", expanded=not conexao_ok):
        st.caption("Informe os dados do servidor RM para estabelecer a conexão. Se seu ambiente é Cloud TOTVS informe como o exemplo: https://claudioximenes.rm.cloudtotvs.com.br:10607")
        st.caption("Atenção !!!! Para utilizar esse Dashboard você precisa solicitar o acesso no grupo do Telegram na página inicial")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            servidor_input = st.text_input("🌐 Endereço do Servidor",
                value=st.session_state.get("servidor_base", "http://localhost:8051"),
                placeholder="Ex: http://192.168.1.10:8051")
        with col2:
            usuario_input = st.text_input("👤 Usuário", value=st.session_state.get("rm_usuario", "mestre"))
        with col3:
            senha_input = st.text_input("🔒 Senha", value=st.session_state.get("rm_senha", ""), type="password")
        if st.button("💾 Salvar Configurações", use_container_width=True):
            servidor_base = servidor_input.strip().rstrip("/")
            if not servidor_base.startswith("http"):
                st.error("⚠️ O endereço deve começar com http:// ou https://")
            elif not usuario_input.strip():
                st.error("⚠️ Informe o usuário.")
            elif not senha_input.strip():
                st.error("⚠️ Informe a senha.")
            else:
                st.session_state["servidor_base"] = servidor_base
                st.session_state["wsdl_url"]      = servidor_base + WSDL_SUFIXO
                st.session_state["rm_usuario"]    = usuario_input.strip()
                st.session_state["rm_senha"]      = senha_input
                st.session_state["conexao_ok"]    = True
                st.session_state.pop("df", None)
                st.success(f"✅ Conexão configurada! URL: `{st.session_state['wsdl_url']}`")
                st.rerun()

    if conexao_ok:
        st.info(f"🔗 Conectado em: `{st.session_state['wsdl_url']}` | Usuário: `{st.session_state['rm_usuario']}`")

    st.markdown("---")

    if not st.session_state.get("conexao_ok"):
        st.warning("⚠️ Configure e salve as **Configurações de Conexão** acima antes de consultar.")
        st.stop()

    st.subheader("🔍 Parâmetros da Consulta")
    with st.form("form_consulta_dash"):
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            coligada_input = st.text_input("Coligada", value="1")
        with col2:
            ano_input = st.number_input("Ano", min_value=2000, max_value=2100, value=2024, step=1)
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            consultar = st.form_submit_button("🔎 Consultar", use_container_width=True)

    if consultar:
        if not coligada_input.strip().isdigit():
            st.error("Coligada deve ser um número válido.")
            st.stop()
        st.session_state["param_coligada"] = coligada_input
        st.session_state["param_ano"] = ano_input
        st.session_state["executar_consulta"] = True

    if st.session_state.get("executar_consulta"):
        st.session_state["executar_consulta"] = False
        with st.spinner(f"Buscando dados..."):
            st.session_state["df"] = buscar_dados(
                int(st.session_state["param_coligada"]),
                int(st.session_state["param_ano"])
            )
        st.session_state["consultou"] = True

    df: pd.DataFrame = st.session_state.get("df", pd.DataFrame())

    if not st.session_state.get("consultou"):
        st.info("👆 Preencha a Coligada e o Ano acima e clique em **Consultar** para carregar os dados.")
        st.stop()

    if df.empty or "Ano" not in df.columns:
        st.warning(f"⚠️ Dados não encontrados para Coligada **{st.session_state['param_coligada']}** / Ano **{st.session_state['param_ano']}**.")
        st.stop()

    colunas_esperadas = ["Ano", "Mês", "Nome", "Tipo Evento", "Evento", "Valor", "Empresa"]
    colunas_faltando = [c for c in colunas_esperadas if c not in df.columns]
    if colunas_faltando:
        st.error(f"Colunas não encontradas: {colunas_faltando}")
        st.stop()

    st.success(f"✅ Coligada **{st.session_state['param_coligada']}** | Ano **{st.session_state['param_ano']}** | **{len(df):,}** registros carregados.")
    st.markdown("---")

    # Filtros
    st.subheader("🔎 Filtros")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        anos = st.multiselect("Ano", sorted(df["Ano"].unique()), default=sorted(df["Ano"].unique()))
    with col2:
        tipos = st.multiselect("Tipo de Evento", df["Tipo Evento"].unique(), default=df["Tipo Evento"].unique())
    with col3:
        periodos_disponiveis = sorted(df["Período"].dropna().unique().tolist())
        periodos_sel = st.multiselect("Período", periodos_disponiveis, default=periodos_disponiveis)
    with col4:
        lista_funcionarios = ["Todos"] + sorted(df["Nome"].unique().tolist())
        funcionario_sel = st.selectbox("👤 Funcionário", lista_funcionarios)

    mes_min = int(df["Mês"].min())
    mes_max = int(df["Mês"].max())
    mes_inicio, mes_fim = st.slider("📅 Intervalo de Mês", min_value=mes_min, max_value=mes_max,
        value=(mes_min, mes_max), format="%d")
    st.caption(f"Filtrando de **{MESES[mes_inicio]}** até **{MESES[mes_fim]}**")

    nomes_filtro = df["Nome"].unique() if funcionario_sel == "Todos" else [funcionario_sel]
    df_filtrado = df[
        df["Ano"].isin(anos) &
        df["Tipo Evento"].isin(tipos) &
        df["Período"].isin(periodos_sel) &
        df["Nome"].isin(nomes_filtro) &
        df["Mês"].between(mes_inicio, mes_fim)
    ]

    st.markdown("---")

    # Métricas
    st.subheader("📈 Resumo")
    col1, col2, col3, col4 = st.columns(4)
    total_proventos = df_filtrado[df_filtrado["Tipo Evento"] == "Provento"]["Valor"].sum()
    total_descontos = df_filtrado[df_filtrado["Tipo Evento"] == "Desconto"]["Valor"].sum()
    saldo           = total_proventos - total_descontos
    col1.metric("Total de Registros", len(df_filtrado))
    col2.metric("Total Proventos",    fmt(total_proventos))
    col3.metric("Total Descontos",    fmt(total_descontos))
    col4.metric("Saldo Líquido",      fmt(saldo))

    st.markdown("---")

    # Gráficos
    st.plotly_chart(grafico_proventos_descontos_saldo(df_filtrado), use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafico_evolucao_saldo(df_filtrado), use_container_width=True)
    with col2:
        st.plotly_chart(grafico_ranking_eventos(df_filtrado), use_container_width=True)

    tipo_valor = st.radio("💰 Tipo de Valor — Gastos por Função e Seção",
        options=["Valor Bruto", "Valor Líquido"], horizontal=True)
    coluna_valor = "Liquido" if tipo_valor == "Valor Líquido" else "Valor"

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafico_gastos_funcao(df_filtrado, coluna_valor), use_container_width=True)
    with col2:
        st.plotly_chart(grafico_gastos_secao(df_filtrado, coluna_valor), use_container_width=True)

    st.markdown("---")

    # Pareto de Concentração da Folha
    st.subheader("📊 Concentração da Folha de Pagamento")
    st.caption("Identifica quem concentra a maior parte do custo total — princípio de Pareto.")

    col_par1, col_par2, col_par3, col_par4 = st.columns([1, 1, 1, 1])
    with col_par1:
        limiar_pareto = st.slider("🎯 Limiar de concentração (%)",
            min_value=50, max_value=95, value=80, step=5,
            help="Percentual do custo total a ser analisado")
    with col_par2:
        n_buckets = st.slider("📦 Número de faixas (buckets)",
            min_value=10, max_value=50, value=20, step=5,
            help="Usado quando há mais de 40 itens. Agrupa em N faixas para melhor visualização.")
    with col_par3:
        tipo_valor_pareto = st.selectbox("💰 Tipo de Valor",
            options=["Provento", "Desconto", "Base (Líquido)"],
            help="Provento = bruto recebido | Desconto = total descontado | Base (Líquido) = Provento − Desconto")
    with col_par4:
        agrupamento_pareto = st.selectbox("👥 Agrupar por",
            options=["Funcionário", "Seção", "Função"],
            help="Define a dimensão de análise do Pareto")

    resultado_pareto = grafico_pareto_folha(df_filtrado, float(limiar_pareto), n_buckets,
                                            tipo_valor_pareto, agrupamento_pareto)

    if isinstance(resultado_pareto, tuple):
        fig_pareto, n_func, pct_func, total_func, df_alerta = resultado_pareto

        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric(f"👥 Total de {agrupamento_pareto}s", total_func)
        col_p2.metric(f"🎯 {agrupamento_pareto}s que concentram {limiar_pareto}%", n_func)
        col_p3.metric("📌 Representam", f"{pct_func}% do total")

        st.plotly_chart(fig_pareto, use_container_width=True)

        if not df_alerta.empty:
            with st.expander(f"📋 Ver os {n_func} {agrupamento_pareto.lower()}(s) que concentram {limiar_pareto}% do custo", expanded=False):
                st.caption(f"{agrupamento_pareto}s ordenados por maior custo ({tipo_valor_pareto}), do maior para o menor.")
                st.dataframe(df_alerta.reset_index(drop=True), use_container_width=True)
                csv_alerta = df_alerta.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
                st.download_button(
                    "⬇️ Baixar lista em CSV",
                    data=csv_alerta,
                    file_name=f"concentracao_folha_{limiar_pareto:.0f}pct.csv",
                    mime="text/csv"
                )
    else:
        st.plotly_chart(resultado_pareto, use_container_width=True)

    st.markdown("---")

    # Índice de comprometimento
    st.subheader("🚨 Índice de Comprometimento de Descontos")
    st.caption("Proporção de Descontos em relação aos Proventos. Valores acima do limiar são destacados em vermelho.")
    col_limiar, _ = st.columns([1, 3])
    with col_limiar:
        limiar_pct = st.slider("⚠️ Limiar de alerta (%)", min_value=10, max_value=80, value=30, step=5)

    POR_PAGINA = 20
    tabs_comp = st.tabs(["👤 Por Funcionário", "🏢 Por Seção", "👔 Por Função"])
    agrupamentos = ["Nome", "Seção", "Função"]

    for tab, agrup in zip(tabs_comp, agrupamentos):
        with tab:
            _, qtd_alertas, df_comp = grafico_comprometimento(df_filtrado, limiar_pct, agrup)
            if qtd_alertas > 0:
                st.warning(f"⚠️ **{qtd_alertas}** {agrup.lower()}(s) com índice acima de **{limiar_pct}%**")
            else:
                st.success(f"✅ Nenhum(a) {agrup.lower()} acima do limiar de **{limiar_pct}%**")

            total     = len(df_comp)
            total_pag = max(1, -(-total // POR_PAGINA))
            pag_key   = f"pag_{agrup}"
            pag_atual = min(st.session_state.get(pag_key, 0), total_pag - 1)
            inicio = pag_atual * POR_PAGINA
            fim    = inicio + POR_PAGINA
            df_pag = df_comp.iloc[inicio:fim]

            fig_pag, _, _ = grafico_comprometimento(
                df_filtrado[df_filtrado[agrup].isin(df_pag[agrup])], limiar_pct, agrup)
            fig_pag.update_layout(title=f"🚨 Comprometimento por {agrup} — Pág. {pag_atual+1}/{total_pag} ({total} registros)")
            st.plotly_chart(fig_pag, use_container_width=True)

            col_prev, *cols_num, col_next = st.columns([1] + [1]*min(total_pag, 10) + [1])
            with col_prev:
                if st.button("◀", key=f"prev_{agrup}", disabled=pag_atual == 0):
                    st.session_state[pag_key] = pag_atual - 1
                    st.rerun()
            for i, col in enumerate(cols_num):
                pag_i = i if total_pag <= 10 else round(i * (total_pag - 1) / max(len(cols_num)-1, 1))
                label = f"**{pag_i+1}**" if pag_i == pag_atual else str(pag_i+1)
                with col:
                    if st.button(label, key=f"pag_{agrup}_{i}"):
                        st.session_state[pag_key] = pag_i
                        st.rerun()
            with col_next:
                if st.button("▶", key=f"next_{agrup}", disabled=pag_atual >= total_pag - 1):
                    st.session_state[pag_key] = pag_atual + 1
                    st.rerun()
            st.caption(f"Exibindo {inicio+1}–{min(fim, total)} de **{total}** registros")

            df_alerta = df_comp[df_comp["Índice (%)"] >= limiar_pct].sort_values("Índice (%)", ascending=False)
            if not df_alerta.empty:
                with st.expander(f"📋 Ver detalhes dos {agrup.lower()}(s) em alerta"):
                    df_alerta_fmt = df_alerta[[agrup, "Proventos", "Descontos", "Índice (%)"]].copy()
                    df_alerta_fmt["Proventos"]  = df_alerta_fmt["Proventos"].apply(fmt)
                    df_alerta_fmt["Descontos"]  = df_alerta_fmt["Descontos"].apply(fmt)
                    df_alerta_fmt["Índice (%)"] = df_alerta_fmt["Índice (%)"].apply(lambda v: f"{v:.1f}%")
                    st.dataframe(df_alerta_fmt.reset_index(drop=True), use_container_width=True)

    st.markdown("---")

    # Envelope de Pagamento
    st.subheader("🧾 Envelope de Pagamento")
    st.caption("Selecione um funcionário e o período para visualizar o envelope detalhado.")

    col_env1, col_env2, col_env3, col_env4 = st.columns([2, 1, 1, 1])
    with col_env1:
        func_env = st.selectbox("👤 Funcionário", sorted(df["Nome"].unique().tolist()), key="env_func")
    with col_env2:
        meses_env_disp = sorted(df["Mês"].dropna().unique().tolist())
        mes_env = st.selectbox("🗓️ Mês", meses_env_disp,
            index=len(meses_env_disp)-1, format_func=lambda m: MESES.get(int(m), str(m)), key="env_mes")
    with col_env3:
        periodos_env_disp = sorted(df[(df["Nome"]==func_env)&(df["Mês"]==mes_env)]["Período"].dropna().unique().tolist())
        if not periodos_env_disp:
            periodos_env_disp = sorted(df[df["Mês"]==mes_env]["Período"].dropna().unique().tolist())
        periodo_env = st.selectbox("📋 Período", periodos_env_disp,
            index=len(periodos_env_disp)-1, key="env_periodo")
    with col_env4:
        st.markdown("<br>", unsafe_allow_html=True)
        gerar_envelope = st.button("📄 Gerar Envelope", use_container_width=True)

    if gerar_envelope:
        st.session_state["envelope_gerado"] = True
        st.session_state["envelope_func"]   = func_env
        st.session_state["envelope_mes"]    = mes_env
        st.session_state["envelope_period"] = periodo_env

    if st.session_state.get("envelope_gerado"):
        _func   = st.session_state["envelope_func"]
        _mes    = st.session_state["envelope_mes"]
        _period = st.session_state["envelope_period"]
        df_env  = df[(df["Nome"]==_func)&(df["Mês"]==_mes)&(df["Período"]==_period)].copy()

        if not df_env.empty:
            _ano_env = int(df_env["Ano"].iloc[0])
            _period_label = f"{MESES.get(_mes, str(_mes))}/{_ano_env} — Período {_period}"
        else:
            _period_label = f"{MESES.get(_mes, str(_mes))} — Período {_period}"

        if df_env.empty:
            st.warning(f"Nenhum dado encontrado para **{_func}** no período **{_period_label}**.")
        else:
            empresa = df_env["Empresa"].iloc[0] if "Empresa" in df_env.columns else ""
            proventos_df = df_env[df_env["Tipo Evento"]=="Provento"][["Evento","Período","Valor"]].copy()
            descontos_df = df_env[df_env["Tipo Evento"]=="Desconto"][["Evento","Período","Valor"]].copy()
            total_prov = proventos_df["Valor"].sum()
            total_desc = descontos_df["Valor"].sum()
            liquido    = total_prov - total_desc
            linhas = []
            for _, row in proventos_df.iterrows():
                ev = str(int(float(row["Evento"]))) if str(row["Evento"]).replace(".","").isdigit() else row["Evento"]
                linhas.append({"Evento": ev, "Proventos": fmt(row["Valor"]), "Descontos": ""})
            for _, row in descontos_df.iterrows():
                ev = str(int(float(row["Evento"]))) if str(row["Evento"]).replace(".","").isdigit() else row["Evento"]
                linhas.append({"Evento": ev, "Proventos": "", "Descontos": fmt(row["Valor"])})
            df_envelope = pd.DataFrame(linhas)
            rows_html = ""
            for _, r in df_envelope.iterrows():
                rows_html += f"<tr><td style='text-align:center'>{r['Evento']}</td><td style='text-align:right'>{r['Proventos']}</td><td style='text-align:right'>{r['Descontos']}</td></tr>"

            envelope_html = f"""
            <style>
            .envelope-wrap {{ font-family: Arial, sans-serif; font-size: 13px; color: #e0e0e0; }}
            .envelope-wrap table {{ width: 100%; border-collapse: collapse; background: #1e1e2e; border-radius: 8px; overflow: hidden; }}
            .envelope-wrap .title-row td {{ background: #2d2d44; text-align: center; font-weight: bold; font-size: 15px; padding: 10px; letter-spacing: 1px; color: #ffffff; border-bottom: 2px solid #444; }}
            .envelope-wrap .func-row td {{ background: #252535; padding: 6px 10px; font-weight: bold; color: #ccc; border-bottom: 1px solid #444; text-align: center; }}
            .envelope-wrap .header-row td {{ background: #2d2d44; padding: 7px 10px; color: #aaa; font-size: 12px; border-bottom: 2px solid #555; font-weight: bold; text-transform: uppercase; }}
            .envelope-wrap tbody tr:nth-child(even) {{ background: #1a1a2e; }}
            .envelope-wrap tbody tr:nth-child(odd)  {{ background: #1e1e2e; }}
            .envelope-wrap tbody td {{ padding: 6px 10px; border-bottom: 1px solid #2a2a3e; text-align: center; }}
            .envelope-wrap .totals-row td {{ background: #252535; padding: 7px 10px; font-weight: bold; text-align: right; border-top: 2px solid #555; color: #ccc; }}
            .envelope-wrap .liquido-row td {{ background: #1c3a2a; padding: 8px 10px; font-weight: bold; text-align: right; color: #2ecc71; font-size: 14px; border-top: 2px solid #2ecc71; }}
            </style>
            <div class="envelope-wrap"><table><tbody>
                <tr class="title-row"><td colspan="3">ENVELOPE DE PAGAMENTO</td></tr>
                <tr class="func-row"><td colspan="3">FUNCIONÁRIO: {_func} &nbsp;|&nbsp; EMPRESA: {empresa} &nbsp;|&nbsp; PERÍODO: {_period_label}</td></tr>
                <tr class="header-row"><td style="text-align:center;width:60%">DESCRIÇÃO</td><td style="text-align:right;width:20%">PROVENTOS</td><td style="text-align:right;width:20%">DESCONTOS</td></tr>
                {rows_html}
            </tbody>
                <tr class="totals-row"><td style="text-align:right;color:#aaa">Totais</td><td>{fmt(total_prov)}</td><td>{fmt(total_desc)}</td></tr>
                <tr class="liquido-row"><td style="text-align:left">💰 LÍQUIDO</td><td></td><td>{fmt(liquido)}</td></tr>
            </table></div>"""
            st.html(envelope_html)
            csv_env = df_envelope.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
            st.download_button("⬇️ Baixar Envelope CSV", data=csv_env,
                file_name=f"envelope_{_func.replace(' ','_')}.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("📋 Dados Detalhados")
    tab1, tab2 = st.tabs(["📊 Análise Dinâmica (PyGWalker)", "📋 Tabela"])
    with tab1:
        st.caption("Arraste os campos para criar seus próprios agrupamentos e gráficos!")
        renderer = StreamlitRenderer(df_filtrado.sort_values(["Ano","Mês","Nome"]).reset_index(drop=True))
        renderer.explorer()
    with tab2:
        st.dataframe(df_filtrado.sort_values(["Ano","Mês","Nome"]).reset_index(drop=True), use_container_width=True)
        csv = df_filtrado.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
        st.download_button("⬇️ Baixar CSV", data=csv, file_name="ficha_financeira.csv", mime="text/csv")

# ============================================================
# ██  MÓDULO: SQL MAKER
# ============================================================
elif st.session_state["modulo_ativo"] == "sqlmaker":

    # ---------- Helpers ----------
    def gerar_preview_fake(colunas):
        dados = {}
        for col in colunas:
            nome_coluna = col.split(".")[-1].upper()
            if any(p in nome_coluna for p in ["COD","ID","NUM","SEQ"]):
                dados[col] = [random.randint(1,9999) for _ in range(5)]
            elif any(p in nome_coluna for p in ["DATA","DT"]):
                dados[col] = pd.date_range(start="2024-01-01", periods=5)
            elif any(p in nome_coluna for p in ["VALOR","SAL","TOTAL","PRECO"]):
                dados[col] = [round(random.uniform(1000,5000),2) for _ in range(5)]
            elif any(p in nome_coluna for p in ["ATIVO","STATUS"]):
                dados[col] = [random.choice(["SIM","NÃO"]) for _ in range(5)]
            else:
                dados[col] = [f"{nome_coluna}_{i}" for i in range(1,6)]
        return pd.DataFrame(dados)

    def inicializar_historico():
        if "historico_queries" not in st.session_state:
            st.session_state.historico_queries = []

    def adicionar_ao_historico(sql, tabela_principal, campos_count, tem_join=False, tem_calculo=False):
        inicializar_historico()
        timestamp = datetime.now()
        partes = [f"SELECT de {tabela_principal}"]
        if tem_join:    partes.append("com JOINs")
        if tem_calculo: partes.append("com cálculos")
        item = {
            "sql": sql, "timestamp": timestamp,
            "timestamp_str": timestamp.strftime("%d/%m/%Y %H:%M"),
            "descricao": " ".join(partes), "tabela": tabela_principal,
            "campos_count": campos_count, "favorito": False, "editada": False
        }
        st.session_state.historico_queries.insert(0, item)
        nao_fav = [q for q in st.session_state.historico_queries if not q["favorito"]]
        fav     = [q for q in st.session_state.historico_queries if q["favorito"]]
        if len(nao_fav) > 10:
            nao_fav = nao_fav[:10]
        st.session_state.historico_queries = fav + nao_fav

    def salvar_query_em_arquivo(sql, tabela_principal):
        try:
            if not os.path.exists("historico_queries"):
                os.makedirs("historico_queries")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"historico_queries/query_{tabela_principal}_{timestamp}.sql"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"-- Query gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"-- Tabela principal: {tabela_principal}\n-- Gerado por: RM Suite\n\n")
                f.write(sql)
            return filename
        except Exception as e:
            st.warning(f"Não foi possível salvar automaticamente: {e}")
            return None

    def toggle_favorito(index):
        if "historico_queries" in st.session_state and index < len(st.session_state.historico_queries):
            st.session_state.historico_queries[index]["favorito"] = not st.session_state.historico_queries[index]["favorito"]

    def atualizar_query_editada(sql_editada):
        inicializar_historico()
        if st.session_state.historico_queries and sql_editada != st.session_state.get("sql_gerada",""):
            st.session_state.historico_queries[0]["sql"] = sql_editada
            st.session_state.historico_queries[0]["editada"] = True
            if "tabela_atual" in st.session_state:
                return salvar_query_em_arquivo(sql_editada, st.session_state.tabela_atual)
        return None

    def extrair_colunas_select(sql):
        sql = re.sub(r"--.*","",sql)
        match = re.search(r"SELECT(.*?)FROM", sql, re.IGNORECASE|re.DOTALL)
        if not match: return []
        bloco_select = match.group(1)
        colunas_raw  = [c.strip() for c in bloco_select.split(",") if c.strip()]
        colunas_final = []
        for col in colunas_raw:
            alias_match = re.search(r"\s+AS\s+(.+)$", col, re.IGNORECASE)
            if alias_match:
                colunas_final.append(alias_match.group(1).strip()); continue
            func_match = re.search(r"(\w+)\((.*?)\)", col)
            if func_match:
                func  = func_match.group(1).upper()
                campo = func_match.group(2).split(".")[-1]
                colunas_final.append(f"{func}_{campo}"); continue
            colunas_final.append(col)
        return colunas_final

    @st.cache_data
    def load_data():
        try:
            df_campos   = pd.read_excel("CAMPOS.xlsx")
            df_sistemas = pd.read_excel("SISTEMAS.xlsx")
            df_relacoes = pd.read_excel("RELACIONAMENTOS.xlsx")
            return df_campos, df_sistemas, df_relacoes
        except Exception as e:
            st.error(f"Erro ao carregar planilhas: {e}")
            return None, None, None

    # ---------- Layout ----------
    st.title("🚀 SQL Maker — Assistente de Relatórios RM")
    st.markdown("---")

    tab_tutorial, tab_gerador, tab_historico = st.tabs(["📖 Como Usar", "🛠️ Criar minha Sentença", "🕐 Histórico"])

    df_campos, df_sistemas, df_relacoes = load_data()

    # ABA 1: TUTORIAL
    with tab_tutorial:
        st.header("Seja bem-vindo ao SQL Maker!")
        st.markdown("Esta ferramenta permite que você extraia informações do RM de forma visual, sem precisar escrever SQL manualmente.")

        st.markdown("### ✨ Funcionalidades Principais")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                padding:20px;border-radius:10px;height:180px;">
                <h3 style="color:white;margin:0;">🎯 Seleção Inteligente</h3>
                <p style="color:#f0f0f0;font-size:14px;margin-top:10px;">
                • Escolha tabelas e campos<br>• JOINs automáticos<br>• Interface visual simples</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("""<div style="background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);
                padding:20px;border-radius:10px;height:180px;">
                <h3 style="color:white;margin:0;">🔢 Cálculos e Filtros</h3>
                <p style="color:#f0f0f0;font-size:14px;margin-top:10px;">
                • SUM, COUNT, AVG, MAX, MIN<br>• Filtros WHERE avançados<br>• GROUP BY automático</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown("""<div style="background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);
                padding:20px;border-radius:10px;height:180px;">
                <h3 style="color:white;margin:0;">📊 ORDER BY</h3>
                <p style="color:#f0f0f0;font-size:14px;margin-top:10px;">
                • Ordenação ASC/DESC<br>• Múltiplos critérios<br>• Interface intuitiva</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown("""<div style="background:linear-gradient(135deg,#fa709a 0%,#fee140 100%);
                padding:20px;border-radius:10px;height:180px;">
                <h3 style="color:white;margin:0;">💾 Histórico</h3>
                <p style="color:#f0f0f0;font-size:14px;margin-top:10px;">
                • Salva automaticamente<br>• Marque favoritas<br>• Exportação em .sql</p>
            </div>""", unsafe_allow_html=True)
        with col5:
            st.markdown("""<div style="background:linear-gradient(135deg,#30cfd0 0%,#330867 100%);
                padding:20px;border-radius:10px;height:180px;">
                <h3 style="color:white;margin:0;">✏️ Editor SQL</h3>
                <p style="color:#f0f0f0;font-size:14px;margin-top:10px;">
                • Edite antes de usar<br>• Syntax highlighting<br>• Copiar com 1 clique</p>
            </div>""", unsafe_allow_html=True)
        with col6:
            st.markdown("""<div style="background:linear-gradient(135deg,#a8edea 0%,#fed6e3 100%);
                padding:20px;border-radius:10px;height:180px;">
                <h3 style="color:#333;margin:0;">🔗 Joins Flexíveis</h3>
                <p style="color:#555;font-size:14px;margin-top:10px;">
                • INNER, LEFT, RIGHT, FULL<br>• Relacionamentos automáticos<br>• Múltiplas tabelas</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Passo a Passo:")
        st.markdown("""
        1. **Módulo:** Escolha o sistema (Ex: P - RH).
        2. **Tabela:** Escolha o assunto (Ex: Funcionários).
        3. **Colunas:** Marque o que você quer ver no relatório.
        4. **Joins:** Use se precisar buscar informações de outras tabelas.
        5. **Cálculos:** Use se precisar somar valores ou contar registros.
        6. **Filtros:** Use se precisar filtrar o que é mostrado.
        7. **Ordenação:** Organize os resultados na ordem desejada.
        8. **Revise e Baixe:** Edite, copie ou exporte o script gerado.
        """)
        st.success("Tudo pronto? Clique na aba **'Criar minha Sentença'** acima!")

        st.markdown("---")
        st.markdown("### 🤝 Comunidade e Suporte")
        st.markdown("""<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
            padding:25px;border-radius:15px;margin:20px 0;text-align:center;">
            <h3 style="color:white;margin:0;">💬 Grupo do Telegram</h3>
            <p style="color:#f0f0f0;font-size:16px;margin-top:15px;">
            Tem dúvidas, encontrou um erro ou quer sugerir uma nova tabela?<br>
            <strong>Junte-se à nossa comunidade!</strong></p>
        </div>""", unsafe_allow_html=True)
        col_tg1, col_tg2, col_tg3 = st.columns([1,2,1])
        with col_tg2:
            st.link_button("📱 Entrar no Grupo do Telegram", "https://t.me/+HC1B2Grb0UdhNzlh",
                use_container_width=True, type="primary")

    # ABA 2: GERADOR
    with tab_gerador:
        if df_campos is not None:
            seed = st.session_state.get("reset_counter", 0)

            df_sistemas.columns = df_sistemas.columns.str.strip().str.upper()
            df_campos.columns   = df_campos.columns.str.strip().str.upper()
            df_relacoes.columns = df_relacoes.columns.str.strip().str.upper()

            df_sistemas["LABEL"] = df_sistemas["CODSISTEMA"].astype(str) + " - " + df_sistemas["DESCRICAO"]
            sistema_sel = st.selectbox("1. Qual o Módulo do RM?", df_sistemas["LABEL"], key=f"sis_{seed}")
            cod_sistema = str(df_sistemas[df_sistemas["LABEL"]==sistema_sel]["CODSISTEMA"].values[0])

            tab_disponiveis = df_campos[df_campos["TABELA"].fillna("").str.startswith(cod_sistema)]["TABELA"].unique()
            tabela_pai = st.selectbox("2. Escolha a Tabela Principal", sorted(tab_disponiveis), key=f"pai_{seed}")

            col_nome_campo = df_campos.columns[1]
            todos_campos_pai = df_campos[df_campos["TABELA"]==tabela_pai][col_nome_campo].dropna().tolist()
            campos_pai_sel   = st.multiselect(f"Quais informações de {tabela_pai} você quer?",
                options=todos_campos_pai, key=f"cols_pai_{seed}")

            # Pai → Filha (direto)
            filhas_do_pai = df_relacoes[df_relacoes["MASTERTABLE"]==tabela_pai]["CHILDTABLE"].unique().tolist()

            # Filha → Filha: tabelas que se relacionam com qualquer filha do pai
            # mas que NÃO têm vínculo direto com a tabela pai
            filhas_das_filhas = df_relacoes[df_relacoes["MASTERTABLE"].isin(filhas_do_pai)]["CHILDTABLE"].unique().tolist()
            todas_filhas_possiveis = list(set(filhas_do_pai + filhas_das_filhas))

            filhas_finais = sorted([t for t in todas_filhas_possiveis if t != tabela_pai])

            tabelas_filhas = st.multiselect("Deseja buscar dados em tabelas relacionadas? (Joins)", filhas_finais, key=f"fil_{seed}")

            tipos_join      = {}
            campos_por_filha = {}
            for filha in tabelas_filhas:
                st.markdown(f"**📎 {filha}**")
                col_join, col_campos = st.columns([1,3])
                with col_join:
                    st.markdown("**Tipo de JOIN:**")
                    tipo_join = st.selectbox("Tipo de JOIN", options=["INNER","LEFT","RIGHT","FULL"],
                        key=f"join_{filha}_{seed}", label_visibility="collapsed")
                    tipos_join[filha] = tipo_join
                with col_campos:
                    st.markdown("**Colunas:**")
                    campos_da_filha = df_campos[df_campos["TABELA"]==filha][col_nome_campo].dropna().tolist()
                    campos_por_filha[filha] = st.multiselect(f"Colunas de: {filha}",
                        options=campos_da_filha, key=f"cols_{filha}_{seed}", label_visibility="collapsed")

            st.markdown("### 📊 Adicionar Cálculos (Opcional)")
            col1, col2 = st.columns(2)
            with col1:
                op_agregacao = st.selectbox("Deseja fazer algum cálculo?",
                    ["NENHUM","SOMA (SUM)","CONTAGEM (COUNT)","MÉDIA (AVG)","MÁXIMO (MAX)","MÍNIMO (MIN)"],
                    key=f"op_{seed}")
            with col2:
                if op_agregacao != "NENHUM":
                    todos_escolhidos = campos_pai_sel + [item for sublist in campos_por_filha.values() for item in sublist]
                    campo_metrica = st.selectbox("Calcular sobre qual coluna?", [""]+todos_escolhidos, key=f"met_{seed}")

            # Filtros WHERE
            st.markdown("### 🔍 Filtros (WHERE)")
            if f"filtros_{seed}" not in st.session_state:
                st.session_state[f"filtros_{seed}"] = []
            if f"filtro_counter_{seed}" not in st.session_state:
                st.session_state[f"filtro_counter_{seed}"] = 0

            campos_disponiveis_filtro = {}
            for campo in todos_campos_pai:
                campos_disponiveis_filtro[f"{tabela_pai}.{campo}"] = tabela_pai
            for filha in tabelas_filhas:
                campos_da_filha = df_campos[df_campos["TABELA"]==filha][col_nome_campo].dropna().tolist()
                for campo in campos_da_filha:
                    campos_disponiveis_filtro[f"{filha}.{campo}"] = filha
            lista_campos_filtro = sorted(list(campos_disponiveis_filtro.keys()))

            with st.expander("➕ Adicionar Novo Filtro", expanded=len(st.session_state[f"filtros_{seed}"])==0):
                filtro_key = f"{seed}_{st.session_state[f'filtro_counter_{seed}']}"
                col_campo, col_op, col_valor = st.columns([2,1,2])
                with col_campo:
                    campo_filtro = st.selectbox("Campo", options=[""]+lista_campos_filtro, key=f"novo_campo_filtro_{filtro_key}")
                with col_op:
                    operador_filtro = st.selectbox("Operador",
                        options=["=","!=",">","<",">=","<=","LIKE","NOT LIKE","IN","NOT IN","BETWEEN","IS NULL","IS NOT NULL"],
                        key=f"novo_op_filtro_{filtro_key}")
                with col_valor:
                    if operador_filtro not in ["IS NULL","IS NOT NULL"]:
                        if operador_filtro == "BETWEEN":
                            cv1, cv2 = st.columns(2)
                            with cv1:
                                valor1_filtro = st.text_input("Valor Inicial", placeholder="Ex: 1", key=f"novo_valor1_filtro_{filtro_key}")
                            with cv2:
                                valor2_filtro = st.text_input("Valor Final", placeholder="Ex: 100", key=f"novo_valor2_filtro_{filtro_key}")
                            valor_filtro = f"{valor1_filtro}|{valor2_filtro}"
                        elif operador_filtro in ["IN","NOT IN"]:
                            valor_filtro = st.text_input("Valores (separados por vírgula)", placeholder="Ex: 1, 2, 3", key=f"novo_valor_filtro_{filtro_key}")
                        elif operador_filtro in ["LIKE","NOT LIKE"]:
                            valor_filtro = st.text_input("Valor", placeholder="Ex: %XIMENES%", key=f"novo_valor_filtro_{filtro_key}")
                        else:
                            valor_filtro = st.text_input("Valor", placeholder="Ex: 1 ou 'TEXTO'", key=f"novo_valor_filtro_{filtro_key}")
                    else:
                        valor_filtro = ""
                        st.info("Operador não requer valor")

                col_add, col_conector = st.columns([1,1])
                with col_add:
                    if st.button("➕ Adicionar Filtro", key=f"add_filtro_{seed}", use_container_width=True):
                        if campo_filtro:
                            if operador_filtro == "BETWEEN":
                                if "|" in valor_filtro and all(v.strip() for v in valor_filtro.split("|")):
                                    st.session_state[f"filtros_{seed}"].append({"campo":campo_filtro,"operador":operador_filtro,"valor":valor_filtro.strip(),"conector":"AND"})
                                    st.session_state[f"filtro_counter_{seed}"] += 1
                                    st.rerun()
                                else:
                                    st.warning("Preencha os dois valores para BETWEEN!")
                            elif operador_filtro in ["IS NULL","IS NOT NULL"] or valor_filtro.strip():
                                st.session_state[f"filtros_{seed}"].append({"campo":campo_filtro,"operador":operador_filtro,"valor":valor_filtro.strip(),"conector":"AND"})
                                st.session_state[f"filtro_counter_{seed}"] += 1
                                st.rerun()
                            else:
                                st.warning("Preencha o valor do filtro!")
                        else:
                            st.warning("Selecione um campo!")
                with col_conector:
                    if len(st.session_state[f"filtros_{seed}"]) > 0:
                        st.info(f"✓ {len(st.session_state[f'filtros_{seed}'])} filtro(s) adicionado(s)")

            # Exibe filtros ativos
            if st.session_state[f"filtros_{seed}"]:
                st.markdown("**Filtros Ativos:**")
                for idx, filtro in enumerate(st.session_state[f"filtros_{seed}"]):
                    col_info, col_conec, col_del = st.columns([4,1,1])
                    with col_info:
                        if filtro["operador"] in ["IS NULL","IS NOT NULL"]:
                            desc_filtro = f"`{filtro['campo']}` **{filtro['operador']}**"
                        elif filtro["operador"] == "BETWEEN":
                            valores = filtro['valor'].split("|")
                            if len(valores)==2:
                                v1,v2 = valores[0].strip(), valores[1].strip()
                                if not v1.replace('.','').replace('-','').isdigit(): v1=f"'{v1}'"
                                if not v2.replace('.','').replace('-','').isdigit(): v2=f"'{v2}'"
                                desc_filtro = f"`{filtro['campo']}` **BETWEEN** `{v1}` **AND** `{v2}`"
                            else:
                                desc_filtro = f"`{filtro['campo']}` **BETWEEN** `{filtro['valor']}`"
                        elif filtro["operador"] in ["IN","NOT IN"]:
                            desc_filtro = f"`{filtro['campo']}` **{filtro['operador']}** `({filtro['valor']})`"
                        elif filtro["operador"] in ["LIKE","NOT LIKE"]:
                            desc_filtro = f"`{filtro['campo']}` **{filtro['operador']}** `'{filtro['valor']}'`"
                        else:
                            vd = filtro['valor']
                            if not vd.replace('.','').replace('-','').isdigit(): vd=f"'{vd}'"
                            desc_filtro = f"`{filtro['campo']}` **{filtro['operador']}** `{vd}`"
                        if idx > 0:
                            st.markdown(f"**{filtro['conector']}** {desc_filtro}")
                        else:
                            st.markdown(desc_filtro)
                    with col_conec:
                        if idx < len(st.session_state[f"filtros_{seed}"]) - 1:
                            novo_conector = st.selectbox("Conector", options=["AND","OR"],
                                index=0 if st.session_state[f"filtros_{seed}"][idx+1]["conector"]=="AND" else 1,
                                key=f"conector_{idx}_{seed}", label_visibility="collapsed")
                            if novo_conector != st.session_state[f"filtros_{seed}"][idx+1]["conector"]:
                                st.session_state[f"filtros_{seed}"][idx+1]["conector"] = novo_conector
                                st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"del_filtro_{idx}_{seed}"):
                            st.session_state[f"filtros_{seed}"].pop(idx)
                            st.rerun()
                if st.button("🗑️ Limpar Todos os Filtros", key=f"limpar_filtros_{seed}"):
                    st.session_state[f"filtros_{seed}"] = []
                    st.rerun()

            st.markdown("---")

            # ORDER BY
            st.markdown("### 📊 Ordenação (ORDER BY)")
            if f"ordenacoes_{seed}" not in st.session_state:
                st.session_state[f"ordenacoes_{seed}"] = []

            todos_campos_order = [f"{tabela_pai}.{c}" for c in campos_pai_sel]
            for filha, campos in campos_por_filha.items():
                todos_campos_order += [f"{filha}.{c}" for c in campos]

            if todos_campos_order:
                col_o1, col_o2, col_o3 = st.columns([3,2,1])
                with col_o1:
                    campo_order = st.selectbox("Campo para Ordenar:", options=todos_campos_order, key=f"campo_order_{seed}")
                with col_o2:
                    direcao_order = st.selectbox("Direção:", options=["ASC","DESC"], key=f"direcao_order_{seed}")
                with col_o3:
                    st.write(""); st.write("")
                    if st.button("➕ Adicionar", key=f"add_order_{seed}", use_container_width=True):
                        st.session_state[f"ordenacoes_{seed}"].append({"campo":campo_order,"direcao":direcao_order})
                        st.rerun()

                if st.session_state[f"ordenacoes_{seed}"]:
                    st.markdown("**Ordenações Configuradas:**")
                    for idx, ordem in enumerate(st.session_state[f"ordenacoes_{seed}"]):
                        col_oa, col_ob = st.columns([5,1])
                        with col_oa:
                            prio = f"{idx+1}º - " if len(st.session_state[f"ordenacoes_{seed}"])>1 else ""
                            icone = "⬆️" if ordem['direcao']=="ASC" else "⬇️"
                            st.text(f"{prio}{icone} {ordem['campo']} ({ordem['direcao']})")
                        with col_ob:
                            if st.button("🗑️", key=f"remove_order_{idx}_{seed}"):
                                st.session_state[f"ordenacoes_{seed}"].pop(idx)
                                st.rerun()
                    if len(st.session_state[f"ordenacoes_{seed}"])>1:
                        st.caption("💡 A ordenação será aplicada na sequência mostrada acima.")
                    if st.button("🗑️ Limpar Todas as Ordenações", key=f"limpar_ordenacoes_{seed}"):
                        st.session_state[f"ordenacoes_{seed}"] = []
                        st.rerun()
            else:
                st.info("ℹ️ Selecione campos primeiro para adicionar ordenação.")

            st.markdown("---")

            # GERAÇÃO DA SQL
            if st.button("✨ GERAR MINHA SENTENÇA SQL", use_container_width=True):
                if not campos_pai_sel and not any(campos_por_filha.values()):
                    st.warning("Selecione ao menos uma coluna!")
                else:
                    colunas_select = [f"{tabela_pai}.{c}" for c in campos_pai_sel]
                    for filha, cols in campos_por_filha.items():
                        for c in cols:
                            colunas_select.append(f"{filha}.{c}")

                    if op_agregacao != "NENHUM" and 'campo_metrica' in locals() and campo_metrica:
                        map_op = {"SOMA (SUM)":"SUM","CONTAGEM (COUNT)":"COUNT","MÉDIA (AVG)":"AVG","MÁXIMO (MAX)":"MAX","MÍNIMO (MIN)":"MIN"}
                        func = map_op[op_agregacao]
                        prefixo_met = tabela_pai if campo_metrica in campos_pai_sel else ""
                        if not prefixo_met:
                            for f_filha, cs in campos_por_filha.items():
                                if campo_metrica in cs:
                                    prefixo_met = f_filha; break
                        campo_final_met = f"{func}({prefixo_met}.{campo_metrica}) AS {func}_{campo_metrica}"
                        campos_gb   = [c for c in colunas_select if not c.endswith(f".{campo_metrica}")]
                        select_final = ",\n  ".join(campos_gb + [campo_final_met])
                        group_by_sql = f"\nGROUP BY\n  " + ",\n  ".join(campos_gb)
                    else:
                        select_final = ",\n  ".join(colunas_select)
                        group_by_sql = ""

                    script = f"SELECT\n  {select_final}\nFROM {tabela_pai} (NOLOCK)"
                    for filha in tabelas_filhas:
                        # Tenta relação direta Pai → Filha
                        rel = df_relacoes[(df_relacoes["MASTERTABLE"]==tabela_pai)&(df_relacoes["CHILDTABLE"]==filha)]
                        master_usado = tabela_pai

                        # Se não encontrou, procura relação Filha → Filha
                        # (alguma tabela já adicionada que é master desta filha)
                        if rel.empty:
                            for outra_filha in tabelas_filhas:
                                if outra_filha == filha:
                                    continue
                                rel_ff = df_relacoes[(df_relacoes["MASTERTABLE"]==outra_filha)&(df_relacoes["CHILDTABLE"]==filha)]
                                if not rel_ff.empty:
                                    rel = rel_ff
                                    master_usado = outra_filha
                                    break

                        tipo = tipos_join.get(filha,"INNER")
                        if not rel.empty:
                            conds = []
                            for _, r in rel.iterrows():
                                cp_l = str(r["MASTERFIELD"]).split(",")
                                cf_l = str(r["CHILDFIELD"]).split(",")
                                for cp, cf in zip(cp_l, cf_l):
                                    conds.append(f"{master_usado}.{cp.strip()} = {filha}.{cf.strip()}")
                            script += f"\n{tipo} JOIN {filha} (NOLOCK) ON\n  " + " AND\n  ".join(conds)
                        else:
                            script += f"\n{tipo} JOIN {filha} (NOLOCK) ON\n  -- AJUSTE O JOIN: {tabela_pai}.ID = {filha}.ID"

                    if st.session_state[f"filtros_{seed}"]:
                        condicoes_where = []
                        for idx, filtro in enumerate(st.session_state[f"filtros_{seed}"]):
                            campo = filtro["campo"]; operador = filtro["operador"]; valor = filtro["valor"]
                            if operador in ["IS NULL","IS NOT NULL"]:
                                condicao = f"{campo} {operador}"
                            elif operador == "BETWEEN":
                                valores = valor.split("|")
                                if len(valores)==2:
                                    val1,val2=valores[0].strip(),valores[1].strip()
                                    if not val1.replace('.','').replace('-','').isdigit() and not val1.startswith("'"): val1=f"'{val1}'"
                                    if not val2.replace('.','').replace('-','').isdigit() and not val2.startswith("'"): val2=f"'{val2}'"
                                    condicao = f"{campo} BETWEEN {val1} AND {val2}"
                                else:
                                    condicao = f"{campo} BETWEEN {valor}"
                            elif operador in ["IN","NOT IN"]:
                                condicao = f"{campo} {operador} ({valor})"
                            elif operador in ["LIKE","NOT LIKE"]:
                                if not valor.startswith("'"): valor=f"'{valor}'"
                                condicao = f"{campo} {operador} {valor}"
                            else:
                                if valor.replace('.','').replace('-','').replace(',','').isdigit():
                                    condicao = f"{campo} {operador} {valor}"
                                else:
                                    if not valor.startswith("'"): valor=f"'{valor}'"
                                    condicao = f"{campo} {operador} {valor}"
                            if idx==0: condicoes_where.append(condicao)
                            else:      condicoes_where.append(f"{filtro['conector']} {condicao}")
                        if condicoes_where:
                            script += f"\nWHERE\n  " + "\n  ".join(condicoes_where)

                    script += group_by_sql

                    if st.session_state[f"ordenacoes_{seed}"]:
                        order_fields = [f"{o['campo']} {o['direcao']}" for o in st.session_state[f"ordenacoes_{seed}"]]
                        script += "\nORDER BY\n  " + ",\n  ".join(order_fields)

                    st.session_state.sql_gerada  = script
                    st.session_state.sql_editada = script
                    st.session_state.tabela_atual = tabela_pai

                    tem_join    = len(tabelas_filhas) > 0
                    tem_calculo = op_agregacao != "NENHUM"
                    total_campos = len(campos_pai_sel) + sum(len(cols) for cols in campos_por_filha.values())
                    adicionar_ao_historico(script, tabela_pai, total_campos, tem_join, tem_calculo)
                    arquivo_salvo = salvar_query_em_arquivo(script, tabela_pai)
                    if arquivo_salvo:
                        st.session_state.ultimo_arquivo_salvo = arquivo_salvo

            # EXIBIÇÃO DA SQL
            if "sql_editada" in st.session_state:
                st.markdown("---")
                st.markdown("### ✅ Sua Sentença SQL")
                st.markdown("""<div class="success-box">
                    ✓ <strong>Tudo pronto!</strong> Você pode editar a query abaixo antes de copiar ou baixar.<br>
                    💾 <em>Query salva automaticamente no histórico.</em>
                </div>""", unsafe_allow_html=True)

                tab_view, tab_edit = st.tabs(["👁️ Visualizar", "✏️ Editar SQL"])
                with tab_view:
                    st.code(st.session_state.sql_editada, language="sql", line_numbers=True)
                    st.caption("💡 Use o botão 📋 no canto superior direito para copiar")
                with tab_edit:
                    sql_editada = st.text_area("Editor SQL:", value=st.session_state.sql_editada,
                        height=300, key=f"editor_sql_{seed}", label_visibility="collapsed")
                    if sql_editada != st.session_state.sql_editada:
                        st.session_state.sql_editada = sql_editada
                        arquivo_salvo = atualizar_query_editada(sql_editada)
                        st.success("✓ Edição salva automaticamente!", icon="💾")
                    if st.button("💾 Salvar Edição Manualmente", key="save_edit_manual"):
                        atualizar_query_editada(sql_editada)
                        st.success("✓ Versão editada salva!")

                st.download_button("💾 Baixar .sql", st.session_state.sql_editada,
                    file_name=f"sentenca_{st.session_state.get('tabela_atual','query')}.sql",
                    use_container_width=True)

                st.markdown("---")
                st.markdown("### 👀 Pré-visualização dos Dados (Simulação)")
                if st.button("🔎 Visualizar Dados Simulados", use_container_width=True):
                    colunas_preview = extrair_colunas_select(st.session_state.sql_editada)
                    if colunas_preview:
                        df_fake = gerar_preview_fake(colunas_preview)
                        st.dataframe(df_fake, use_container_width=True)
                        st.caption("⚠️ Dados simulados apenas para visualização.")
                    else:
                        st.info("Nenhuma coluna válida encontrada para simulação.")

        else:
            st.error("⚠️ Arquivos de configuração não encontrados. Certifique-se de que **CAMPOS.xlsx**, **SISTEMAS.xlsx** e **RELACIONAMENTOS.xlsx** estão na pasta do app.")

    # ABA 3: HISTÓRICO
    with tab_historico:
        st.header("🕐 Histórico de Queries")
        inicializar_historico()

        if not st.session_state.historico_queries:
            st.info("📭 Nenhuma query gerada ainda. Vá para a aba 'Criar minha Sentença' e gere sua primeira query!")
        else:
            total_queries = len(st.session_state.historico_queries)
            favoritas     = len([q for q in st.session_state.historico_queries if q["favorito"]])
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total de Queries", total_queries)
            with col2: st.metric("Favoritas", favoritas)
            with col3:
                if st.button("🗑️ Limpar Histórico"):
                    st.session_state.historico_queries = []
                    st.rerun()

            st.markdown("---")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                mostrar_fav = st.checkbox("⭐ Mostrar apenas favoritas")
            with col_f2:
                ordenar_por = st.selectbox("Ordenar por", ["Mais recentes","Mais antigas","Tabela (A-Z)"])

            queries_exibir = st.session_state.historico_queries.copy()
            if mostrar_fav:
                queries_exibir = [q for q in queries_exibir if q["favorito"]]
            if ordenar_por == "Mais antigas":
                queries_exibir = list(reversed(queries_exibir))
            elif ordenar_por == "Tabela (A-Z)":
                queries_exibir = sorted(queries_exibir, key=lambda x: x["tabela"])

            if not queries_exibir:
                st.info("Nenhuma query encontrada com os filtros aplicados.")
            else:
                for idx, query in enumerate(queries_exibir):
                    idx_real = st.session_state.historico_queries.index(query)
                    with st.container():
                        col_titulo, _ = st.columns([4,1])
                        with col_titulo:
                            titulo = ("⭐ " if query['favorito'] else "") + ("✏️ " if query.get('editada') else "") + query['descricao']
                            st.markdown(f"**{titulo}**")
                        info_text = f"{query['timestamp_str']} • Tabela: {query['tabela']} • {query['campos_count']} campos"
                        if query.get('editada'): info_text += " • 🟢 Editada"
                        st.caption(info_text)

                        col_b1, col_b2, col_b3, col_b4 = st.columns([1,1,1,4])
                        with col_b1:
                            if st.button("📋 Copiar", key=f"copy_{idx_real}"):
                                st.session_state[f"show_sql_{idx_real}"] = True
                        with col_b2:
                            if st.button("👁️ Ver SQL", key=f"view_{idx_real}"):
                                st.session_state[f"show_sql_{idx_real}"] = not st.session_state.get(f"show_sql_{idx_real}", False)
                        with col_b3:
                            st.download_button("💾 Baixar", query["sql"],
                                file_name=f"query_{query['tabela']}_{query['timestamp'].strftime('%Y%m%d_%H%M%S')}.sql",
                                key=f"download_{idx_real}")
                        with col_b4:
                            emoji_fav = "★" if query["favorito"] else "☆"
                            if st.button(f"{emoji_fav} Favoritar", key=f"fav_{idx_real}"):
                                toggle_favorito(idx_real)
                                st.rerun()

                        if st.session_state.get(f"show_sql_{idx_real}", False):
                            st.code(query["sql"], language="sql", line_numbers=True)
                        st.divider()

            st.markdown("""<div class="info-box">
                💡 <strong>Dicas:</strong><br>
                • Clique em <strong>📋 Copiar</strong> para exibir a SQL e usar o botão nativo de copiar<br>
                • Use <strong>☆/★ Favoritar</strong> para marcar queries importantes<br>
                • Queries editadas são marcadas com <strong>✏️</strong><br>
                • O histórico mantém até 10 queries não-favoritas por sessão
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:gray;'>Desenvolvido por Claudio Ximenes | "
        "<a href='mailto:csenemix@gmail.com' style='color:#ff4b4b;text-decoration:none;'>Suporte</a></div>",
        unsafe_allow_html=True
    )
