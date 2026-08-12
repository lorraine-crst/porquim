# Porquim Pessoal 🐷

Assistente financeiro pessoal no WhatsApp. Você manda "mercado 130", ele
registra e categoriza. Pergunta "resumo", recebe o total do mês por categoria.

Produção: `railway.com`

## Como funciona

```
WhatsApp  ──▶  webhook (FastAPI)  ──▶  Claude (texto → JSON)
                     │                        │
                     ▼                        ▼
              resposta ao usuário  ◀──   SQLite (lançamentos)
```

Texto livre é convertido em JSON pelo Claude Haiku. Fotos de comprovante são
lidas pelo Claude Sonnet com visão. O resultado vai para o SQLite e o bot
confirma.

## Comandos

Registrar:

```
mercado 130
uber 27
paguei 1200 de aluguel ontem
recebi 3000 de salário
apliquei 500 no CDB
```

O valor aceita "1,2k", "mil e duzentos" ou "R$ 1.200,00". Datas relativas como
"ontem" são resolvidas na gravação.

Foto de comprovante: valor e estabelecimento saem da imagem. Se a categoria não
for evidente, o bot pergunta e você responde com número ou nome.

Consultar:

```
resumo
resumo da semana
quanto gastei esse mês?
```

Corrigir o último lançamento:

```
apagar
categoria transporte
valor 50
```

Áudio não é suportado. O bot pede texto ou imagem.

## Estrutura

```
app/
  config.py      lê o .env
  db.py          schema, migrações e consultas
  parser.py      interpreta texto e imagem
  summary.py     monta o resumo em BRL
  whatsapp.py    envio e validação de assinatura
  main.py        webhook e roteamento
tests/           um teste por módulo
Procfile         comando de start
requirements.txt
```

## Dados

Três tipos de lançamento: `gasto`, `receita` e `investimento`. Investimento é
tipo próprio, não categoria de gasto, para separar os três totais do mês.

Tabela `lancamentos`:

| coluna | descrição |
|--------|-----------|
| `id` | chave primária |
| `ts` | quando o gasto aconteceu |
| `criado_em` | quando a linha foi gravada |
| `usuario` | número de quem enviou |
| `tipo` | gasto, receita ou investimento |
| `valor` | em reais |
| `categoria` | da lista fechada em `parser.py` |
| `descricao` | resumo curto |
| `origem` | canal de entrada |
| `raw` | mensagem original |

Cada usuário vê apenas os próprios lançamentos.

Tabelas de apoio: `mensagens_vistas` (deduplicação por id, contra reentrega da
Meta) e `pendentes` (lançamento de imagem aguardando categoria).

## Configuração

| Variável | Origem |
|----------|--------|
| `ANTHROPIC_API_KEY` | console.anthropic.com, API Keys |
| `WHATSAPP_TOKEN` | System User token, business.facebook.com |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta, WhatsApp, API Setup |
| `VERIFY_TOKEN` | Definido por você, igual no painel da Meta |
| `APP_SECRET` | Meta, Configurações, Básico |
| `ALLOWED_NUMBERS` | Números autorizados, separados por vírgula |
| `DB_PATH` | Opcional. Padrão: `financas.db` na raiz |

Local no `.env` (modelo em `.env.example`), produção nas variáveis da
plataforma.

A Meta identifica números brasileiros com ou sem o nono dígito. Cadastre as
duas variantes em `ALLOWED_NUMBERS`.

## Rodar local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --port 8000 --reload
```

Para receber mensagens reais localmente é preciso expor a porta com ngrok e
apontar o webhook da Meta para essa URL.

## Testes

```bash
python -m tests.teste_db
python -m tests.teste_parser
python -m tests.teste_summary
python -m tests.teste_whatsapp
```

Usam bancos próprios. O do parser consome créditos da API.

## Deploy

Railway, com deploy automático a cada push na `main`.

Requisitos:

- `Procfile` com o comando de start. Sem ele o build falha, porque o detector
  automático não encontra `app.main:app`.
- `.python-version` fixando a versão.
- Volume em `/data` e `DB_PATH=/data/financas.db`. O disco do contêiner é
  efêmero e o banco seria apagado a cada deploy.

Variáveis de ambiente vão no painel. Erros aparecem em Deploy Logs.

## Segurança

`ALLOWED_NUMBERS` restringe quem pode usar o bot.

`APP_SECRET` valida a assinatura HMAC-SHA256 de cada webhook. O corpo é lido em
bytes crus antes do parsing, senão a verificação quebra.

Edição e exclusão filtram por usuário.

O `.env` não é versionado. Chave vazada precisa ser revogada, não apagada.

## Custos

`claude-haiku-4-5` para texto, `claude-sonnet-5` para imagem. Menos de um
décimo de centavo de dólar por mensagem de texto.

Respostas dentro da janela de 24h são gratuitas na Cloud API. Mensagens
iniciadas pelo bot fora dela exigem template aprovado e são cobradas.

## Próximos passos

- Alertas de limite por categoria
- Resumo automático no dia 1º
- Backup do banco de produção
