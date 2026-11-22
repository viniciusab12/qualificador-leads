from dataclasses import dataclass


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
    id: int | None = None