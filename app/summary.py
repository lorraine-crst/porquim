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


def texto_resumo(ano_mes: str) -> str:
    linhas = resumo_mensal(ano_mes)
    mes = _mes_extenso(ano_mes)

    if not linhas:
        return f"Nenhum gasto registrado em {mes}."

    gasto = total_mes(ano_mes, tipo="gasto")
    recebido = total_mes(ano_mes, tipo="receita")
    investido = total_mes(ano_mes, tipo="investimento")

    partes = [f"*Resumo de {mes}*", ""]

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