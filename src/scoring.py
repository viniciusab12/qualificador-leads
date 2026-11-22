"""Cálculo objetivo da pontuação dos leads, a partir de src/criterios.py."""

from src import criterios


def formatar_reais(valor):
    """Formata um número como dinheiro: 3500 -> 'R$ 3.500'."""
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


def pontuar_orcamento(orcamento):
    """Devolve (pontos, explicação) para o orçamento."""
    for valor_minimo, pontos in criterios.FAIXAS_ORCAMENTO:
        if orcamento >= valor_minimo:
            return pontos, f"orçamento de {formatar_reais(orcamento)}"
    return 0, "orçamento não informado"


def pontuar_prazo(prazo):
    """Devolve (pontos, explicação) para o prazo."""
    pontos = criterios.PONTOS_PRAZO.get(prazo, 0)
    return pontos, f"prazo: {prazo}"


def pontuar_segmento(segmento):
    """Devolve (pontos, explicação) para o segmento."""
    if segmento in criterios.SEGMENTOS_ALVO:
        return criterios.PONTOS_SEGMENTO_ALVO, f"{segmento} é segmento-alvo"
    elif segmento in criterios.SEGMENTOS_SECUNDARIOS:
        return criterios.PONTOS_SEGMENTO_SECUNDARIO, f"{segmento} é segmento secundário"
    else:
        return 0, f"{segmento} está fora do foco"


def pontuar_necessidade(necessidade, descricao):
    """Devolve (pontos, explicação) para a necessidade e a descrição."""
    pontos = 0
    explicacoes = []

    if necessidade in criterios.SERVICOS_OFERECIDOS:
        pontos += criterios.PONTOS_SERVICO_OFERECIDO
        explicacoes.append(f"{necessidade} é um serviço oferecido")
    else:
        explicacoes.append(f"{necessidade} está fora do portfólio")

    if len(descricao.strip()) >= criterios.TAMANHO_MINIMO_DESCRICAO:
        pontos += criterios.PONTOS_DESCRICAO_CLARA
        explicacoes.append("descrição detalhada")
    else:
        explicacoes.append("descrição curta")

    return pontos, "; ".join(explicacoes)


def pontuar_decisor(contato_decisor):
    """Devolve (pontos, explicação) para o contato ser ou não decisor."""
    if contato_decisor:
        return criterios.PONTOS_DECISOR, "contato é quem decide a compra"
    return criterios.PONTOS_NAO_DECISOR, "contato não é quem decide a compra"


def classificar(nota):
    """Transforma a nota em Quente, Morno ou Frio."""
    if nota >= criterios.LIMITE_QUENTE:
        return "Quente"
    elif nota >= criterios.LIMITE_MORNO:
        return "Morno"
    else:
        return "Frio"


def calcular_pontuacao(lead):
    """Calcula nota, classificação e justificativa de um lead."""
    pontos_orc, texto_orc = pontuar_orcamento(lead.orcamento)
    pontos_prazo, texto_prazo = pontuar_prazo(lead.prazo)
    pontos_seg, texto_seg = pontuar_segmento(lead.segmento)
    pontos_nec, texto_nec = pontuar_necessidade(lead.necessidade, lead.descricao)
    pontos_dec, texto_dec = pontuar_decisor(lead.contato_decisor)

    nota = pontos_orc + pontos_prazo + pontos_seg + pontos_nec + pontos_dec

    justificativa = "\n".join([
        f"Orçamento: {pontos_orc}/{criterios.MAX_ORCAMENTO} ({texto_orc})",
        f"Prazo: {pontos_prazo}/{criterios.MAX_PRAZO} ({texto_prazo})",
        f"Segmento: {pontos_seg}/{criterios.MAX_SEGMENTO} ({texto_seg})",
        f"Necessidade: {pontos_nec}/{criterios.MAX_NECESSIDADE} ({texto_nec})",
        f"Decisor: {pontos_dec}/{criterios.MAX_DECISOR} ({texto_dec})",
    ])

    return {
        "nota": nota,
        "classificacao": classificar(nota),
        "justificativa": justificativa,
    }