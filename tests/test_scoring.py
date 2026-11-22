from src.models import Lead
from src.scoring import (
    calcular_pontuacao,
    classificar,
    pontuar_necessidade,
    pontuar_orcamento,
    pontuar_prazo,
)


def criar_lead(**mudancas):
    """Cria um lead quente padrão; os campos podem ser trocados no teste."""
    dados = {
        "empresa": "Empresa Teste",
        "contato": "Ana",
        "segmento": "Varejo",
        "necessidade": "Site institucional",
        "descricao": "Quero um site com cardápio e botão de pedidos",
        "orcamento": 8000,
        "prazo": "Até 1 mês",
        "contato_decisor": True,
    }
    dados.update(mudancas)
    return Lead(**dados)


# ---------- Leads completos ----------

def test_lead_quente():
    resultado = calcular_pontuacao(criar_lead())

    assert resultado["nota"] == 95
    assert resultado["classificacao"] == "Quente"


def test_lead_morno():
    lead = criar_lead(
        orcamento=3000,           # 15 pontos
        prazo="1 a 3 meses",      # 18 pontos
        segmento="Serviços",      # 10 pontos
        necessidade="Landing page",
        descricao="Pagina simples",  # 10 pontos (descrição curta)
        contato_decisor=False,    # 3 pontos
    )
    resultado = calcular_pontuacao(lead)

    assert resultado["nota"] == 56
    assert resultado["classificacao"] == "Morno"


def test_lead_frio():
    lead = criar_lead(
        orcamento=0,                     # 0 pontos
        prazo="Indefinido",              # 3 pontos
        segmento="Outro",                # 0 pontos
        necessidade="Aplicativo mobile", # 0 pontos (fora do portfólio)
        descricao="App",                 # 0 pontos (descrição curta)
        contato_decisor=False,           # 3 pontos
    )
    resultado = calcular_pontuacao(lead)

    assert resultado["nota"] == 6
    assert resultado["classificacao"] == "Frio"


def test_nota_maxima_e_100():
    resultado = calcular_pontuacao(criar_lead(orcamento=20000))

    assert resultado["nota"] == 100


def test_justificativa_tem_todos_os_criterios():
    justificativa = calcular_pontuacao(criar_lead())["justificativa"]

    for criterio in ["Orçamento", "Prazo", "Segmento", "Necessidade", "Decisor"]:
        assert criterio in justificativa


# ---------- Casos de borda ----------

def test_limites_da_classificacao():
    assert classificar(100) == "Quente"
    assert classificar(70) == "Quente"
    assert classificar(69) == "Morno"
    assert classificar(40) == "Morno"
    assert classificar(39) == "Frio"
    assert classificar(0) == "Frio"


def test_limites_das_faixas_de_orcamento():
    assert pontuar_orcamento(15000)[0] == 30
    assert pontuar_orcamento(14999)[0] == 25
    assert pontuar_orcamento(5000)[0] == 25
    assert pontuar_orcamento(1999)[0] == 5
    assert pontuar_orcamento(0)[0] == 0


def test_descricao_so_com_espacos_nao_ganha_pontos():
    pontos, _ = pontuar_necessidade("Site institucional", " " * 50)

    assert pontos == 10  # só os pontos do serviço, sem os da descrição


def test_prazo_desconhecido_vale_zero():
    pontos, _ = pontuar_prazo("Ontem")

    assert pontos == 0

# ---------- Regras personalizadas ----------

from src import criterios  # noqa: E402


def regras(**mudancas):
    config = criterios.criterios_padrao()
    config.update(mudancas)
    return config


def test_regras_padrao_dao_o_mesmo_resultado_de_antes():
    lead = criar_lead()

    assert calcular_pontuacao(lead, criterios.criterios_padrao()) == calcular_pontuacao(lead)


def test_peso_maior_aumenta_os_pontos_na_mesma_proporcao():
    pesos = {"orcamento": 40, "prazo": 25, "segmento": 20, "necessidade": 10, "decisor": 5}
    lead = criar_lead(orcamento=3000)  # faixa que vale 15 de 30 no padrão

    resultado = calcular_pontuacao(lead, regras(pesos=pesos, versao=2))

    assert "Orçamento: 20/40" in resultado["justificativa"]
    assert "Regras personalizadas, versão 2" in resultado["justificativa"]
    assert resultado["criterios_versao"] == 2


def test_peso_zero_desliga_o_criterio():
    pesos = {"orcamento": 0, "prazo": 40, "segmento": 30, "necessidade": 20, "decisor": 10}

    resultado = calcular_pontuacao(criar_lead(orcamento=50000), regras(pesos=pesos))

    assert "Orçamento: 0/0" in resultado["justificativa"]


def test_nenhum_criterio_passa_do_proprio_peso():
    lead = criar_lead(orcamento=50000)
    for pesos in [
        {"orcamento": 1, "prazo": 1, "segmento": 1, "necessidade": 1, "decisor": 96},
        {"orcamento": 33, "prazo": 33, "segmento": 1, "necessidade": 1, "decisor": 32},
        {"orcamento": 10, "prazo": 10, "segmento": 10, "necessidade": 67, "decisor": 3},
    ]:
        resultado = calcular_pontuacao(lead, regras(pesos=pesos))
        assert resultado["nota"] <= 100
        assert resultado["nota"] == 100  # lead perfeito leva o máximo de cada critério


def test_limites_personalizados_mudam_a_classificacao():
    lead = criar_lead()  # 95 pontos

    assert calcular_pontuacao(lead, regras(limite_quente=96, limite_morno=50))["classificacao"] == "Morno"


def test_segmentos_personalizados():
    lead = criar_lead(segmento="Tecnologia")

    resultado = calcular_pontuacao(lead, regras(segmentos_alvo=["Tecnologia"], segmentos_secundarios=[]))

    assert "Segmento: 20/20 (Tecnologia é segmento-alvo)" in resultado["justificativa"]
