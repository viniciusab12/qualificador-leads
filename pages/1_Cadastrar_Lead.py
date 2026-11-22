import streamlit as st

from src import criterios
from src.ai_analyzer import analisar_lead
from src.componentes import mostrar_erro, mostrar_selo, texto_seguro_com_linhas
from src.dados import (
    LIMITE_IA_DEMO,
    ErroBanco,
    aviso_limite_ia,
    modo_demonstracao,
    pode_usar_ia,
    pontuar,
    registrar_uso_ia,
    salvar_lead,
)
from src.models import Lead

# Opções das listas, puxadas das regras de pontuação
SEGMENTOS = criterios.SEGMENTOS_DISPONIVEIS
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

if modo_demonstracao():
    st.info(
        "Modo demonstração: o lead fica só nesta sessão e some quando você fecha a aba. "
        f"Até {LIMITE_IA_DEMO} cadastros recebem a análise real da IA. "
        "Entre na sua conta para guardar os seus próprios leads."
    )

with st.form("form_lead"):
    coluna1, coluna2 = st.columns(2)

    with coluna1:
        empresa = st.text_input("Empresa *", max_chars=100)
        segmento = st.selectbox("Segmento *", SEGMENTOS)
        orcamento = st.number_input(
            "Orçamento (R$) *",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            help="Digite só números, sem ponto de milhar. Ex.: 12000",
        )

    with coluna2:
        contato = st.text_input("Nome do contato *", max_chars=100)
        necessidade = st.selectbox("Necessidade *", NECESSIDADES)
        prazo = st.selectbox("Prazo para começar *", PRAZOS)

    descricao = st.text_area(
        "Descrição da necessidade",
        max_chars=1000,
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

        # 1. Nota objetiva, calculada pelas regras da conta (página Critérios)
        pontuar(lead)

        # 2. Análise complementar da IA (não altera a nota)
        permitir_ia = pode_usar_ia()
        with st.spinner("Gerando a análise da IA..."):
            analise, aviso_ia = analisar_lead(
                lead, permitir_ia=permitir_ia, aviso_limite=aviso_limite_ia()
            )
        if permitir_ia:
            registrar_uso_ia()
        lead.analise_ia = analise

        # 3. Salva no banco
        try:
            novo_id = salvar_lead(lead)
        except ErroBanco as erro:
            mostrar_erro("Não foi possível salvar o lead agora. Tente de novo em alguns instantes.", erro)
        else:
            st.success(f"Lead #{novo_id} cadastrado com sucesso.")

            coluna_nota, coluna_classe = st.columns(2)
            coluna_nota.metric("Nota", f"{lead.nota}/100")
            with coluna_classe:
                mostrar_selo(lead.classificacao)

            st.subheader("Justificativa da nota")
            st.text(lead.justificativa)

            st.subheader("Análise da IA")
            if aviso_ia:
                st.warning(aviso_ia)
            if lead.analise_ia:
                st.info(texto_seguro_com_linhas(lead.analise_ia))
            st.caption(
                "A análise da IA é um complemento. A nota vem apenas das regras de pontuação."
            )