from datetime import datetime, timedelta

from app.db import resumo_mensal, total_mes


MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mes_extenso(ano_mes: str) -> str:
    ano, mes = ano_mes.split("-")
    return f"{MESES[int(mes) - 1]} de {ano}"


def _semana_extenso(ano_semana: str) -> str:
    try:
        inicio = datetime.strptime(f"{ano_semana}-1", "%Y-%W-%w").date()
    except ValueError:
        return f"semana {ano_semana}"
    fim = inicio + timedelta(days=6)
    return f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')}"


def _monta(periodo: str, formato: str, titulo: str, usuario: str | None) -> str:
    linhas = resumo_mensal(periodo, formato=formato, usuario=usuario)

    if not linhas:
        return f"Nenhum gasto registrado em {titulo}."

    gasto = total_mes(periodo, tipo="gasto", formato=formato, usuario=usuario)
    recebido = total_mes(periodo, tipo="receita", formato=formato, usuario=usuario)
    investido = total_mes(periodo, tipo="investimento", formato=formato, usuario=usuario)

    partes = [f"*Resumo de {titulo}*", ""]

    for linha in linhas:
        pct = linha["total"] / gasto * 100
        pct_txt = f"{pct:.1f}".replace(".", ",")
        partes.append(f"• {linha['categoria']}: R$ {brl(linha['total'])} ({pct_txt}%)")

    partes.append("")
    partes.append(f"Gasto: R$ {brl(gasto)}")

    if investido:
        partes.append(f"Investido: R$ {brl(investido)}")

    if recebido:
        partes.append(f"Recebido: R$ {brl(recebido)}")
        partes.append(f"Sobrou: R$ {brl(recebido - gasto - investido)}")

    return "\n".join(partes)


def texto_resumo(ano_mes: str, usuario: str | None = None) -> str:
    return _monta(ano_mes, "%Y-%m", _mes_extenso(ano_mes), usuario)


def texto_resumo_semana(ano_semana: str, usuario: str | None = None) -> str:
    return _monta(ano_semana, "%Y-%W", _semana_extenso(ano_semana), usuario)