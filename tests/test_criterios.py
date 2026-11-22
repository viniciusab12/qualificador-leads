from src import criterios


def config_valida(**mudancas):
    config = criterios.criterios_padrao()
    config.update(mudancas)
    return config


def test_regras_padrao_sao_validas():
    assert criterios.validar_criterios(criterios.criterios_padrao()) == []


def test_pesos_precisam_somar_100():
    pesos = dict(criterios.PESOS_PADRAO, orcamento=40)

    erros = criterios.validar_criterios(config_valida(pesos=pesos))

    assert erros == ["Os pesos precisam somar 100. Hoje somam 110."]


def test_peso_negativo_ou_quebrado_e_recusado():
    negativo = dict(criterios.PESOS_PADRAO, orcamento=-10, prazo=65)
    quebrado = dict(criterios.PESOS_PADRAO, orcamento=29.5, prazo=25.5)

    assert criterios.validar_criterios(config_valida(pesos=negativo))
    assert criterios.validar_criterios(config_valida(pesos=quebrado))


def test_faltar_um_criterio_e_recusado():
    pesos = dict(criterios.PESOS_PADRAO)
    del pesos["decisor"]

    assert "Informe o peso dos 5 critérios." in criterios.validar_criterios(config_valida(pesos=pesos))


def test_morno_precisa_ser_menor_que_quente():
    erros = criterios.validar_criterios(config_valida(limite_quente=50, limite_morno=50))

    assert any("Morno" in erro for erro in erros)


def test_segmento_nao_pode_ser_alvo_e_secundario():
    erros = criterios.validar_criterios(
        config_valida(segmentos_alvo=["Varejo"], segmentos_secundarios=["Varejo"])
    )

    assert any("alvo e secundário" in erro for erro in erros)


def test_segmento_desconhecido_e_recusado():
    erros = criterios.validar_criterios(config_valida(segmentos_alvo=["Mineração"]))

    assert any("desconhecidos" in erro for erro in erros)


def test_completar_criterios_preenche_o_que_falta():
    completa = criterios.completar_criterios({"versao": 3, "pesos": {"orcamento": 40}})

    assert completa["versao"] == 3
    assert completa["pesos"]["orcamento"] == 40
    assert completa["pesos"]["prazo"] == criterios.MAX_PRAZO
    assert completa["limite_quente"] == criterios.LIMITE_QUENTE


def test_completar_criterios_nao_altera_o_padrao():
    criterios.completar_criterios({"pesos": {"orcamento": 99}})

    assert criterios.CRITERIOS_PADRAO["pesos"]["orcamento"] == criterios.MAX_ORCAMENTO
