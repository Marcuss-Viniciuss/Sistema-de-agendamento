# API de Agendamentos

API REST para gerir marcações de uma barbearia: criar, listar, consultar e cancelar agendamentos, com bloqueio de horários duplicados.

Começou como um script de terminal num único ficheiro e foi refeita com separação de responsabilidades, validação automática, testes e Docker.

## Tecnologias

| Ferramenta | Para quê |
|---|---|
| **Python 3.12** | Linguagem |
| **FastAPI** | Framework web e documentação automática (`/docs`) |
| **Pydantic v2** | Validação dos dados de entrada e saída |
| **SQLite** (`sqlite3` nativo) | Persistência, com SQL escrito à mão |
| **PyJWT** | Tokens de sessão (JWT) |
| **pytest** + **httpx** | Testes automatizados |
| **Docker** | Execução em qualquer máquina |

## Arquitetura

```
app/
├── main.py        # Rotas HTTP: traduz pedidos e erros em códigos HTTP
├── schemas.py     # Modelos Pydantic: validação de entrada/saída
├── services.py    # Regras de negócio (sem HTTP, sem SQL)
├── database.py    # Ligação ao SQLite e todas as queries
└── exceptions.py  # Erros de negócio partilhados
tests/
├── conftest.py        # Base de dados temporária por teste
├── test_services.py  # Testes das regras de negócio
└── test_api.py       # Testes ponta a ponta via HTTP
```

O fluxo de um pedido é sempre `main.py` → `services.py` → `database.py`. Cada camada só conhece a seguinte:

- `main.py` não tem SQL nem regras de negócio.
- `services.py` não sabe o que é HTTP nem SQLite.
- `database.py` não sabe de regras, só guarda e lê.

### Decisões de design

- **Sem ORM nem padrão Repository.** Com uma única tabela, um módulo `database.py` com funções já isola o SQL. SQLAlchemy faria sentido se o modelo crescesse.
- **Horário duplicado bloqueado em dois níveis.** O serviço verifica antes de inserir (resposta rápida e clara) e a coluna `inicio` tem `UNIQUE` no banco, que apanha o caso de dois pedidos simultâneos.
- **Datas em formato ISO** (`AAAA-MM-DDTHH:MM:SS`). Guardadas como `AAAA-MM-DD HH:MM`, a ordenação por texto coincide com a ordem cronológica. Segundos são descartados, por isso `14:30:00` e `14:30:45` são o mesmo horário.
- **Erros de banco devolvem 500 genérico**, sem expor detalhes internos ao cliente.

## Endpoints

| Método | Rota | Descrição | Respostas |
|---|---|---|---|
| `POST` | `/agendamentos` | Cria um agendamento | `201`, `409` horário ocupado, `422` dados inválidos ou no passado |
| `GET` | `/horarios-disponiveis?data=AAAA-MM-DD` | Horas ainda livres nesse dia (vazio ao fim de semana ou em dias passados) | `200`, `401`, `422` |
| `GET` | `/agendamentos` | Lista por ordem cronológica; cliente vê só os seus, admin vê todos (`?data=AAAA-MM-DD` filtra por dia) | `200` |
| `GET` | `/agendamentos/{id}` | Consulta um agendamento | `200`, `404` |
| `DELETE` | `/agendamentos/{id}` | Cancela um agendamento, **só admin** | `204`, `404` |
| `POST` | `/auth/registo` | Cria conta de cliente e devolve token | `201`, `409` email repetido, `422` |
| `POST` | `/auth/login` | Autentica e devolve token | `200`, `401` |
| `GET` | `/auth/me` | Utilizador autenticado | `200`, `401` |
| `PATCH` | `/agendamentos/{id}` | Muda o estado (`pendente`/`concluido`), **só admin** | `200`, `403`, `404` |
| `GET` | `/health` | Verificação de estado | `200` |

Exemplo:

```bash
curl -X POST http://localhost:8000/agendamentos \
  -H "Content-Type: application/json" \
  -d '{"cliente": "João Silva", "servico": "Corte", "inicio": "2030-05-20T14:30:00"}'
```

## Como executar

### Localmente

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API fica em http://localhost:8000 e a documentação interativa em http://localhost:8000/docs. Os dados ficam em `agendamentos.db` (ou no caminho definido em `DATABASE_PATH`).

### Com Docker

```bash
docker build -t api-agendamentos .
docker run -p 8000:8000 -v agendamentos-dados:/data api-agendamentos
```

O volume `agendamentos-dados` mantém a base de dados entre execuções do contentor.

## Horário de funcionamento e marcações

