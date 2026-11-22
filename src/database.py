import sqlite3
from datetime import datetime
from pathlib import Path

from src.models import Lead

# Caminho do arquivo do banco: pasta data/ na raiz do projeto
PASTA_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = PASTA_PROJETO / "data" / "leads.db"


def conectar(caminho_banco=CAMINHO_BANCO):
    """Abre uma conexão com o banco SQLite."""
    caminho_banco = Path(caminho_banco)
    caminho_banco.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho_banco)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_tabela(caminho_banco=CAMINHO_BANCO):
    """Cria a tabela de leads, se ela ainda não existir."""
    conexao = conectar(caminho_banco)
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT NOT NULL,
            contato TEXT NOT NULL,
            segmento TEXT NOT NULL,
            necessidade TEXT NOT NULL,
            descricao TEXT,
            orcamento REAL NOT NULL,
            prazo TEXT NOT NULL,
            contato_decisor INTEGER NOT NULL,
            nota INTEGER,
            classificacao TEXT,
            justificativa TEXT,
            analise_ia TEXT,
            status TEXT DEFAULT 'Novo',
            criado_em TEXT
        )
        """
    )
    conexao.commit()
    conexao.close()


def salvar_lead(lead, caminho_banco=CAMINHO_BANCO):
    """Salva um lead novo no banco e devolve o id criado."""
    criado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conexao = conectar(caminho_banco)
    cursor = conexao.execute(
        """
        INSERT INTO leads (
            empresa, contato, segmento, necessidade, descricao,
            orcamento, prazo, contato_decisor, nota, classificacao,
            justificativa, analise_ia, status, criado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead.empresa,
            lead.contato,
            lead.segmento,
            lead.necessidade,
            lead.descricao,
            lead.orcamento,
            lead.prazo,
            int(lead.contato_decisor),
            lead.nota,
            lead.classificacao,
            lead.justificativa,
            lead.analise_ia,
            lead.status,
            criado_em,
        ),
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()
    return novo_id


def _linha_para_lead(linha):
    """Converte uma linha do banco em um objeto Lead."""
    dados = dict(linha)
    dados["contato_decisor"] = bool(dados["contato_decisor"])
    return Lead(**dados)


def listar_leads(caminho_banco=CAMINHO_BANCO):
    """Devolve todos os leads, do mais novo para o mais antigo."""
    conexao = conectar(caminho_banco)
    linhas = conexao.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    conexao.close()
    return [_linha_para_lead(linha) for linha in linhas]


def buscar_lead(lead_id, caminho_banco=CAMINHO_BANCO):
    """Devolve o lead com esse id, ou None se não existir."""
    conexao = conectar(caminho_banco)
    linha = conexao.execute(
        "SELECT * FROM leads WHERE id = ?", (lead_id,)
    ).fetchone()
    conexao.close()

    if linha is None:
        return None
    return _linha_para_lead(linha)


def atualizar_status(lead_id, novo_status, caminho_banco=CAMINHO_BANCO):
    """Muda o status de um lead. Devolve True se encontrou o lead."""
    conexao = conectar(caminho_banco)
    cursor = conexao.execute(
        "UPDATE leads SET status = ? WHERE id = ?", (novo_status, lead_id)
    )
    conexao.commit()
    encontrou = cursor.rowcount > 0
    conexao.close()
    return encontrou