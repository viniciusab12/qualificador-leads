import streamlit as st

st.set_page_config(page_title="Qualificador de Leads", layout="wide")

pagina = st.navigation(
    [
        st.Page("inicio.py", title="Início", icon=":material/home:", default=True),
        st.Page("pages/1_Cadastrar_Lead.py", title="Cadastrar lead", icon=":material/person_add:"),
        st.Page("pages/2_Leads.py", title="Leads", icon=":material/list:"),
        st.Page("pages/3_Dashboard.py", title="Dashboard", icon=":material/bar_chart:"),
    ]
)
pagina.run()