- Só **segunda a sexta**, das **09:00 às 12:00** e das **13:00 às 18:00** (pausa de almoço das 12:00 às 13:00).
- Blocos de **30 minutos** por defeito; define `SLOT_MINUTOS=60` para blocos de uma hora. As regras estão em `app/horarios.py`.
- Fora do expediente, ao fim de semana ou fora da grelha (ex: 14:15) a API devolve `422` com a explicação.
- **Sem sobreposição, mesmo em simultâneo:** todos os blocos têm a mesma duração e começam na grelha, por isso dois blocos ou coincidem ou não se tocam. A coluna `inicio` tem `UNIQUE` no SQLite, e é o banco que decide quando dois pedidos chegam ao mesmo tempo: só um INSERT é aceite e o outro recebe `409`. Há um teste com 8 pedidos simultâneos.
- Se mudares `SLOT_MINUTOS` com marcações já existentes, as antigas podem deixar de coincidir com a grelha nova.

## Autenticação e papéis

Todas as rotas de `/agendamentos` exigem o cabeçalho `Authorization: Bearer <token>`.

| Papel | Pode |
|---|---|
| **Cliente** (quem cria conta) | Ver só as suas marcações e criar novas (o nome vem da conta) |
| **Administrador** | Ver todas, criar em nome de qualquer cliente, concluir e cancelar |

- Palavras-passe guardadas com hash PBKDF2-SHA256 e sal aleatório, nunca em texto.
- O papel é lido da base de dados a cada pedido, não do token.
- A conta de administrador é criada no arranque a partir de `ADMIN_EMAIL` e `ADMIN_PASSWORD` (por defeito `admin@demo.pt` / `admin1234`, **só para demonstração**).
- Em produção define também `SECRET_KEY`, que assina os tokens.

```bash
export ADMIN_EMAIL=dono@exemplo.pt ADMIN_PASSWORD=uma-palavra-passe-forte SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
uvicorn app.main:app --reload
```

## Frontend

Painel em HTML, CSS e JavaScript puro (sem frameworks), na pasta `frontend/`: ecrã de login/registo, barra de navegação, resumo (marcações de hoje, pendentes, concluídos) e tabela filtrável. O token fica em `localStorage` e é enviado em todos os pedidos; o que cada papel vê muda consoante a conta. Erros da API (como `409` horário ocupado) aparecem no ecrã.

```bash
# Terminal 1: API
uvicorn app.main:app --reload

# Terminal 2: frontend
cd frontend
python -m http.server 5500
```

Abre http://127.0.0.1:5500. O CORS da API aceita esta origem por defeito; para outra, define `CORS_ORIGINS`.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Cada teste usa uma base de dados SQLite temporária, por isso não afetam os dados reais. Cobrem horários duplicados, datas inexistentes ou no passado, campos vazios, ordenação cronológica, cancelamento e erros de banco.

## Próximos passos

- Duração por serviço, para evitar sobreposições (um corte de 30 min às 14:00 bloqueia as 14:15)
- Endpoint para remarcar (`PATCH`)
- Autenticação
- Migrar para PostgreSQL + SQLAlchemy/Alembic
- Pipeline de CI com GitHub Actions para correr os testes

## Resolução de problemas

**`404 Not Found` em `/auth/registo` (ou noutra rota)**

O 404 genérico (`{"detail":"Not Found"}`) significa que o servidor que respondeu não tem essa rota. Com o código deste projeto isso só acontece se estiver a correr uma versão antiga. Verifica por ordem:

1. Abre http://127.0.0.1:8000/docs. A lista tem de incluir `/auth/registo`, `/auth/login` e `/auth/me`. Se não incluir, o servidor está desatualizado.
2. Pára **todos** os processos do uvicorn (no Windows, `--reload` pode deixar um processo órfão a servir o código antigo): `taskkill /F /IM python.exe` no Windows, ou `pkill -f uvicorn` no Linux/macOS. Confirma que a porta 8000 ficou livre e arranca de novo.
3. Corre o comando **na pasta que contém `app/`** (a raiz do projeto), nunca dentro de `app/`: `uvicorn app.main:app --reload`.
4. Confirma que só existe uma pasta `app/` e que o `app/main.py` contém `/auth/registo`.
5. Testa sem o frontend: `curl -X POST http://127.0.0.1:8000/auth/registo -H "Content-Type: application/json" -d '{"nome":"Ana","email":"ana@mail.pt","password":"segredo123"}'` deve devolver `201`.

Um problema de CORS não dá 404: aparece na consola do navegador como erro de CORS e o pedido nem chega à API.

**Base de dados antiga:** `init_db()` usa `CREATE TABLE IF NOT EXISTS` e acrescenta as colunas novas a uma base existente, por isso não apaga dados.
