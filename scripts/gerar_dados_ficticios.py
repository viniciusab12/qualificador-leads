"""Gera leads fictícios para testar o app e o dashboard.

Como rodar (na raiz do projeto):
    python -m scripts.gerar_dados_ficticios            adiciona 50 leads
    python -m scripts.gerar_dados_ficticios --limpar   apaga todos os leads antes
"""

import random
import sys
from datetime import datetime, timedelta

from src import criterios
from src.ai_analyzer import analise_simulada
from src.database import criar_tabela, excluir_todos_leads, salvar_lead
from src.models import STATUS_FUNIL, Lead
from src.scoring import calcular_pontuacao

QUANTIDADE = 50
SEMENTE = 42  # mesma semente = mesmos leads sempre
DIAS_PARA_TRAS = 90

SEGMENTOS = criterios.SEGMENTOS_ALVO + criterios.SEGMENTOS_SECUNDARIOS + ["Outro"]
NECESSIDADES = criterios.SERVICOS_OFERECIDOS + ["Outro"]
PRAZOS = list(criterios.PONTOS_PRAZO.keys())

PREFIXOS = {
    "Varejo": ["Loja", "Boutique", "Mercado"],
    "Alimentação": ["Padaria", "Restaurante", "Cafeteria"],
    "Saúde": ["Clínica", "Consultório", "Laboratório"],
    "Educação": ["Escola", "Curso", "Colégio"],
    "Serviços": ["Escritório", "Agência", "Oficina"],
    "Indústria": ["Metalúrgica", "Indústria", "Fábrica"],
    "Tecnologia": ["Tech", "Soluções", "Sistemas"],
    "Outro": ["Associação", "Instituto", "Grupo"],
}
NOMES = [
    "Aurora", "Bom Grão", "Vida", "Horizonte", "Central", "Estrela",
    "Primavera", "Nova Era", "Real", "Bela Vista", "Sol Nascente", "Vale Verde",
]
CONTATOS = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio",
    "Gabriela", "Henrique", "Isabela", "João", "Larissa", "Marcos",
]
DESCRICOES = [
    "Site com páginas de serviços, formulário de contato e integração com WhatsApp",
    "Loja online com catálogo de produtos e pagamento por Pix e cartão",
    "Sistema para controlar estoque, vendas e emissão de relatórios",
    "Página única para divulgar uma campanha e captar contatos",
    "Atualizar o site atual e corrigir problemas de velocidade",
    "Quero um site",
    "Orçamento",
    "",
]
ORCAMENTOS = [0, 1000, 1500, 2500, 3500, 6000, 8000, 12000, 18000, 25000]

# Chance de cada status (na ordem do STATUS_FUNIL) conforme a classificação.
# Leads quentes têm mais chance de virar "Ganho"; frios, de ficar parados ou ser perdidos.
PESOS_STATUS = {
    "Quente": [1, 2, 3, 3, 1],
    "Morno": [2, 3, 2, 1, 2],
    "Frio": [4, 2, 1, 0.5, 2.5],
}


def gerar_lead():
    """Cria um lead fictício, já pontuado pelas regras reais."""
    segmento = random.choice(SEGMENTOS)

    lead = Lead(
        empresa=f"{random.choice(PREFIXOS[segmento])} {random.choice(NOMES)}",
        contato=random.choice(CONTATOS),
        segmento=segmento,
        necessidade=random.choice(NECESSIDADES),
        descricao=random.choice(DESCRICOES),
        orcamento=random.choice(ORCAMENTOS),
        prazo=random.choice(PRAZOS),
        contato_decisor=random.random() < 0.6,
    )

    resultado = calcular_pontuacao(lead)
    lead.nota = resultado["nota"]
    lead.classificacao = resultado["classificacao"]
    lead.justificativa = resultado["justificativa"]
    lead.analise_ia = analise_simulada(lead)
    lead.status = random.choices(STATUS_FUNIL, weights=PESOS_STATUS[lead.classificacao])[0]

    return lead


def gerar_data():
    """Sorteia uma data e hora dentro dos últimos DIAS_PARA_TRAS dias."""
    momento = datetime.now() - timedelta(
        days=random.randint(0, DIAS_PARA_TRAS),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return momento.strftime("%Y-%m-%d %H:%M:%S")


def main():
    random.seed(SEMENTE)
    criar_tabela()

    if "--limpar" in sys.argv:
        apagados = excluir_todos_leads()
        print(f"{apagados} leads apagados.")

    for _ in range(QUANTIDADE):
        salvar_lead(gerar_lead(), criado_em=gerar_data())

    print(f"{QUANTIDADE} leads fictícios cadastrados.")


if __name__ == "__main__":
    main()