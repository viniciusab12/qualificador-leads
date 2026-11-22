"""Escolhe de onde vêm os leads.

Visitante sem login: base de demonstração (SQLite, dados fictícios).
Usuário logado: os próprios leads, no Supabase.
As páginas usam só este módulo, sem saber qual banco está por trás.
"""

from src import database as demo
from src import supabase_db
from src.auth import usuario_atual


class ErroBanco(Exception):
    """Falha ao ler ou gravar leads, em qualquer um dos bancos."""


def email_logado():
    """Dono dos leads de quem está logado, ou None no modo demonstração.

    Para e-mail e senha e para o Google, é o e-mail. Para o GitHub, é o
    identificador fixo da conta (ex.: "github|12345").
    """
    usuario = usuario_atual()
    return usuario["dono"] if usuario else None


def modo_demonstracao():
    """True quando ninguém está logado."""
    return email_logado() is None


def _executar(funcao_demo, funcao_usuario, *args):
    """Chama a função do banco certo e padroniza os erros."""
    email = email_logado()
    try:
        if email:
            return funcao_usuario(*args, email)
        return funcao_demo(*args)
    except ValueError:
        raise
    except Exception as erro:
        raise ErroBanco(str(erro)) from erro


def criar_tabela():
    """Prepara a base de demonstração. No Supabase, a tabela já existe."""
    demo.criar_tabela()


def listar_leads():
    return _executar(demo.listar_leads, supabase_db.listar_leads)


def buscar_lead(lead_id):
    return _executar(demo.buscar_lead, supabase_db.buscar_lead, lead_id)


def salvar_lead(lead):
    return _executar(demo.salvar_lead, supabase_db.salvar_lead, lead)


def atualizar_status(lead_id, novo_status):
    return _executar(demo.atualizar_status, supabase_db.atualizar_status, lead_id, novo_status)


def excluir_lead(lead_id):
    return _executar(demo.excluir_lead, supabase_db.excluir_lead, lead_id)
