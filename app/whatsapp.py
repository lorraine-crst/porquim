import hashlib
import hmac

import httpx

from app.config import APP_SECRET, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_TOKEN


VERSAO_API = "v26.0"
BASE_URL = f"https://graph.facebook.com/{VERSAO_API}"


def enviar_texto(para: str, texto: str) -> dict:
    resposta = httpx.post(
        f"{BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": para,
            "type": "text",
            "text": {"body": texto},
        },
        timeout=15,
    )
    resposta.raise_for_status()
    return resposta.json()


def assinatura_valida(corpo_bruto: bytes, header: str | None) -> bool:
    if not APP_SECRET:
        return True

    if not header or not header.startswith("sha256="):
        return False

    esperado = hmac.new(APP_SECRET.encode(), corpo_bruto, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, header.removeprefix("sha256="))

def baixar_midia(media_id: str) -> tuple[bytes, str]:
    cabecalho = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    meta = httpx.get(f"{BASE_URL}/{media_id}", headers=cabecalho, timeout=15)
    meta.raise_for_status()
    info = meta.json()

    arquivo = httpx.get(info["url"], headers=cabecalho, timeout=30)
    arquivo.raise_for_status()

    return arquivo.content, info.get("mime_type", "image/jpeg").split(";")[0]