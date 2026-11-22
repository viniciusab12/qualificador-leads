import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import criar_tabela, listar_leads
from src.metricas import (
    calcular_indicadores,
    contar_por_classificacao,
    contar_por_segmento,
    contar_por_status,
    conversao_por_classificacao,
    leads_para_tabela,
    leads_por_semana,
    nota_media_por_segmento,
)

st.set_page_config(page_title="Dashboard", layout="wide")
criar_tabela()

COR = "#1c5cab"  # mesma cor principal do tema
ROTULOS = {
    "classificacao": "Classificação",
    "quantidade": "Leads",
    "status": "Status",
    "segmento": "Segmento",
    "nota_media": "Nota média",
    "taxa_conversao": "Conversão (%)",
    "semana": "Semana",
}
PERIODOS = {
    "Últimos 30 dias": 30,
    "Últimos 60 dias": 60,
    "Últimos 90 dias": 90,
    "Todo o período": None,
}


def formatar_decimal(numero):
    """12.5 -> '12,5' (padrão brasileiro)."""
    return f"{numero:.1f}".replace(".", ",")


def ajustar_grafico(figura, barras=True):
    """Aplica o mesmo visual limpo a todos os gráficos."""
    figura.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None,
        height=320,
    )
    if barras:
        figura.update_traces(marker_color=COR, marker_cornerradius=4, textposition="outside")
    return figura


def mostrar_grafico(titulo, figura, dados):
    """Exibe o título, o gráfico e a tabela com os dados do gráfico."""
    st.subheader(titulo)
    st.plotly_chart(figura, width="stretch")
    with st.expander("Ver dados"):
        st.dataframe(dados.rename(columns=ROTULOS), hide_index=True)


st.title("Dashboard")

tabela = leads_para_tabela(listar_leads())

if tabela.empty:
    st.info("Ainda não há leads para analisar.")
    st.page_link("pages/1_Cadastrar_Lead.py", label="Cadastrar um lead", icon=":material/add:")
    st.stop()

# ---------- Filtro de período ----------
periodo = st.radio("Período", list(PERIODOS), index=3, horizontal=True)
dias = PERIODOS[periodo]
if dias is not None:
    limite = pd.Timestamp.now() - pd.Timedelta(days=dias)
    tabela = tabela[tabela["criado_em"] >= limite]

if tabela.empty:
    st.warning("Nenhum lead cadastrado nesse período.")
    st.stop()

# ---------- Indicadores ----------
indicadores = calcular_indicadores(tabela)
taxa = indicadores["taxa_conversao"]

coluna1, coluna2, coluna3, coluna4 = st.columns(4)
coluna1.metric("Leads", indicadores["total"])
coluna2.metric("Leads quentes", f"{formatar_decimal(indicadores['percentual_quentes'])}%")
coluna3.metric("Nota média", f"{formatar_decimal(indicadores['nota_media'])}/100")
coluna4.metric(
    "Taxa de conversão",
    f"{formatar_decimal(taxa)}%" if taxa is not None else "Sem dados",
    help="Leads ganhos divididos pelos leads fechados (ganhos + perdidos).",
)

st.divider()

# ---------- Gráficos ----------
esquerda, direita = st.columns(2)

with esquerda:
    dados = contar_por_classificacao(tabela)
    figura = px.bar(dados, x="classificacao", y="quantidade", text="quantidade", labels=ROTULOS)
    mostrar_grafico("Leads por classificação", ajustar_grafico(figura), dados)

with direita:
    dados = conversao_por_classificacao(tabela)
    figura = px.bar(dados, x="classificacao", y="taxa_conversao", text="taxa_conversao", labels=ROTULOS)
    figura.update_traces(texttemplate="%{text:.0f}%")
    figura.update_yaxes(range=[0, 110], ticksuffix="%")
    mostrar_grafico("Conversão por classificação", ajustar_grafico(figura), dados)

with esquerda:
    dados = contar_por_status(tabela)
    figura = px.bar(
        dados, x="quantidade", y="status", orientation="h", text="quantidade", labels=ROTULOS
    )
    figura.update_yaxes(autorange="reversed")  # mantém a ordem do funil, de cima para baixo
    mostrar_grafico("Leads por etapa do funil", ajustar_grafico(figura), dados)

with direita:
    dados = contar_por_segmento(tabela)
    figura = px.bar(
        dados, x="quantidade", y="segmento", orientation="h", text="quantidade", labels=ROTULOS
    )
    figura.update_yaxes(autorange="reversed")  # maior no topo
    mostrar_grafico("Leads por segmento", ajustar_grafico(figura), dados)

with esquerda:
    dados = nota_media_por_segmento(tabela)
    figura = px.bar(
        dados, x="nota_media", y="segmento", orientation="h", text="nota_media", labels=ROTULOS
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(range=[0, 100])
    mostrar_grafico("Nota média por segmento", ajustar_grafico(figura), dados)

with direita:
    dados = leads_por_semana(tabela)
    figura = px.line(dados, x="semana", y="quantidade", markers=True, labels=ROTULOS)
    figura.update_traces(line=dict(color=COR, width=2), marker=dict(color=COR, size=8))
    figura.update_yaxes(rangemode="tozero")
    tabela_semanas = dados.assign(semana=dados["semana"].dt.strftime("%d/%m/%Y"))
    mostrar_grafico("Leads cadastrados por semana", ajustar_grafico(figura, barras=False), tabela_semanas)