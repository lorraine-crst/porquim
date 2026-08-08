import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS lancamentos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT    NOT NULL,
    criado_em  TEXT    NOT NULL,
    tipo       TEXT    NOT NULL CHECK (tipo IN ('gasto', 'receita', 'investimento')),
    valor      REAL    NOT NULL,
    categoria  TEXT    NOT NULL,
    descricao  TEXT    NOT NULL DEFAULT '',
    origem     TEXT    NOT NULL DEFAULT 'whatsapp',
    raw        TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_lancamentos_ts ON lancamentos (ts);
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(SCHEMA)


def inserir_lancamento(
    tipo: str,
    valor: float,
    categoria: str,
    descricao: str = "",
    ts: str | None = None,
    origem: str = "whatsapp",
    raw: str = "",
) -> int:
    agora = datetime.now().isoformat(sep=" ", timespec="seconds")
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO lancamentos
                (ts, criado_em, tipo, valor, categoria, descricao, origem, raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts or agora, agora, tipo, valor, categoria, descricao, origem, raw),
        )
        return cur.lastrowid


def resumo_mensal(ano_mes: str) -> list[dict]:
    with _conn() as conn:
        linhas = conn.execute(
            """
            SELECT categoria, SUM(valor) AS total, COUNT(*) AS qtd
            FROM lancamentos
            WHERE tipo = 'gasto' AND strftime('%Y-%m', ts) = ?
            GROUP BY categoria
            ORDER BY total DESC
            """,
            (ano_mes,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def total_mes(ano_mes: str, tipo: str = "gasto") -> float:
    with _conn() as conn:
        linha = conn.execute(
            """
            SELECT COALESCE(SUM(valor), 0) AS total
            FROM lancamentos
            WHERE tipo = ? AND strftime('%Y-%m', ts) = ?
            """,
            (tipo, ano_mes),
        ).fetchone()
    return float(linha["total"])