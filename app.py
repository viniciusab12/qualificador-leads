import streamlit as st

from scripts.gerar_dados_ficticios import popular_banco
from src.database import criar_tabela, listar_leads
from src.estilo import aplicar_estilo

st.set_page_config(
    page_title="Termo · Qualificador de leads",
    page_icon=":material/thermostat:",
    layout="wide",
)


@st.cache_resource
def preparar_banco():
    """Cria a tabela e, se o banco estiver vazio, carrega os leads de demonstração."""
    criar_tabela()
    if not listar_leads():
        popular_banco()


preparar_banco()
aplicar_estilo()
st.logo("assets/logo.svg", icon_image="assets/icone.svg", size="large")

st.sidebar.caption(
    "Demonstração com dados fictícios. Não digite dados reais: "
    "o texto dos leads é enviado à IA do Google."
)

pagina = st.navigation(
    [
        st.Page("inicio.py", title="Início", icon=":material/home:", default=True),
        st.Page("pages/1_Cadastrar_Lead.py", title="Cadastrar lead", icon=":material/person_add:"),
        st.Page("pages/2_Leads.py", title="Leads", icon=":material/list:"),
        st.Page("pages/3_Dashboard.py", title="Dashboard", icon=":material/bar_chart:"),
    ]
)
pagina.run()