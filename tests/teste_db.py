import os
from pathlib import Path

TESTE_DB = Path(__file__).resolve().parent / "teste.db"
os.environ["DB_PATH"] = str(TESTE_DB)
TESTE_DB.unlink(missing_ok=True)

from app.db import init_db, inserir_lancamento, resumo_mensal, total_mes

init_db()

inserir_lancamento("gasto", 130.00, "mercado", ts="2026-08-03 10:00:00", raw="mercado 130")
inserir_lancamento("gasto", 27.00, "transporte", ts="2026-08-04 19:30:00", raw="uber 27")
inserir_lancamento("gasto", 1200.00, "moradia", ts="2026-08-05 09:00:00", raw="paguei 1200 de aluguel")
inserir_lancamento("receita", 3000.00, "salario", ts="2026-08-05 12:00:00", raw="recebi 3000 de salário")
inserir_lancamento("investimento", 500.00, "investimento", ts="2026-08-06 11:00:00", raw="apliquei 500 no CDB")

print("resumo de 2026-08:")
for linha in resumo_mensal("2026-08"):
    print(f"  {linha['categoria']:<12} R$ {linha['total']:>8.2f}  ({linha['qtd']}x)")

total = total_mes("2026-08")
recebido = total_mes("2026-08", tipo="receita")
investido = total_mes("2026-08", tipo="investimento")

print(f"\nrecebido:  R$ {recebido:>8.2f}")
print(f"gasto:     R$ {total:>8.2f}")
print(f"investido: R$ {investido:>8.2f}")
print(f"sobrou:    R$ {recebido - total - investido:>8.2f}")

esperado = 130.00 + 27.00 + 1200.00
categorias = [linha["categoria"] for linha in resumo_mensal("2026-08")]

assert round(total, 2) == esperado, f"esperava {esperado}, veio {total} — a receita entrou!"
assert "salario" not in categorias, "a receita apareceu no resumo de gastos!"
assert round(total_mes("2026-08", tipo="investimento"), 2) == 500.00, "investimento não somou"
assert "investimento" not in categorias, "investimento entrou no resumo de gastos!"
print("OK — a receita de 3000 ficou de fora dos gastos.")