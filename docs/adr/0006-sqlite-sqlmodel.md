# 0006. SQLite + SQLModel para persistência

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, persistência, banco

## Contexto

O backend precisa persistir:
- Usuários (e-mail, hash de senha, timestamps).
- Refresh tokens (hash, expiração, status de revogação).
- Jobs de geração de vídeo (status, parâmetros, resultado).
- Vídeos gerados (metadata + caminho do arquivo no storage).
- Histórico de temas usados.

Volume esperado no curto prazo: **dezenas a baixas centenas de usuários**, alguns vídeos por usuário por dia. Sem necessidade de read replicas, sharding, queries de analytics pesadas.

Restrições adicionais:
- Backup simples — copiar um arquivo.
- Deploy simples — sem subir banco separado.
- Modelo de dados ainda em evolução; migrations rápidas valem mais que features avançadas de SQL.

Stack consideradas: SQLite (single-file embutido), Postgres (cliente-servidor), SQLAlchemy puro, SQLModel (SQLAlchemy + Pydantic).

## Decisão

Adotamos **SQLite** como banco e **SQLModel** como camada ORM/ODM.

**SQLite porque:**
- Single-file, zero deploy operacional.
- Performance sobra: SQLite aguenta dezenas de milhares de writes/seg em hardware modesto. Nosso volume previsto está 3-4 ordens de magnitude abaixo do limite.
- Backup = `cp videos.db backup.db`. Restore = inverso.
- WAL mode dá leitura concorrente sem dor.

**SQLModel porque:**
- Modelos são **simultaneamente** SQLAlchemy ORM **e** Pydantic — o mesmo arquivo serve pra persistência e pra schemas Pydantic (com adaptações via subclasses).
- Mesmo autor do FastAPI, integração natural.
- Tipagem forte; modelos viram contratos.
- Por baixo, é SQLAlchemy 2.x — migrar pra Postgres não exige reescrever modelos, só trocar engine + revisar tipos.

## Consequências

### Positivas
- **Setup local em zero passos:** `sqlite:///./videos.db` e acabou.
- **Deploy idem:** subir o backend em qualquer VPS, sem provisionar banco.
- **Modelos sem duplicação:** o mesmo `Usuario(SQLModel)` é usado pra persistência e pode gerar schemas Pydantic via herança.
- **Migração pra Postgres é viável:** SQLAlchemy + SQLModel suportam ambos. Trocar a URL + ajustar tipos específicos (UUID, JSONB) cobre a maior parte.

### Negativas
- **Sem concorrência de write real:** SQLite serializa writes. Em pico de jobs simultâneos, lá pelo 50º write/segundo começa a sentir. Estamos longe disso, mas é teto.
- **Sem tipos nativos avançados:** sem `JSONB` indexável, sem arrays nativos, sem extensions (pg_trgm, etc.). Workaround = `TEXT` + parse manual ou `sqlite-utils`.
- **WAL files** (`.db-wal`, `.db-shm`) precisam ir pro `.gitignore` e ser copiados juntos em backup atômico.
- **SQLModel ainda é "jovem"**: alguns edge cases (relacionamentos complexos, hooks) exigem cair pra SQLAlchemy puro. Mitigado mantendo modelos simples.

### Neutras
- WAL mode será habilitado por padrão (`PRAGMA journal_mode=WAL;`).
- `check_same_thread=False` precisará ser setado no `connect_args` por causa do async/multi-thread do uvicorn.

## Alternativas consideradas

### Alternativa A — PostgreSQL desde o dia 1
**Por que foi descartada:** exige infra (Docker local mínimo, depois Postgres hospedado). Pra prototipagem com 1-3 devs e zero produção crítica, o custo operacional não compensa. Migração futura é viável e barata.

### Alternativa B — SQLAlchemy puro (sem SQLModel)
Mais maduro, mais flexível. **Por que foi descartada:** precisamos duplicar modelos Pydantic pra request/response separadamente dos modelos ORM. SQLModel resolve essa duplicação. Quando bate o limite do SQLModel (relacionamentos complexos), nada impede cair pra SQLAlchemy puro num módulo específico.

### Alternativa C — Tortoise ORM (async puro, parecido com Django)
ORM async-first. **Por que foi descartada:** ecossistema menor, integração com Pydantic menos natural, migrations imaturas. SQLAlchemy 2.x já tem suporte async maduro suficiente.

### Alternativa D — Banco-documento (TinyDB, MongoDB)
**Por que foi descartada:** dados são relacionais (usuário → refresh tokens, usuário → vídeos, vídeo → tema). Forçar documentos cria duplicação ou joins manuais.

## Referências

- [SQLModel docs](https://sqlmodel.tiangolo.com/)
- [SQLite Limitations](https://www.sqlite.org/whentouse.html) — guia oficial de "quando NÃO usar SQLite".
- [SQLite WAL mode](https://www.sqlite.org/wal.html)
- Spec do projeto: `docs/spec_backend.md`.

## Notas de revisão

Re-avaliar quando: (a) concorrência de write virar gargalo medido, (b) precisarmos de tipos avançados (JSONB indexável, full-text search robusto), (c) precisarmos rodar múltiplas instâncias do backend simultaneamente. Qualquer um disso aponta pra Postgres.
