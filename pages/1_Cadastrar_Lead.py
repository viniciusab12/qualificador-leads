import sqlite3

import streamlit as st

from src import criterios
from src.ai_analyzer import analisar_lead
from src.database import criar_tabela, salvar_lead
from src.models import Lead
from src.scoring import calcular_pontuacao

st.set_page_config(page_title="Cadastrar Lead", layout="centered")

# Garante que a tabela existe antes de qualquer coisa
criar_tabela()

# Opções das listas, puxadas das regras de pontuação
SEGMENTOS = criterios.SEGMENTOS_ALVO + criterios.SEGMENTOS_SECUNDARIOS + ["Outro"]
NECESSIDADES = criterios.SERVICOS_OFERECIDOS + ["Outro"]
PRAZOS = list(criterios.PONTOS_PRAZO.keys())


def validar(empresa, contato):
    """Confere os campos obrigatórios. Devolve uma lista de erros."""
    erros = []
    if not empresa.strip():
        erros.append("Informe o nome da empresa.")
    if not contato.strip():
        erros.append("Informe o nome do contato.")
    return erros


st.title("Cadastrar lead")
st.write("Preencha os dados do potencial cliente. A nota é calculada automaticamente.")

with st.form("form_lead"):
    coluna1, coluna2 = st.columns(2)

    with coluna1:
        empresa = st.text_input("Empresa *")
        segmento = st.selectbox("Segmento *", SEGMENTOS)
        orcamento = st.number_input(
            "Orçamento (R$) *",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            help="Digite só números, sem ponto de milhar. Ex.: 12000",
        )

    with coluna2:
        contato = st.text_input("Nome do contato *")
        necessidade = st.selectbox("Necessidade *", NECESSIDADES)
        prazo = st.selectbox("Prazo para começar *", PRAZOS)

    descricao = st.text_area(
        "Descrição da necessidade",
        placeholder="Ex.: site com cardápio, fotos dos produtos e botão de pedido pelo WhatsApp",
    )
    contato_decisor = st.checkbox("O contato é quem decide a compra")

    enviado = st.form_submit_button("Cadastrar e qualificar", type="primary")

if enviado:
    erros = validar(empresa, contato)

    if erros:
        for erro in erros:
            st.error(erro)
    else:
        lead = Lead(
            empresa=empresa.strip(),
            contato=contato.strip(),
            segmento=segmento,
            necessidade=necessidade,
            descricao=descricao.strip(),
            orcamento=orcamento,
            prazo=prazo,
            contato_decisor=contato_decisor,
        )

        # 1. Nota objetiva, calculada pelas regras
        resultado = calcular_pontuacao(lead)
        lead.nota = resultado["nota"]
        lead.classificacao = resultado["classificacao"]
        lead.justificativa = resultado["justificativa"]

        # 2. Análise complementar da IA (não altera a nota)
        with st.spinner("Gerando a análise da IA..."):
            analise, aviso_ia = analisar_lead(lead)
        lead.analise_ia = analise

        # 3. Salva no banco
        try:
            novo_id = salvar_lead(lead)
        except sqlite3.Error as erro:
            st.error(f"Não foi possível salvar o lead. Detalhe: {erro}")
        else:
            st.success(f"Lead #{novo_id} cadastrado com sucesso.")

            coluna_nota, coluna_classe = st.columns(2)
            coluna_nota.metric("Nota", f"{lead.nota}/100")
            coluna_classe.metric("Classificação", lead.classificacao)

            st.subheader("Justificativa da nota")
            st.text(lead.justificativa)

            st.subheader("Análise da IA")
            if aviso_ia:
                st.warning(aviso_ia)
            if lead.analise_ia:
                st.info(lead.analise_ia)
            st.caption(
                "A análise da IA é um complemento. A nota vem apenas das regras de pontuação."
            )