import os
from pathlib import Path

TESTE_DB = Path(__file__).resolve().parent / "teste_summary.db"
os.environ["DB_PATH"] = str(TESTE_DB)
TESTE_DB.unlink(missing_ok=True)

from app.db import init_db, inserir_lancamento
from app.summary import texto_resumo

init_db()

inserir_lancamento("gasto", 130.00, "mercado", ts="2026-08-03 10:00:00", raw="mercado 130")
inserir_lancamento("gasto", 27.00, "transporte", ts="2026-08-04 19:30:00", raw="uber 27")
inserir_lancamento("gasto", 1200.00, "moradia", ts="2026-08-05 09:00:00", raw="aluguel")
inserir_lancamento("receita", 3000.00, "salario", ts="2026-08-05 12:00:00", raw="salário")
inserir_lancamento("investimento", 500.00, "investimento", ts="2026-08-06 11:00:00", raw="CDB")

texto = texto_resumo("2026-08")
print(texto)
print()
print(texto_resumo("2026-01"))

assert "1.357,00" in texto, "o total não saiu no formato brasileiro"
assert "Nenhum gasto" in texto_resumo("2026-01"), "mês vazio não foi tratado"
print("\nOK — formatação BRL e mês vazio funcionando.")