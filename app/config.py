import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _parse_numbers(raw: str) -> set[str]:
    """ "+55 11 99999-1111, 5511988882222" -> {"5511999991111", "5511988882222"} """
    result = set()
    for item in raw.split(","):
        digits = "".join(c for c in item if c.isdigit())
        if digits:
            result.add(digits)
    return result


# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# WhatsApp Cloud API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
APP_SECRET = os.getenv("APP_SECRET", "")

# Só estes números podem conversar com o bot
ALLOWED_NUMBERS = _parse_numbers(os.getenv("ALLOWED_NUMBERS", ""))

# Banco de dados
_db_path = os.getenv("DB_PATH")
DB_PATH = Path(_db_path) if _db_path else BASE_DIR / "financas.db"


_REQUIRED = {
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
    "WHATSAPP_TOKEN": WHATSAPP_TOKEN,
    "WHATSAPP_PHONE_NUMBER_ID": WHATSAPP_PHONE_NUMBER_ID,
    "VERIFY_TOKEN": VERIFY_TOKEN,
    "APP_SECRET": APP_SECRET,
}


def missing_vars() -> list[str]:
    """Variáveis obrigatórias que estão vazias — para checar na subida do app."""
    return [name for name, value in _REQUIRED.items() if not value]