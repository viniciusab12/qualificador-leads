import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from src.models import STATUS_FUNIL, Lead

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


@contextmanager
def abrir_conexao(caminho_banco=CAMINHO_BANCO):
    """Abre a conexão, confirma as alterações e SEMPRE fecha, mesmo se der erro."""
    conexao = conectar(caminho_banco)
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def criar_tabela(caminho_banco=CAMINHO_BANCO):
    """Cria a tabela de leads, se ela ainda não existir."""
    with abrir_conexao(caminho_banco) as conexao:
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


def salvar_lead(lead, caminho_banco=CAMINHO_BANCO, criado_em=None):
    """Salva um lead novo no banco e devolve o id criado.

    criado_em: data e hora no formato "AAAA-MM-DD HH:MM:SS".
    Se não for informado, usa o momento atual.
    """
    if criado_em is None:
        criado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with abrir_conexao(caminho_banco) as conexao:
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
        return cursor.lastrowid


def _linha_para_lead(linha):
    """Converte uma linha do banco em um objeto Lead."""
    dados = dict(linha)
    dados["contato_decisor"] = bool(dados["contato_decisor"])
    return Lead(**dados)


def listar_leads(caminho_banco=CAMINHO_BANCO):
    """Devolve todos os leads, do mais novo para o mais antigo."""
    with abrir_conexao(caminho_banco) as conexao:
        linhas = conexao.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return [_linha_para_lead(linha) for linha in linhas]


def buscar_lead(lead_id, caminho_banco=CAMINHO_BANCO):
    """Devolve o lead com esse id, ou None se não existir."""
    with abrir_conexao(caminho_banco) as conexao:
        linha = conexao.execute(
            "SELECT * FROM leads WHERE id = ?", (lead_id,)
        ).fetchone()

    if linha is None:
        return None
    return _linha_para_lead(linha)


def atualizar_status(lead_id, novo_status, caminho_banco=CAMINHO_BANCO):
    """Muda o status de um lead. Devolve True se encontrou o lead."""
    if novo_status not in STATUS_FUNIL:
        raise ValueError(f"Status inválido: {novo_status}. Use um destes: {STATUS_FUNIL}")

    with abrir_conexao(caminho_banco) as conexao:
        cursor = conexao.execute(
            "UPDATE leads SET status = ? WHERE id = ?", (novo_status, lead_id)
        )
        return cursor.rowcount > 0


def excluir_lead(lead_id, caminho_banco=CAMINHO_BANCO):
    """Apaga um lead. Devolve True se encontrou o lead."""
    with abrir_conexao(caminho_banco) as conexao:
        cursor = conexao.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        return cursor.rowcount > 0


def excluir_todos_leads(caminho_banco=CAMINHO_BANCO):
    """Apaga TODOS os leads e reinicia a contagem de ids. Devolve quantos foram apagados."""
    with abrir_conexao(caminho_banco) as conexao:
        cursor = conexao.execute("DELETE FROM leads")
        apagados = cursor.rowcount
        conexao.execute("DELETE FROM sqlite_sequence WHERE name = 'leads'")
        return apagados