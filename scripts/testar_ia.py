"""Testa a análise da IA com um lead fictício. Não salva nada no banco.

Como rodar (na raiz do projeto):  python -m scripts.testar_ia
"""

from src.ai_analyzer import analisar_lead
from src.models import Lead
from src.scoring import calcular_pontuacao

lead = Lead(
    empresa="Boutique Flor de Lis",
    contato="Carla",
    segmento="Varejo",
    necessidade="Loja virtual",
    descricao="Loja online com 200 produtos, pagamento por Pix e cartão e cálculo de frete",
    orcamento=1500,
    prazo="Até 1 mês",
    contato_decisor=True,
)

resultado = calcular_pontuacao(lead)
lead.nota = resultado["nota"]
lead.classificacao = resultado["classificacao"]
lead.justificativa = resultado["justificativa"]

print(f"Nota: {lead.nota}/100 ({lead.classificacao})")
print()

texto, aviso = analisar_lead(lead)
if aviso:
    print("Aviso:", aviso)
print(texto)