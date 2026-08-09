import json
import traceback
from contextlib import asynccontextmanager
from datetime import date

from fastapi import BackgroundTasks, FastAPI, Request, Response

from app.config import ALLOWED_NUMBERS, VERIFY_TOKEN
from app.db import init_db, inserir_lancamento, total_mes
from app.parser import interpretar
from app.summary import brl, texto_resumo
from app.whatsapp import assinatura_valida, enviar_texto


AJUDA = (
    'Manda um gasto assim: "mercado 130".\n'
    'Também entendo "recebi 3000 de salário" e "apliquei 500 no CDB".\n'
    'Pergunte "resumo" para ver o mês por categoria.'
)

ROTULO = {"gasto": "Gasto", "receita": "Receita", "investimento": "Investimento"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/webhook")
def verificar(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def receber(request: Request, tarefas: BackgroundTasks):
    corpo = await request.body()

    if not assinatura_valida(corpo, request.headers.get("X-Hub-Signature-256")):
        return Response(status_code=403)

    for numero, texto in _mensagens(json.loads(corpo)):
        if numero in ALLOWED_NUMBERS:
            tarefas.add_task(processar, numero, texto)
        else:
            print(f"[ignorado] número fora da whitelist: {numero}")

    return {"status": "ok"}


def _mensagens(dados: dict):
    for entrada in dados.get("entry", []):
        for mudanca in entrada.get("changes", []):
            for msg in mudanca.get("value", {}).get("messages", []):
                if msg.get("type") == "text":
                    yield msg["from"], msg["text"]["body"]


def processar(numero: str, texto: str) -> None:
    try:
        lancamento = interpretar(texto)

        if lancamento.tipo == "pergunta" or lancamento.valor is None:
            enviar_texto(numero, _responder_pergunta(texto))
            return

        categoria = lancamento.categoria or "outros"

        inserir_lancamento(
            tipo=lancamento.tipo,
            valor=lancamento.valor,
            categoria=categoria,
            descricao=lancamento.descricao or "",
            ts=lancamento.data.isoformat() if lancamento.data else None,
            raw=texto,
        )

        enviar_texto(
            numero,
            f"{ROTULO[lancamento.tipo]} de R$ {brl(lancamento.valor)} em {categoria} registrado.",
        )
    except Exception:
        traceback.print_exc()


def _responder_pergunta(texto: str) -> str:
    t = texto.lower()
    mes = date.today().strftime("%Y-%m")

    if "resumo" in t:
        return texto_resumo(mes)

    if "quanto" in t or "gastei" in t:
        return f"Você gastou R$ {brl(total_mes(mes))} neste mês."

    return AJUDA