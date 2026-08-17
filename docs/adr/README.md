# Architecture Decision Records

Este diretório contém todas as decisões arquiteturais significativas do projeto **Vídeos Narrados** (backend FastAPI + app React Native).

## Por que ADRs

Decisões importantes têm motivos que se perdem em conversas, threads e PRs. ADRs preservam o **porquê** ao lado do **o quê**. Se daqui a 6 meses alguém perguntar "por que usamos SQLite em vez de Postgres?", a resposta está aqui — não na memória de quem decidiu.

Justificativa completa: [ADR-0003 — Documentação via ADRs](./0003-documentacao-via-adrs.md).

## Convenções

- Arquivos seguem o padrão `NNNN-titulo-curto-em-kebab-case.md`.
- Numeração é monotônica — nunca reaproveite um número, mesmo se uma ADR for descartada.
- Cada ADR nova usa o template em [`template.md`](./template.md).
- **ADRs aceitas nunca são editadas no mérito.** Pequenos ajustes de redação são ok; mudar a decisão exige uma ADR nova com status `Substituído por ADR-XXXX` na antiga.
- Status válidos: `Proposto`, `Aceito`, `Substituído por ADR-XXXX`, `Obsoleto`.

## Índice

### Compartilhadas (sistema todo)
- [ADR-0001 — Organização Feature-Sliced](./0001-organizacao-feature-sliced.md)
- [ADR-0002 — SOLID pragmático](./0002-solid-pragmatico.md)
- [ADR-0003 — Documentação via ADRs](./0003-documentacao-via-adrs.md)

### Backend
- [ADR-0004 — FastAPI como framework](./0004-fastapi-como-framework.md)
- [ADR-0005 — DI manual via Container leve](./0005-di-manual-container-leve.md)
- [ADR-0006 — SQLite + SQLModel pra persistência](./0006-sqlite-sqlmodel.md)
- [ADR-0007 — Processamento async via BackgroundTasks](./0007-async-via-background-tasks.md)
- [ADR-0008 — Plugin architecture para Temas](./0008-plugin-architecture-temas.md)

### Segurança / Auth
- [ADR-0009 — JWT + Refresh Token rotacionado](./0009-jwt-refresh-token-rotacionado.md)
- [ADR-0010 — SecureStore no app + SHA-256 dos refresh tokens no backend](./0010-securestore-mobile-sha256-backend.md) (escopo atual: backend; seção mobile como TODO)

### Próximas (planejadas, ainda não escritas)
- ADR-0011 — Expo Managed Workflow (mobile)
- ADR-0012 — Zustand + TanStack Query (mobile)
- ADR-0013 — DI idiomática React Native (sem container)

## Como criar uma ADR nova

1. Reserve o próximo número (`ls docs/adr/ | grep '^[0-9]' | sort | tail -1`).
2. Copie `template.md` pra `NNNN-titulo-curto.md`.
3. Preencha **Contexto**, **Decisão**, **Consequências** e **Alternativas consideradas**. Mínimo de uma alternativa real — "não fazer nada" conta se for verdade.
4. Abra PR. Status nasce `Proposto`. Vira `Aceito` ao mergear.
5. Adicione o link no índice acima.
