from datetime import date

import streamlit as st

from src.auth import sair, usuario_atual
from src.componentes import mostrar_erro, texto_seguro
from src.dados import ErroBanco, excluir_conta, listar_leads
from src.metricas import leads_para_csv

PROVEDORES = {"google": "Google", "github": "GitHub", "email": "E-mail e senha"}
PALAVRA_CONFIRMACAO = "EXCLUIR"

st.title("Minha conta")

usuario = usuario_atual()
if usuario is None:
    st.info("Entre na sua conta para ver esta página.")
    st.page_link("pages/0_Entrar.py", label="Entrar ou criar conta", icon=":material/login:")
    st.stop()

st.write(f"**Conta:** {texto_seguro(usuario['nome'])}")
if usuario["email"] and usuario["email"] != usuario["nome"]:
    st.write(f"**E-mail:** {texto_seguro(usuario['email'])}")
st.write(f"**Forma de entrar:** {PROVEDORES.get(usuario['provedor'], '')}")

# ---------- Exportar ----------
st.subheader("Baixar os meus dados")
st.write("Todos os seus leads em um arquivo CSV, que abre no Excel.")
try:
    leads = listar_leads()
except ErroBanco as erro:
    mostrar_erro("Não foi possível carregar os leads agora. Tente de novo em alguns instantes.", erro)
    st.stop()

st.download_button(
    f"Baixar {len(leads)} lead(s) em CSV",
    data=leads_para_csv(leads),
    file_name=f"meus_leads_termo_{date.today().isoformat()}.csv",
    mime="text/csv",
    icon=":material/download:",
)

# ---------- Excluir conta ----------
st.subheader("Excluir conta")
texto_exclusao = (
    "Apaga todos os seus leads, anotações e regras de pontuação. Esta ação não pode ser desfeita."
)
if usuario["provedor"] == "email":
    texto_exclusao += " O seu cadastro de e-mail e senha também é apagado."
else:
    texto_exclusao += (
        f" A sua conta {PROVEDORES[usuario['provedor']]} continua existindo: "
        "o Termo só apaga os dados que guardou."
    )
st.warning(texto_exclusao)

confirmacao = st.text_input(f"Para confirmar, digite {PALAVRA_CONFIRMACAO}")
if st.button(
    "Excluir minha conta",
    type="primary",
    disabled=confirmacao.strip() != PALAVRA_CONFIRMACAO,
):
    try:
        apagados = excluir_conta()
    except ErroBanco as erro:
        mostrar_erro("Não foi possível concluir a exclusão agora. Tente de novo em alguns instantes.", erro)
    else:
        sair()
        st.success(f"Conta excluída. {apagados} lead(s) apagado(s).")
        st.rerun()
