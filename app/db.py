import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS lancamentos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT    NOT NULL,
    criado_em  TEXT    NOT NULL,
    usuario    TEXT    NOT NULL DEFAULT '',
    tipo       TEXT    NOT NULL CHECK (tipo IN ('gasto', 'receita', 'investimento')),
    valor      REAL    NOT NULL,
    categoria  TEXT    NOT NULL,
    descricao  TEXT    NOT NULL DEFAULT '',
    origem     TEXT    NOT NULL DEFAULT 'whatsapp',
    raw        TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mensagens_vistas (
    id         TEXT PRIMARY KEY,
    criado_em  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lancamentos_ts ON lancamentos (ts);

CREATE TABLE IF NOT EXISTS pendentes (
    usuario    TEXT PRIMARY KEY,
    tipo       TEXT NOT NULL,
    valor      REAL NOT NULL,
    descricao  TEXT NOT NULL DEFAULT '',
    ts         TEXT,
    raw        TEXT NOT NULL DEFAULT '',
    criado_em  TEXT NOT NULL
);
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
        colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(lancamentos)")}
        if "usuario" not in colunas:
            conn.execute("ALTER TABLE lancamentos ADD COLUMN usuario TEXT NOT NULL DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lancamentos_usuario ON lancamentos (usuario)")


def inserir_lancamento(
    tipo: str,
    valor: float,
    categoria: str,
    descricao: str = "",
    ts: str | None = None,
    origem: str = "whatsapp",
    raw: str = "",
    usuario: str = "",
) -> int:
    agora = datetime.now().isoformat(sep=" ", timespec="seconds")
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO lancamentos
                (ts, criado_em, usuario, tipo, valor, categoria, descricao, origem, raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts or agora, agora, usuario, tipo, valor, categoria, descricao, origem, raw),
        )
        return cur.lastrowid


def resumo_mensal(ano_mes: str, formato: str = "%Y-%m", usuario: str | None = None) -> list[dict]:
    sql = """
        SELECT categoria, SUM(valor) AS total, COUNT(*) AS qtd
        FROM lancamentos
        WHERE tipo = 'gasto' AND strftime(?, ts) = ?
    """
    params = [formato, ano_mes]

    if usuario:
        sql += " AND usuario = ?"
        params.append(usuario)

    sql += " GROUP BY categoria ORDER BY total DESC"

    with _conn() as conn:
        linhas = conn.execute(sql, params).fetchall()
    return [dict(linha) for linha in linhas]


def total_mes(
    ano_mes: str,
    tipo: str = "gasto",
    formato: str = "%Y-%m",
    usuario: str | None = None,
) -> float:
    sql = """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM lancamentos
        WHERE tipo = ? AND strftime(?, ts) = ?
    """
    params = [tipo, formato, ano_mes]

    if usuario:
        sql += " AND usuario = ?"
        params.append(usuario)

    with _conn() as conn:
        linha = conn.execute(sql, params).fetchone()
    return float(linha["total"])


def marcar_mensagem(wamid: str) -> bool:
    with _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO mensagens_vistas (id, criado_em) VALUES (?, ?)",
                (wamid, datetime.now().isoformat(sep=" ", timespec="seconds")),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def salvar_pendente(
    usuario: str, tipo: str, valor: float, descricao: str, ts: str | None, raw: str
) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO pendentes (usuario, tipo, valor, descricao, ts, raw, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(usuario) DO UPDATE SET
                tipo=excluded.tipo, valor=excluded.valor, descricao=excluded.descricao,
                ts=excluded.ts, raw=excluded.raw, criado_em=excluded.criado_em
            """,
            (usuario, tipo, valor, descricao, ts, raw,
             datetime.now().isoformat(sep=" ", timespec="seconds")),
        )


def buscar_pendente(usuario: str) -> dict | None:
    with _conn() as conn:
        linha = conn.execute(
            "SELECT tipo, valor, descricao, ts, raw FROM pendentes WHERE usuario = ?",
            (usuario,),
        ).fetchone()
    return dict(linha) if linha else None


def limpar_pendente(usuario: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM pendentes WHERE usuario = ?", (usuario,))