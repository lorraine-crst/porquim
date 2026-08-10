import base64
import json
import re
import traceback
from contextlib import asynccontextmanager
from datetime import date

from fastapi import BackgroundTasks, FastAPI, Request, Response

from app.config import ALLOWED_NUMBERS, VERIFY_TOKEN
from app.db import (
    buscar_pendente,
    init_db,
    inserir_lancamento,
    limpar_pendente,
    marcar_mensagem,
    salvar_pendente,
    total_mes,
    apagar_lancamento,
    atualizar_lancamento,
    buscar_pendente,
    init_db,
    inserir_lancamento,
    limpar_pendente,
    marcar_mensagem,
    salvar_pendente,
    total_mes,
    ultimo_lancamento,
)
from app.parser import CATEGORIAS_GASTO, interpretar, interpretar_imagem
from app.summary import brl, texto_resumo, texto_resumo_semana
from app.whatsapp import assinatura_valida, baixar_midia, enviar_texto


AJUDA = (
    'Manda um gasto assim: "mercado 130".\n'
    'Também entendo "recebi 3000 de salário" e "apliquei 500 no CDB".\n'
    "Pode mandar foto de comprovante também.\n\n"
    'Pergunte "resumo" ou "resumo da semana".\n\n'
    "Para corrigir o último lançamento:\n"
    '"apagar" — apaga\n'
    '"categoria transporte" — muda a categoria\n'
    '"valor 50" — corrige o valor'
)

APAGAR = ("apagar", "apaga", "deletar", "deleta", "desfazer", "desfaz", "remover")
MUDAR = ("categoria", "muda", "mudar", "troca", "trocar", "corrig", "era ")

