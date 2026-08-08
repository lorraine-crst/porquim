from app.parser import interpretar

casos = [
    "mercado 130",
    "paguei 1200 de aluguel ontem",
    "apliquei 500 no CDB",
    "resumo",
]

for texto in casos:
    resultado = interpretar(texto)
    print(f"{texto!r}")
    print(f"  -> {resultado.model_dump_json()}")
    print()

assert interpretar("mercado 130").tipo == "gasto"
assert interpretar("resumo").tipo == "pergunta"
assert interpretar("apliquei 500 no CDB").tipo == "investimento"
print("OK — tipos classificados corretamente.")