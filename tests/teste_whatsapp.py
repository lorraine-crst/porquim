import hashlib
import hmac

from app.config import APP_SECRET
from app.whatsapp import assinatura_valida

corpo = b'{"object":"whatsapp_business_account","entry":[]}'
assinatura = "sha256=" + hmac.new(APP_SECRET.encode(), corpo, hashlib.sha256).hexdigest()

assert assinatura_valida(corpo, assinatura), "assinatura legítima foi recusada"
assert not assinatura_valida(corpo + b" ", assinatura), "corpo adulterado passou"
assert not assinatura_valida(corpo, "sha256=" + "0" * 64), "assinatura errada passou"
assert not assinatura_valida(corpo, None), "requisição sem header passou"
assert not assinatura_valida(corpo, "abc123"), "header sem prefixo sha256= passou"

print("OK — assinatura válida aceita, adulteradas recusadas.")