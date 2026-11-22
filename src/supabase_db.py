"""Leads e regras de pontuação dos usuários logados, guardados no Supabase (PostgreSQL).

Todas as funções recebem o dono (e-mail ou "github|<id>") e só leem ou alteram
os dados dele. O filtro por dono_email é conferido em tests/test_supabase_db.py.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client

from src import config
from src.models import STATUS_FUNIL, Lead

FUSO = ZoneInfo("America/Sao_Paulo")
TABELA = "leads"
TABELA_CRITERIOS = "criterios_conta"

# Campos que atualizar_campos aceita. dono_email, id e criado_em nunca mudam.
CAMPOS_EDITAVEIS = {
    "empresa",
    "contato",
    "segmento",
    "necessidade",
    "descricao",
    "orcamento",
    "prazo",
    "contato_decisor",
    "nota",
    "classificacao",
    "justificativa",
    "analise_ia",
    "status",
    "criterios_versao",
    "anotacoes",
    "proximo_contato",
}


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
        criterios_versao=int(linha.get("criterios_versao") or 0),
        anotacoes=list(linha.get("anotacoes") or []),
        proximo_contato=str(linha.get("proximo_contato") or ""),
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
        "criterios_versao": int(lead.criterios_versao),
        "anotacoes": list(lead.anotacoes),
        "proximo_contato": lead.proximo_contato or None,
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


def atualizar_campos(lead_id, campos, email):
    """Muda campos de um lead do usuário. Devolve True se encontrou o lead.

    Só aceita os campos de CAMPOS_EDITAVEIS: o dono de um lead nunca muda.
    """
    desconhecidos = set(campos) - CAMPOS_EDITAVEIS
    if desconhecidos:
        raise ValueError(f"Campos que não podem ser alterados: {sorted(desconhecidos)}")
    if "status" in campos and campos["status"] not in STATUS_FUNIL:
        raise ValueError(f"Status inválido: {campos['status']}. Use um destes: {STATUS_FUNIL}")

    dados = dict(campos)
    if "proximo_contato" in dados:
        dados["proximo_contato"] = dados["proximo_contato"] or None

    resposta = (
        cliente_banco()
        .table(TABELA)
        .update(dados)
        .eq("id", int(lead_id))
        .eq("dono_email", email)
        .execute()
    )
    return len(resposta.data) > 0


# ---------- Regras de pontuação de cada conta ----------
#
# Cada alteração cria uma versão nova (1, 2, 3...). As versões antigas ficam
# guardadas, então dá para saber com quais regras um lead antigo foi pontuado.

def buscar_criterios(email):
    """Devolve as regras mais recentes do usuário, ou None se ele nunca personalizou."""
    resposta = (
        cliente_banco()
        .table(TABELA_CRITERIOS)
        .select("*")
        .eq("dono_email", email)
        .order("versao", desc=True)
        .limit(1)
        .execute()
    )
    if not resposta.data:
        return None
    linha = resposta.data[0]
    return {**linha["config"], "versao": int(linha["versao"])}


def salvar_criterios(config, email):
    """Guarda uma versão nova das regras do usuário e devolve o número dela."""
    atual = buscar_criterios(email)
    nova_versao = (atual["versao"] if atual else 0) + 1
    sem_versao = {chave: valor for chave, valor in config.items() if chave != "versao"}

    cliente_banco().table(TABELA_CRITERIOS).insert(
        {"dono_email": email, "versao": nova_versao, "config": sem_versao}
    ).execute()
    return nova_versao


# ---------- Conta ----------

def excluir_dados_da_conta(email):
    """Apaga todos os leads e todas as regras do usuário. Devolve quantos leads foram apagados."""
    leads = cliente_banco().table(TABELA).delete().eq("dono_email", email).execute()
    cliente_banco().table(TABELA_CRITERIOS).delete().eq("dono_email", email).execute()
    return len(leads.data)


def excluir_usuario_do_login(id_usuario):
    """Apaga o cadastro de e-mail e senha no Supabase Auth (só para quem entrou por e-mail)."""
    cliente_banco().auth.admin.delete_user(id_usuario)
