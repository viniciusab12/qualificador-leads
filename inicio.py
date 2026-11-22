import pandas as pd
import streamlit as st

from src import criterios
from src.componentes import banner
from src.database import criar_tabela, listar_leads

criar_tabela()

banner(
    titulo="Termo",
    texto=(
        "Cadastre potenciais clientes e receba uma nota de 0 a 100, com a classificação "
        "em quente, morno ou frio e a justificativa de cada ponto."
    ),
    rotulo="Qualificador de leads · Python + IA",
)

# Resumo rápido dos leads cadastrados
leads = listar_leads()
quentes = [lead for lead in leads if lead.classificacao == "Quente"]

coluna1, coluna2 = st.columns(2)
coluna1.metric("Leads cadastrados", len(leads))
coluna2.metric("Leads quentes", len(quentes))

st.page_link("pages/1_Cadastrar_Lead.py", label="Cadastrar um novo lead", icon=":material/add:")

st.subheader("Como a nota é calculada")
st.write("A nota segue regras fixas. Os mesmos dados sempre geram a mesma nota.")

tabela_criterios = pd.DataFrame(
    {
        "Critério": ["Orçamento", "Prazo", "Segmento", "Necessidade", "Contato decisor"],
        "Pontos máximos": [
            criterios.MAX_ORCAMENTO,
            criterios.MAX_PRAZO,
            criterios.MAX_SEGMENTO,
            criterios.MAX_NECESSIDADE,
            criterios.MAX_DECISOR,
        ],
    }
)
st.dataframe(tabela_criterios, hide_index=True)

st.write(
    f"**Quente:** {criterios.LIMITE_QUENTE} pontos ou mais · "
    f"**Morno:** de {criterios.LIMITE_MORNO} a {criterios.LIMITE_QUENTE - 1} · "
    f"**Frio:** abaixo de {criterios.LIMITE_MORNO}"
)
st.caption(
    "A IA (Gemini) complementa a análise com resumo, riscos e próxima ação, "
    "mas não altera a nota."
)