SO_TEXTO_E_IMAGEM = (
    "Por enquanto eu só entendo texto e imagem.\n"
    'Reenvie como mensagem escrita (ex.: "mercado 130") ou mande a foto do comprovante.'
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

    for wamid, numero, kind, dado in _mensagens(json.loads(corpo)):
        if numero not in ALLOWED_NUMBERS:
            print(f"[ignorado] número fora da whitelist: {numero}")
            continue

        if not marcar_mensagem(wamid):
            print(f"[duplicada] já processada: {wamid}")
            continue

        tarefas.add_task(processar, numero, kind, dado)

    return {"status": "ok"}


def _mensagens(dados: dict):
    for entrada in dados.get("entry", []):
        for mudanca in entrada.get("changes", []):
            for msg in mudanca.get("value", {}).get("messages", []):
                tipo = msg.get("type")
                if tipo == "text":
                    yield msg["id"], msg["from"], "text", msg["text"]["body"]
                elif tipo == "image":
                    yield msg["id"], msg["from"], "image", msg["image"]["id"]
                else:
                    yield msg["id"], msg["from"], "outro", tipo


def processar(numero: str, kind: str, dado: str) -> None:
    try:
        if kind == "image":
            _processar_imagem(numero, dado)
        elif kind == "text":
            _processar_texto(numero, dado)
        else:
            enviar_texto(numero, SO_TEXTO_E_IMAGEM)
    except Exception:
        traceback.print_exc()


def _processar_imagem(numero: str, media_id: str) -> None:
    conteudo, media_type = baixar_midia(media_id)
    imagem_b64 = base64.standard_b64encode(conteudo).decode("utf-8")
    lancamento = interpretar_imagem(imagem_b64, media_type)

    if lancamento.valor is None:
        enviar_texto(numero, "Não consegui ler um valor nessa imagem. Pode mandar por texto?")
        return

    ts = lancamento.data.isoformat() if lancamento.data else None
    raw = f"[imagem] {lancamento.descricao or ''}".strip()

    if lancamento.categoria:
        _gravar(numero, lancamento.tipo, lancamento.valor, lancamento.categoria,
                lancamento.descricao or "", ts, raw)
        return

    salvar_pendente(numero, lancamento.tipo, lancamento.valor,
                    lancamento.descricao or "", ts, raw)
    enviar_texto(numero, _pergunta_categoria(lancamento.valor, lancamento.descricao))


def _processar_texto(numero: str, texto: str) -> None:
    pendente = buscar_pendente(numero)

    if pendente:
        if texto.strip().lower() in ("cancelar", "cancela"):
            limpar_pendente(numero)
            enviar_texto(numero, "Lançamento cancelado.")
            return

        categoria = _categoria_escolhida(texto)
        if categoria:
            limpar_pendente(numero)
            _gravar(numero, pendente["tipo"], pendente["valor"], categoria,
                    pendente["descricao"], pendente["ts"], pendente["raw"])
            return

        enviar_texto(numero, _pergunta_categoria(pendente["valor"], pendente["descricao"]))
        return

    edicao = _comando_edicao(numero, texto)
    if edicao:
        enviar_texto(numero, edicao)
        return

    lancamento = interpretar(texto)

    lancamento = interpretar(texto)

    if lancamento.tipo == "pergunta" or lancamento.valor is None:
        enviar_texto(numero, _responder_pergunta(texto, numero))
        return

    _gravar(numero, lancamento.tipo, lancamento.valor, lancamento.categoria or "outros",
            lancamento.descricao or "",
            lancamento.data.isoformat() if lancamento.data else None, texto)


def _gravar(numero: str, tipo: str, valor: float, categoria: str,
            descricao: str, ts: str | None, raw: str) -> None:
    inserir_lancamento(
        tipo=tipo, valor=valor, categoria=categoria, descricao=descricao,
        ts=ts, raw=raw, usuario=numero,
    )
    enviar_texto(numero, f"{ROTULO[tipo]} de R$ {brl(valor)} em {categoria} registrado.")


def _categoria_escolhida(texto: str) -> str | None:
    t = texto.strip().lower()
    if t.isdigit():
        i = int(t) - 1
        return CATEGORIAS_GASTO[i] if 0 <= i < len(CATEGORIAS_GASTO) else None
    return t if t in CATEGORIAS_GASTO else None


def _pergunta_categoria(valor: float, descricao: str | None) -> str:
    alvo = f" ({descricao})" if descricao else ""
    linhas = [f"Li R$ {brl(valor)}{alvo}, mas não identifiquei a categoria.", "", "Responda com o número:"]
    linhas += [f"{i}) {c}" for i, c in enumerate(CATEGORIAS_GASTO, 1)]
    linhas += ["", 'Ou "cancelar" para descartar.']
    return "\n".join(linhas)


def _responder_pergunta(texto: str, usuario: str) -> str:
    t = texto.lower()
    hoje = date.today()

    if "semana" in t:
        return texto_resumo_semana(hoje.strftime("%Y-%W"), usuario)

    if "resumo" in t:
        return texto_resumo(hoje.strftime("%Y-%m"), usuario)

    if "quanto" in t or "gastei" in t:
        total = total_mes(hoje.strftime("%Y-%m"), usuario=usuario)
        return f"Você gastou R$ {brl(total)} neste mês."

    return AJUDA

def _valor_citado(texto: str) -> float | None:
    achado = re.search(r"\d[\d.]*(?:,\d{1,2})?", texto)
    if not achado:
        return None
    try:
        return float(achado.group().replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _categoria_citada(texto: str) -> str | None:
    for categoria in CATEGORIAS_GASTO:
        if categoria in texto:
            return categoria
    return None


def _comando_edicao(usuario: str, texto: str) -> str | None:
    t = texto.strip().lower()

    quer_apagar = any(p in t for p in APAGAR)
    quer_mudar = any(p in t for p in MUDAR)
    nova_categoria = _categoria_citada(t)

    if not (quer_apagar or (quer_mudar and nova_categoria) or t.startswith("valor")):
        return None

    ultimo = ultimo_lancamento(usuario)
    if not ultimo:
        return "Não encontrei nenhum lançamento seu para alterar."

    if quer_apagar:
        apagar_lancamento(ultimo["id"], usuario)
        return (
            f"Apagado: {ROTULO[ultimo['tipo']]} de R$ {brl(ultimo['valor'])} "
            f"em {ultimo['categoria']}."
        )

    if quer_mudar and nova_categoria:
        atualizar_lancamento(ultimo["id"], usuario, categoria=nova_categoria)
        return f"Categoria corrigida para {nova_categoria}: R$ {brl(ultimo['valor'])}."

    novo_valor = _valor_citado(t)
    if novo_valor is None:
        return 'Não entendi o valor. Escreva assim: "valor 50".'

    atualizar_lancamento(ultimo["id"], usuario, valor=novo_valor)
    return f"Valor corrigido para R$ {brl(novo_valor)} em {ultimo['categoria']}."