"""Cálculo objetivo da pontuação dos leads.

As regras vêm de src/criterios.py. Cada conta pode ter pesos próprios: o peso
é a pontuação máxima do critério. Os pontos de cada faixa crescem ou diminuem
na mesma proporção do peso. Exemplo: com o peso de Orçamento em 40 (o padrão
é 30), a faixa que valia 15 de 30 passa a valer 20 de 40.

Mesmos dados + mesma versão das regras = mesma nota, sempre. A IA não participa.
"""

from src import criterios


def formatar_reais(valor):
    """Formata um número como dinheiro: 3500 -> 'R$ 3.500'."""
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


def _regras(config):
    """Usa as regras padrão quando nenhuma configuração é informada."""
    return criterios.completar_criterios(config)


def _escalar(pontos_padrao, criterio, config):
    """Converte os pontos de uma faixa do peso padrão para o peso da conta."""
    peso = config["pesos"][criterio]
    peso_padrao = criterios.PESOS_PADRAO[criterio]
    return round(pontos_padrao * peso / peso_padrao)


def pontuar_orcamento(orcamento, config=None):
    """Devolve (pontos, explicação) para o orçamento."""
    config = _regras(config)
    for valor_minimo, pontos in criterios.FAIXAS_ORCAMENTO:
        if orcamento >= valor_minimo:
            return _escalar(pontos, "orcamento", config), f"orçamento de {formatar_reais(orcamento)}"
    return 0, "orçamento não informado"


def pontuar_prazo(prazo, config=None):
    """Devolve (pontos, explicação) para o prazo."""
    config = _regras(config)
    pontos = criterios.PONTOS_PRAZO.get(prazo, 0)
    return _escalar(pontos, "prazo", config), f"prazo: {prazo}"


def pontuar_segmento(segmento, config=None):
    """Devolve (pontos, explicação) para o segmento."""
    config = _regras(config)
    if segmento in config["segmentos_alvo"]:
        return _escalar(criterios.PONTOS_SEGMENTO_ALVO, "segmento", config), f"{segmento} é segmento-alvo"
    if segmento in config["segmentos_secundarios"]:
        pontos = _escalar(criterios.PONTOS_SEGMENTO_SECUNDARIO, "segmento", config)
        return pontos, f"{segmento} é segmento secundário"
    return 0, f"{segmento} está fora do foco"


def pontuar_necessidade(necessidade, descricao, config=None):
    """Devolve (pontos, explicação) para a necessidade e a descrição."""
    config = _regras(config)
    pontos = 0
    explicacoes = []

    if necessidade in criterios.SERVICOS_OFERECIDOS:
        pontos += _escalar(criterios.PONTOS_SERVICO_OFERECIDO, "necessidade", config)
        explicacoes.append(f"{necessidade} é um serviço oferecido")
    else:
        explicacoes.append(f"{necessidade} está fora do portfólio")

    if len(descricao.strip()) >= config["tamanho_minimo_descricao"]:
        pontos += _escalar(criterios.PONTOS_DESCRICAO_CLARA, "necessidade", config)
        explicacoes.append("descrição detalhada")
    else:
        explicacoes.append("descrição curta")

    # O arredondamento das duas partes nunca pode passar do peso do critério
    pontos = min(pontos, config["pesos"]["necessidade"])
    return pontos, "; ".join(explicacoes)


def pontuar_decisor(contato_decisor, config=None):
    """Devolve (pontos, explicação) para o contato ser ou não decisor."""
    config = _regras(config)
    if contato_decisor:
        return _escalar(criterios.PONTOS_DECISOR, "decisor", config), "contato é quem decide a compra"
    return _escalar(criterios.PONTOS_NAO_DECISOR, "decisor", config), "contato não é quem decide a compra"


def classificar(nota, config=None):
    """Transforma a nota em Quente, Morno ou Frio."""
    config = _regras(config)
    if nota >= config["limite_quente"]:
        return "Quente"
    if nota >= config["limite_morno"]:
        return "Morno"
    return "Frio"


def calcular_pontuacao(lead, config=None):
    """Calcula nota, classificação e justificativa de um lead.

    config: regras da conta (de src/criterios.py). Sem config, usa as regras padrão.
    """
    config = _regras(config)
    pesos = config["pesos"]

    pontos_orc, texto_orc = pontuar_orcamento(lead.orcamento, config)
    pontos_prazo, texto_prazo = pontuar_prazo(lead.prazo, config)
    pontos_seg, texto_seg = pontuar_segmento(lead.segmento, config)
    pontos_nec, texto_nec = pontuar_necessidade(lead.necessidade, lead.descricao, config)
    pontos_dec, texto_dec = pontuar_decisor(lead.contato_decisor, config)

    nota = min(100, pontos_orc + pontos_prazo + pontos_seg + pontos_nec + pontos_dec)

    linhas = [
        f"Orçamento: {pontos_orc}/{pesos['orcamento']} ({texto_orc})",
        f"Prazo: {pontos_prazo}/{pesos['prazo']} ({texto_prazo})",
        f"Segmento: {pontos_seg}/{pesos['segmento']} ({texto_seg})",
        f"Necessidade: {pontos_nec}/{pesos['necessidade']} ({texto_nec})",
        f"Decisor: {pontos_dec}/{pesos['decisor']} ({texto_dec})",
    ]
    if config["versao"]:
        linhas.append(f"Regras personalizadas, versão {config['versao']}")

    return {
        "nota": nota,
        "classificacao": classificar(nota, config),
        "justificativa": "\n".join(linhas),
        "criterios_versao": config["versao"],
    }
