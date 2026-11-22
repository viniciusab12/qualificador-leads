"""Escolhe de onde vêm os leads.

Visitante sem login: os 50 leads de exemplo (SQLite) mais as mudanças que
esse visitante fez, guardadas só na sessão dele (st.session_state).
Usuário logado: os próprios leads, no Supabase.
As páginas usam só este módulo, sem saber qual banco está por trás.
"""

from dataclasses import replace
from datetime import datetime

import streamlit as st

from src import database as demo
from src import supabase_db
from src.auth import usuario_atual
from src.models import STATUS_FUNIL

# Quantas análises reais do Gemini cada visitante pode pedir no modo demonstração
LIMITE_IA_DEMO = 3

# Chaves da sessão do visitante no modo demonstração
CHAVE_NOVOS = "demo_leads_novos"         # leads que o visitante cadastrou
CHAVE_STATUS = "demo_status_alterados"   # {id do lead: novo status}
CHAVE_EXCLUIDOS = "demo_leads_excluidos" # ids que o visitante excluiu
CHAVE_USO_IA = "demo_analises_ia"        # quantas análises reais já pediu


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


# ---------- Modo demonstração: mudanças só na sessão do visitante ----------
#
# O arquivo SQLite com os 50 leads de exemplo é compartilhado por todos os
# visitantes. Por isso ele só é lido, nunca alterado. O que cada visitante
# cadastra, muda ou exclui fica guardado na sessão dele e some quando a aba fecha.

def _sessao():
    """Onde ficam as mudanças do visitante. Os testes trocam por um dicionário."""
    return st.session_state


def _demo_listar():
    sessao = _sessao()
    excluidos = sessao.get(CHAVE_EXCLUIDOS, set())
    status = sessao.get(CHAVE_STATUS, {})

    exemplos = [
        replace(lead, status=status.get(lead.id, lead.status))
        for lead in demo.listar_leads()
        if lead.id not in excluidos
    ]
    novos = [
        replace(lead, status=status.get(lead.id, lead.status))
        for lead in sessao.get(CHAVE_NOVOS, [])
    ]
    # Mais novos primeiro, como no banco
    return sorted(novos, key=lambda lead: lead.id, reverse=True) + exemplos


def _demo_buscar(lead_id):
    lead_id = int(lead_id)
    for lead in _demo_listar():
        if lead.id == lead_id:
            return lead
    return None


def _demo_salvar(lead):
    sessao = _sessao()
    novos = sessao.setdefault(CHAVE_NOVOS, [])

    ids_usados = [item.id for item in demo.listar_leads()] + [item.id for item in novos]
    novo_id = max(ids_usados, default=0) + 1

    novos.append(
        replace(lead, id=novo_id, criado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    return novo_id


def _demo_atualizar_status(lead_id, novo_status):
    if novo_status not in STATUS_FUNIL:
        raise ValueError(f"Status inválido: {novo_status}. Use um destes: {STATUS_FUNIL}")
    lead_id = int(lead_id)
    if _demo_buscar(lead_id) is None:
        return False
    _sessao().setdefault(CHAVE_STATUS, {})[lead_id] = novo_status
    return True


def _demo_excluir(lead_id):
    lead_id = int(lead_id)
    if _demo_buscar(lead_id) is None:
        return False

    sessao = _sessao()
    novos = sessao.get(CHAVE_NOVOS, [])
    if any(lead.id == lead_id for lead in novos):
        sessao[CHAVE_NOVOS] = [lead for lead in novos if lead.id != lead_id]
    else:
        sessao.setdefault(CHAVE_EXCLUIDOS, set()).add(lead_id)
    return True


def pode_usar_ia():
    """Logado: sempre. Modo demonstração: até LIMITE_IA_DEMO análises por visitante."""
    if not modo_demonstracao():
        return True
    return _sessao().get(CHAVE_USO_IA, 0) < LIMITE_IA_DEMO


def registrar_uso_ia():
    """Conta uma análise real feita no modo demonstração."""
    if modo_demonstracao():
        sessao = _sessao()
        sessao[CHAVE_USO_IA] = sessao.get(CHAVE_USO_IA, 0) + 1


# ---------- Escolha do banco ----------

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
    return _executar(_demo_listar, supabase_db.listar_leads)


def buscar_lead(lead_id):
    return _executar(_demo_buscar, supabase_db.buscar_lead, lead_id)


def salvar_lead(lead):
    return _executar(_demo_salvar, supabase_db.salvar_lead, lead)


def atualizar_status(lead_id, novo_status):
    return _executar(_demo_atualizar_status, supabase_db.atualizar_status, lead_id, novo_status)


def excluir_lead(lead_id):
    return _executar(_demo_excluir, supabase_db.excluir_lead, lead_id)
