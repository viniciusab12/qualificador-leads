import json
from types import SimpleNamespace

from src import ai_analyzer, config
from src.models import Lead

RESPOSTA_VALIDA = json.dumps(
    {
        "resumo": "Lead com urgência e orçamento baixo.",
        "pontos_fortes": ["Prazo curto", "Contato decisor"],
        "riscos": ["Orçamento baixo"],
        "proxima_acao": "Ligar e alinhar o escopo.",
        "alerta": "Orçamento baixo para 200 produtos.",
    }
)


def criar_lead_pontuado():
    """Lead fictício que já passou pelas regras de pontuação."""
    return Lead(
        empresa="Empresa Teste",
        contato="Ana",
        segmento="Varejo",
        necessidade="Loja virtual",
        descricao="Loja com 200 produtos e cálculo de frete",
        orcamento=1500,
        prazo="Até 1 mês",
        contato_decisor=True,
        nota=75,
        classificacao="Quente",
        justificativa="Orçamento: 5/30 (orçamento de R$ 1.500)",
    )


# ---------- Modo simulado ----------

def test_sem_chave_usa_modo_simulado(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")

    texto, aviso = ai_analyzer.analisar_lead(criar_lead_pontuado())

    assert "Modo simulado" in aviso
    assert "Empresa Teste" in texto


# ---------- Respostas da IA ----------

def test_resposta_valida_da_ia(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "chave-falsa")
    monkeypatch.setattr(ai_analyzer, "chamar_gemini", lambda prompt: RESPOSTA_VALIDA)

    texto, aviso = ai_analyzer.analisar_lead(criar_lead_pontuado())

    assert aviso is None
    assert "Resumo: Lead com urgência e orçamento baixo." in texto
    assert "- Prazo curto" in texto
    assert "Alerta: Orçamento baixo para 200 produtos." in texto


def test_resposta_que_nao_e_json(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "chave-falsa")
    monkeypatch.setattr(ai_analyzer, "chamar_gemini", lambda prompt: "isto não é JSON")

    texto, aviso = ai_analyzer.analisar_lead(criar_lead_pontuado())

    assert texto == ""
    assert "fora do formato" in aviso


def test_resposta_sem_todos_os_campos(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "chave-falsa")
    monkeypatch.setattr(
        ai_analyzer, "chamar_gemini", lambda prompt: json.dumps({"resumo": "Incompleto"})
    )

    texto, aviso = ai_analyzer.analisar_lead(criar_lead_pontuado())

    assert texto == ""
    assert "fora do formato" in aviso


def test_falha_de_conexao(monkeypatch):
    def simular_falha(prompt):
        raise ConnectionError("sem internet")

    monkeypatch.setattr(config, "GEMINI_API_KEY", "chave-falsa")
    monkeypatch.setattr(ai_analyzer, "chamar_gemini", simular_falha)

    texto, aviso = ai_analyzer.analisar_lead(criar_lead_pontuado())

    assert texto == ""
    assert "internet" in aviso


# ---------- Funções auxiliares ----------

def test_mensagens_de_erro_da_api():
    assert "Limite" in ai_analyzer.mensagem_erro_api(SimpleNamespace(code=429))
    assert "Modelo" in ai_analyzer.mensagem_erro_api(SimpleNamespace(code=404))
    assert "GEMINI_API_KEY" in ai_analyzer.mensagem_erro_api(SimpleNamespace(code=401))


def test_interpretar_resposta_remove_crases():
    texto_com_crases = "```json\n" + RESPOSTA_VALIDA + "\n```"

    dados = ai_analyzer.interpretar_resposta(texto_com_crases)

    assert dados["resumo"] == "Lead com urgência e orçamento baixo."


def test_prompt_contem_nota_e_proibe_alterar():
    prompt = ai_analyzer.montar_prompt(criar_lead_pontuado())

    assert "75/100" in prompt
    assert "Não proponha outra nota" in prompt