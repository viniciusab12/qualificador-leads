from dataclasses import dataclass, field

# Etapas do funil de vendas, na ordem em que o lead avança
STATUS_FUNIL = ["Novo", "Em contato", "Proposta enviada", "Ganho", "Perdido"]

# Etapas em que o lead ainda está em negociação
STATUS_EM_ABERTO = ["Novo", "Em contato", "Proposta enviada"]


@dataclass
class Lead:
    """Representa um lead (potencial cliente)."""

    # Dados preenchidos no formulário
    empresa: str
    contato: str
    segmento: str
    necessidade: str
    descricao: str
    orcamento: float
    prazo: str
    contato_decisor: bool

    # Dados calculados pelo sistema (começam vazios)
    nota: int = 0
    classificacao: str = ""
    justificativa: str = ""
    analise_ia: str = ""
    status: str = "Novo"
    criado_em: str = ""

    # Versão das regras de pontuação usada na nota (0 = regras padrão)
    criterios_versao: int = 0

    # Acompanhamento: anotações [{"data": "...", "texto": "..."}] e data do próximo contato (AAAA-MM-DD)
    anotacoes: list = field(default_factory=list)
    proximo_contato: str = ""

    id: int | None = None
