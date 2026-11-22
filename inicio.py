from datetime import date

import pandas as pd
import streamlit as st

from src import criterios
from src.componentes import banner, mostrar_erro, texto_seguro
from src.auth import usuario_atual
from src.dados import ErroBanco, buscar_criterios, leads_para_contatar, listar_leads


banner(
    titulo="Termo",
    texto=(
        "Cadastre potenciais clientes e receba uma nota de 0 a 100, com a classificação "
        "em quente, morno ou frio e a justificativa de cada ponto."
    ),
    rotulo="Qualificador de leads · Python + IA",
)

usuario = usuario_atual()
if usuario:
    st.write(f"Olá, **{texto_seguro(usuario['nome'])}**. Estes são os números dos seus leads.")
else:
    st.write("Você está no modo demonstração, com dados fictícios. Entre para usar com os seus próprios leads.")
    st.page_link("pages/0_Entrar.py", label="Entrar ou criar conta", icon=":material/login:")

# Resumo rápido dos leads cadastrados
try:
    leads = listar_leads()
except ErroBanco as erro:
    mostrar_erro("Não foi possível carregar os leads agora. Tente de novo em alguns instantes. Se continuar, recarregue a página.", erro)
    st.stop()
quentes = [lead for lead in leads if lead.classificacao == "Quente"]

coluna1, coluna2 = st.columns(2)
coluna1.metric("Leads cadastrados", len(leads))
coluna2.metric("Leads quentes", len(quentes))

st.page_link("pages/1_Cadastrar_Lead.py", label="Cadastrar um novo lead", icon=":material/add:")

# ---------- Contatos do dia ----------
para_contatar = leads_para_contatar(leads)
st.subheader("Para contatar hoje")
if para_contatar:
    hoje = date.today().isoformat()
    tabela_contatos = pd.DataFrame(
        {
            "Lead": [f"#{lead.id} · {lead.empresa}" for lead in para_contatar],
            "Contato": [lead.contato for lead in para_contatar],
            "Classificação": [lead.classificacao for lead in para_contatar],
            "Status": [lead.status for lead in para_contatar],
            "Data marcada": [
                date.fromisoformat(lead.proximo_contato).strftime("%d/%m/%Y")
                + (" (atrasado)" if lead.proximo_contato < hoje else "")
                for lead in para_contatar
            ],
        }
    )
    st.dataframe(tabela_contatos, hide_index=True, width="stretch")
    st.page_link("pages/2_Leads.py", label="Abrir a página Leads", icon=":material/list:")
else:
    st.caption("Nenhum contato marcado para hoje. Marque o próximo contato de cada lead na página Leads.")

# ---------- Regras ----------
try:
    regras = buscar_criterios()
except ErroBanco as erro:
    mostrar_erro("Não foi possível carregar as regras de pontuação agora.", erro)
    st.stop()

st.subheader("Como a nota é calculada")
st.write("A nota segue regras fixas. Os mesmos dados sempre geram a mesma nota.")

tabela_criterios = pd.DataFrame(
    {
        "Critério": list(criterios.NOMES_CRITERIOS.values()),
        "Pontos máximos": [regras["pesos"][chave] for chave in criterios.NOMES_CRITERIOS],
    }
)
st.dataframe(tabela_criterios, hide_index=True)

st.write(
    f"**Quente:** {regras['limite_quente']} pontos ou mais · "
    f"**Morno:** de {regras['limite_morno']} a {regras['limite_quente'] - 1} · "
    f"**Frio:** abaixo de {regras['limite_morno']}"
)
if regras["versao"]:
    st.caption(f"Regras personalizadas, versão {regras['versao']}.")
st.page_link("pages/4_Criterios.py", label="Ajustar os critérios", icon=":material/tune:")
st.caption(
    "A IA (Gemini) complementa a análise com resumo, riscos e próxima ação, "
    "mas não altera a nota."
)