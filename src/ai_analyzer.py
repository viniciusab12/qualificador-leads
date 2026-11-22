"""Análise complementar dos leads com a API do Gemini.

A nota e a classificação são calculadas em src/scoring.py.
A IA apenas comenta o lead: ela não altera a nota.
"""

import json

from google import genai
from google.genai import errors, types

from src import config
from src.scoring import formatar_reais

CAMPOS_OBRIGATORIOS = ["resumo", "pontos_fortes", "riscos", "proxima_acao", "alerta"]


def montar_prompt(lead):
    """Monta as instruções e os dados do lead que serão enviados à IA."""
    return f"""Você é um analista comercial de uma empresa que cria sites e sistemas para pequenas e médias empresas.

A nota do lead JÁ FOI CALCULADA por regras fixas. Não proponha outra nota nem outra classificação.
Sua tarefa é comentar o lead para ajudar o vendedor. Use apenas as informações abaixo e não invente dados.

Dados do lead:
- Empresa: {lead.empresa}
- Segmento: {lead.segmento}
- Necessidade: {lead.necessidade}
- Descrição: {lead.descricao or "(não informada)"}
- Orçamento: {formatar_reais(lead.orcamento)}
- Prazo para começar: {lead.prazo}
- Contato é decisor: {"sim" if lead.contato_decisor else "não"}

Resultado das regras:
- Nota: {lead.nota}/100
- Classificação: {lead.classificacao}
- Justificativa:
{lead.justificativa}

Responda somente com um JSON com estes campos:
- "resumo": uma frase sobre o lead.
- "pontos_fortes": lista com até 3 itens curtos.
- "riscos": lista com até 3 itens curtos.
- "proxima_acao": uma ação comercial concreta para o vendedor.
- "alerta": uma inconsistência nos dados (por exemplo, orçamento baixo para o que foi pedido), ou "" se não houver.

Escreva em português do Brasil."""


def chamar_gemini(prompt):
    """Envia o prompt ao Gemini e devolve o texto da resposta."""
    cliente = genai.Client(
        api_key=config.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=30_000),  # 30 segundos
    )
    resposta = cliente.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    return resposta.text


def interpretar_resposta(texto):
    """Converte o texto JSON da IA em dicionário e confere os campos."""
    if not texto:
        raise ValueError("A IA devolveu uma resposta vazia.")

    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`").removeprefix("json").strip()

    dados = json.loads(texto)

    if not isinstance(dados, dict):
        raise ValueError("A resposta da IA não é um objeto JSON.")

    faltando = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in dados]
    if faltando:
        raise ValueError(f"Campos ausentes na resposta da IA: {faltando}")

    return dados


def formatar_analise(dados):
    """Transforma o dicionário da análise em texto para exibir e salvar."""
    linhas = [f"Resumo: {dados['resumo']}", "", "Pontos fortes:"]
    linhas += [f"- {item}" for item in dados["pontos_fortes"]]
    linhas += ["", "Riscos:"]
    linhas += [f"- {item}" for item in dados["riscos"]]
    linhas += ["", f"Próxima ação: {dados['proxima_acao']}"]
    if dados["alerta"]:
        linhas += ["", f"Alerta: {dados['alerta']}"]
    return "\n".join(linhas)


def analise_simulada(lead):
    """Análise de demonstração, usada nos leads fictícios e quando não há chave da API."""
    acoes = {
        "Quente": "Ligar em até 24 horas e agendar uma reunião para apresentar a proposta.",
        "Morno": "Enviar portfólio com projetos parecidos e marcar uma conversa na próxima semana.",
        "Frio": "Registrar o contato e retomar quando houver prazo ou orçamento definidos.",
    }
    dados = {
        "resumo": (
            f"{lead.empresa} ({lead.segmento}) busca {lead.necessidade.lower()} "
            f"e foi classificado como {lead.classificacao.lower()}."
        ),
        "pontos_fortes": ["Análise de demonstração, gerada sem a IA."],
        "riscos": ["Para ver a análise real do Gemini, cadastre um lead novo na página Cadastrar lead."],
        "proxima_acao": acoes.get(lead.classificacao, "Revisar os dados do lead."),
        "alerta": "",
    }
    return formatar_analise(dados)


def mensagem_erro_api(erro):
    """Traduz o código de erro da API em uma mensagem clara."""
    if erro.code in (400, 401, 403):
        return "A API recusou a requisição. Confira a GEMINI_API_KEY no arquivo .env."
    if erro.code == 404:
        return "Modelo não encontrado. Confira o GEMINI_MODEL no arquivo .env."
    if erro.code == 429:
        return "Limite de uso da API atingido. Tente novamente mais tarde."
    return f"A API do Gemini retornou um erro (código {erro.code}). Tente novamente mais tarde."


AVISO_LIMITE_DEMO = (
    "Você já usou as análises com IA do modo demonstração. Esta é uma análise de exemplo. "
    "Entre na sua conta para usar a IA em todos os leads."
)


def analisar_lead(lead, permitir_ia=True):
    """Devolve (texto_da_analise, aviso). O aviso é None quando tudo deu certo.

    permitir_ia=False usa a análise de exemplo sem chamar a API
    (por exemplo, quando o visitante atingiu o limite do modo demonstração).
    """
    if not permitir_ia:
        return analise_simulada(lead), AVISO_LIMITE_DEMO

    if not config.GEMINI_API_KEY:
        aviso = "Modo simulado: configure a GEMINI_API_KEY no arquivo .env para usar a IA."
        return analise_simulada(lead), aviso

    try:
        texto_resposta = chamar_gemini(montar_prompt(lead))
        dados = interpretar_resposta(texto_resposta)
    except errors.APIError as erro:
        return "", mensagem_erro_api(erro)
    except ValueError:
        return "", "A IA respondeu fora do formato esperado. O lead foi salvo sem a análise."
    except Exception as erro:
        print(f"Erro inesperado ao chamar a IA: {erro!r}")
        return "", "Não foi possível conectar à IA. Verifique a internet e tente novamente."

    return formatar_analise(dados), None