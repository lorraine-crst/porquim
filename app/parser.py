import json
from datetime import date

from anthropic import Anthropic
from pydantic import BaseModel, ValidationError
from typing import Literal

from app.config import ANTHROPIC_API_KEY


MODELO = "claude-haiku-4-5-20251001"

CATEGORIAS = [
    "mercado",
    "alimentacao",
    "transporte",
    "moradia",
    "saude",
    "educacao",
    "lazer",
    "assinaturas",
    "roupas",
    "investimento",
    "salario",
    "freelance",
    "outros",
]

_cliente = Anthropic(api_key=ANTHROPIC_API_KEY)


class Lancamento(BaseModel):
    tipo: Literal["gasto", "receita", "investimento", "pergunta"]
    valor: float | None = None
    categoria: str | None = None
    descricao: str | None = None
    data: date | None = None


def _system_prompt() -> str:
    hoje = date.today().isoformat()
    lista = ", ".join(CATEGORIAS)
    return f"""Você interpreta mensagens curtas de um app de finanças pessoais e devolve JSON.

Hoje é {hoje}.

Responda sempre com um único objeto JSON, sem texto antes ou depois e sem crases.

Formato:
{{"tipo": "gasto"|"receita"|"investimento"|"pergunta", "valor": number|null, "categoria": string|null, "descricao": string|null, "data": "YYYY-MM-DD"|null}}

Regras:
- "gasto" é dinheiro que saiu e foi consumido; "receita" é dinheiro que entrou.
- "investimento" é dinheiro aplicado ou guardado: CDB, Tesouro, ações, fundos, cripto, poupança, reserva de emergência. Não classifique isso como gasto.
- "pergunta" é qualquer outra coisa: consultas como "resumo" ou "quanto gastei esse mês", saudações, e mensagens sem valor.
- valor: número em reais, sem símbolo, com ponto decimal. Interprete o português: "1,2k" é 1200, "mil e duzentos" é 1200, "R$ 1.200,00" é 1200.0.
- categoria: escolha uma desta lista: {lista}. Se nada encaixar, use "outros". Quando o tipo for "investimento", use a categoria "investimento" e coloque o veículo na descricao.
- data: resolva expressões relativas a partir de hoje ("ontem", "anteontem", "dia 3"). Se a mensagem não indicar data, use null.
- descricao: um resumo curto, em poucas palavras.
- Quando tipo for "pergunta", valor, categoria e data devem ser null.

Exemplos:
"mercado 130" -> {{"tipo":"gasto","valor":130.0,"categoria":"mercado","descricao":"mercado","data":null}}
"uber 27" -> {{"tipo":"gasto","valor":27.0,"categoria":"transporte","descricao":"uber","data":null}}
"apliquei 500 no CDB" -> {{"tipo":"investimento","valor":500.0,"categoria":"investimento","descricao":"CDB","data":null}}
"guardei 200 na reserva" -> {{"tipo":"investimento","valor":200.0,"categoria":"investimento","descricao":"reserva de emergência","data":null}}
"recebi 3000 de salário" -> {{"tipo":"receita","valor":3000.0,"categoria":"salario","descricao":"salário","data":null}}
"resumo" -> {{"tipo":"pergunta","valor":null,"categoria":null,"descricao":"resumo","data":null}}"""


def _sem_crases(texto: str) -> str:
    t = texto.strip()
    if t.startswith("```"):
        t = t.removeprefix("```json").removeprefix("```").strip()
        t = t.removesuffix("```").strip()
    return t


def interpretar(texto: str) -> Lancamento:
    resposta = _cliente.messages.create(
        model=MODELO,
        max_tokens=300,
        system=_system_prompt(),
        messages=[{"role": "user", "content": texto}],
    )

    try:
        bruto = next(b.text for b in resposta.content if b.type == "text")
        lancamento = Lancamento(**json.loads(_sem_crases(bruto)))
    except (StopIteration, json.JSONDecodeError, ValidationError, TypeError):
        return Lancamento(tipo="pergunta", descricao=texto)

    if lancamento.categoria is not None and lancamento.categoria not in CATEGORIAS:
        lancamento.categoria = "outros"

    return lancamento