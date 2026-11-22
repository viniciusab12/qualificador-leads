"""Leads dos usuários logados, guardados no Supabase (PostgreSQL).

Todas as funções recebem o e-mail do usuário e só leem ou alteram os leads dele.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client

from src import config
from src.models import STATUS_FUNIL, Lead

FUSO = ZoneInfo("America/Sao_Paulo")
TABELA = "leads"


@st.cache_resource
def cliente_banco():
    """Conexão com o Supabase usando a chave secreta (só o servidor do app a conhece)."""
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def formatar_data(valor):
    """Converte a data do Supabase para o horário de Brasília, no formato do app."""
    if not valor:
        return ""
    momento = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if momento.tzinfo is not None:
        momento = momento.astimezone(FUSO)
    return momento.strftime("%Y-%m-%d %H:%M:%S")


def linha_para_lead(linha):
    """Converte uma linha do Supabase em Lead (sem a coluna dono_email)."""
    return Lead(
        empresa=linha["empresa"],
        contato=linha["contato"],
        segmento=linha["segmento"],
        necessidade=linha["necessidade"],
        descricao=linha.get("descricao") or "",
        orcamento=float(linha["orcamento"]),
        prazo=linha["prazo"],
        contato_decisor=bool(linha["contato_decisor"]),
        nota=int(linha.get("nota") or 0),
        classificacao=linha.get("classificacao") or "",
        justificativa=linha.get("justificativa") or "",
        analise_ia=linha.get("analise_ia") or "",
        status=linha.get("status") or "Novo",
        criado_em=formatar_data(linha.get("criado_em")),
        id=int(linha["id"]),
    )


def salvar_lead(lead, email):
    """Salva um lead do usuário e devolve o id criado."""
    dados = {
        "dono_email": email,
        "empresa": lead.empresa,
        "contato": lead.contato,
        "segmento": lead.segmento,
        "necessidade": lead.necessidade,
        "descricao": lead.descricao,
        "orcamento": float(lead.orcamento),
        "prazo": lead.prazo,
        "contato_decisor": bool(lead.contato_decisor),
        "nota": int(lead.nota),
        "classificacao": lead.classificacao,
        "justificativa": lead.justificativa,
        "analise_ia": lead.analise_ia,
        "status": lead.status,
    }
    resposta = cliente_banco().table(TABELA).insert(dados).execute()
    return int(resposta.data[0]["id"])


def listar_leads(email):
    """Devolve os leads do usuário, do mais novo para o mais antigo."""
    resposta = (
        cliente_banco()
        .table(TABELA)
        .select("*")
        .eq("dono_email", email)
        .order("id", desc=True)
        .execute()
    )
    return [linha_para_lead(linha) for linha in resposta.data]


def buscar_lead(lead_id, email):
    """Devolve o lead com esse id, se ele for do usuário. Senão, None."""
    resposta = (
        cliente_banco()
        .table(TABELA)
        .select("*")
        .eq("id", int(lead_id))
        .eq("dono_email", email)
        .limit(1)
        .execute()
    )
    if not resposta.data:
        return None
    return linha_para_lead(resposta.data[0])


def atualizar_status(lead_id, novo_status, email):
    """Muda o status de um lead do usuário. Devolve True se encontrou o lead."""
    if novo_status not in STATUS_FUNIL:
        raise ValueError(f"Status inválido: {novo_status}. Use um destes: {STATUS_FUNIL}")

    resposta = (
        cliente_banco()
        .table(TABELA)
        .update({"status": novo_status})
        .eq("id", int(lead_id))
        .eq("dono_email", email)
        .execute()
    )
    return len(resposta.data) > 0


def excluir_lead(lead_id, email):
    """Apaga um lead do usuário. Devolve True se encontrou o lead."""
    resposta = (
        cliente_banco()
        .table(TABELA)
        .delete()
        .eq("id", int(lead_id))
        .eq("dono_email", email)
        .execute()
    )
    return len(resposta.data) > 0
