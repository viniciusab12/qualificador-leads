import html

import streamlit as st

from scripts.gerar_dados_ficticios import popular_banco
from src.auth import restaurar_sessao, sair, usuario_atual
from src.cookies import atualizar_cookie
from src.database import criar_tabela, listar_leads
from src.estilo import aplicar_estilo

st.set_page_config(
    page_title="Termo · Qualificador de leads",
    page_icon=":material/thermostat:",
    layout="wide",
)


@st.cache_resource
def preparar_banco():
    """Cria a tabela de demonstração e, se estiver vazia, carrega os leads fictícios."""
    criar_tabela()
    if not listar_leads():
        popular_banco()


preparar_banco()
aplicar_estilo()
st.logo("assets/logo.svg", icon_image="assets/icone.svg", size="large")

# Login com e-mail lembrado: tenta entrar de novo com o token salvo no cookie
restaurar_sessao(st.context.cookies)
usuario = usuario_atual()
atualizar_cookie()

# A página Entrar fica sempre registrada, para o login funcionar na primeira tentativa.
# Para quem já entrou, ela só some do menu (CSS abaixo) e redireciona ao Início.
paginas = [
    st.Page("inicio.py", title="Início", icon=":material/home:", default=True),
    st.Page("pages/1_Cadastrar_Lead.py", title="Cadastrar lead", icon=":material/person_add:"),
    st.Page("pages/2_Leads.py", title="Leads", icon=":material/list:"),
    st.Page("pages/3_Dashboard.py", title="Dashboard", icon=":material/bar_chart:"),
    st.Page("pages/0_Entrar.py", title="Entrar", icon=":material/login:", url_path="entrar"),
]

pagina = st.navigation(paginas)

if usuario:
    st.html('<style>[data-testid="stSidebarNav"] a[href$="/entrar"] { display: none; }</style>')

PROVEDORES = {"google": "Google", "email": "E-mail e senha"}

if usuario:
    inicial = (usuario["nome"] or usuario["email"])[:1].upper()
    linha_email = ""
    if usuario["nome"] != usuario["email"]:
        linha_email = f'<div class="conta-email">{html.escape(usuario["email"])}</div>'
    st.sidebar.markdown(
        '<div class="conta-usuario">'
        f'<div class="conta-avatar">{html.escape(inicial)}</div>'
        '<div class="conta-dados">'
        '<div class="conta-rotulo">Conectado</div>'
        f'<div class="conta-nome">{html.escape(usuario["nome"])}</div>'
        f"{linha_email}"
        f'<div class="conta-provedor">via {PROVEDORES.get(usuario["provedor"], "")}</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.sidebar.button("Sair", on_click=sair, icon=":material/logout:", width="stretch")
else:
    st.sidebar.caption("Modo demonstração, com dados fictícios.")

st.sidebar.caption("Não digite dados reais: o texto dos leads é enviado à IA do Google.")

pagina.run()
