# Vídeos Narrados — Backend FastAPI

Backend HTTP/JSON que orquestra **geração de vídeos curtos narrados** a partir de temas (histórias bíblicas, mitologia, curiosidades, fábulas). Consumido por um app móvel (React Native/Expo), expõe autenticação, gestão de jobs de geração e galeria.

> **Status atual:** fundação arquitetural. As features (`auth`, `videos`, `temas`, `pipeline`) ainda não estão implementadas — esta sessão criou apenas a estrutura, ADRs e o esqueleto.

## Visão geral

A arquitetura segue **Feature-Sliced + DI manual + Protocols nas fronteiras de infra externa**. Cada feature é uma pasta autocontida com suas próprias camadas `domain/`, `data/`, `service.py`, `routes.py`. O `container.py` é o único lugar que instancia implementações concretas.

Decisões principais estão registradas em [`docs/adr/`](./docs/adr/README.md). Leia pelo menos:

- [ADR-0001 — Organização Feature-Sliced](./docs/adr/0001-organizacao-feature-sliced.md)
- [ADR-0004 — FastAPI como framework](./docs/adr/0004-fastapi-como-framework.md)
- [ADR-0005 — DI manual via Container leve](./docs/adr/0005-di-manual-container-leve.md)
- [ADR-0006 — SQLite + SQLModel](./docs/adr/0006-sqlite-sqlmodel.md)

A spec completa está em [`docs/spec_arquitetura.md`](./docs/spec_arquitetura.md). A spec de backend (rotas, modelos) em [`docs/spec_backend.md`](./docs/spec_backend.md). A de auth em [`docs/spec_autenticacao.md`](./docs/spec_autenticacao.md).

O **pipeline procedural antigo** (que ainda gera vídeos via `python -m legacy.main`) está preservado em [`legacy/`](./legacy/README.md). Ele será portado pros adapters da feature `pipeline` (`src/pipeline/adapters/`) em uma sessão futura.

## Pré-requisitos

- **Python 3.10+**
- **FFmpeg** no PATH (usado pelo pipeline legado; eventual adapter futuro)
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg`
- (Opcional) Contas externas pro pipeline legado: Anthropic, Pexels, Gmail SMTP. Configuração detalhada em [`legacy/README.md`](./legacy/README.md).

## Setup

```bash
# 1. Clone e entre na pasta
cd videos_biblicos

# 2. Crie e ative o virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure variáveis de ambiente
cp .env.example .env
# edite .env conforme necessário
```

## Como rodar

### Backend FastAPI

```bash
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

Endpoints atuais:

- `GET /health` → `{"status": "ok"}`
- `GET /docs` → Swagger UI gerado a partir do OpenAPI
- `GET /openapi.json` → schema OpenAPI completo

### Pipeline legado (geração de vídeos)

Ver instruções específicas em [`legacy/README.md`](./legacy/README.md). Resumo: `python -m legacy.main`.

## Autenticação

Modelo **JWT (access curto, 15 min) + Refresh Token opaco rotacionado (30 dias)**. Justificativa completa em [ADR-0009](./docs/adr/0009-jwt-refresh-token-rotacionado.md) e detalhes operacionais em [ADR-0010](./docs/adr/0010-securestore-mobile-sha256-backend.md).

Pontos-chave:
- Access token é stateless (HS256), valida sem consultar o banco.
- Refresh token vai pro cliente em plain; no banco fica só o **SHA-256** — vazamento do DB não permite reuso.
- A cada `POST /auth/refresh`, o refresh atual é revogado (`motivo='rotacao'`) e um novo é emitido.
- **Detecção de invasão**: se um refresh já revogado for apresentado, **todos** os refresh tokens ativos do usuário são revogados e a sessão é invalidada.
- Senha hasheada com bcrypt (rounds=12 por padrão).
- Rate limit no `/auth/login` (5 tentativas / 15 min por IP, configurável).
- Eventos sensíveis logados em `logs/seguranca.log` — sem senhas, sem tokens.

### Gerar `JWT_SECRET_KEY`

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copie a saída e cole em `.env` na variável `JWT_SECRET_KEY`. **Nunca commitar.**

### Endpoints disponíveis

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| `GET` | `/health` | — | Healthcheck |
| `POST` | `/auth/registrar` | público | Cria conta + devolve par de tokens |
| `POST` | `/auth/login` | público (rate-limited) | Autentica + devolve par de tokens |
| `POST` | `/auth/refresh` | público | Rotaciona refresh + emite novo access |
| `POST` | `/auth/logout` | opcional | Revoga um refresh token específico |
| `POST` | `/auth/logout-tudo` | Bearer | Revoga todos os refresh tokens do usuário |
| `GET` | `/auth/eu` | Bearer | Dados do usuário autenticado |
| `PATCH` | `/auth/eu` | Bearer | Atualiza nome ou senha |

Quando o access JWT expira, a resposta vem com header **`X-Token-Expired: true`** — sinal pra o cliente disparar `/auth/refresh` automaticamente.

## Estrutura do projeto

```
videos_biblicos/
├── .env.example                 # Template de variáveis (copiar pra .env)
├── README.md                    # este arquivo
├── requirements.txt
├── docs/
│   ├── adr/                     # Architecture Decision Records
│   ├── spec_arquitetura.md      # Spec completa (canônica)
│   ├── spec_backend.md          # Spec do backend
│   └── spec_autenticacao.md     # Spec de auth
├── legacy/                      # Pipeline procedural antigo (a portar)
│   ├── README.md
│   ├── main.py, historias.py, roteiro.py, narracao.py, ...
├── src/                         # Backend FastAPI (foco do projeto)
│   ├── __init__.py
│   ├── main.py                  # Composition root + /health
│   ├── config.py                # Pydantic Settings
│   ├── container.py             # DI manual (ADR-0005)
│   ├── shared/                  # database, logging, exceptions base
│   ├── auth/                    # (vazia — a implementar)
│   ├── videos/                  # (vazia — a implementar)
│   ├── temas/                   # (vazia — a implementar)
│   └── pipeline/                # (vazia — a implementar)
├── assets/                      # músicas de fundo do pipeline legado
├── output/                      # saídas do pipeline legado
└── storage/                     # arquivos gerados pelo backend (criado em runtime)
```

## ADRs

A pasta [`docs/adr/`](./docs/adr/README.md) contém o histórico de decisões arquiteturais. Veja o [índice](./docs/adr/README.md) para a lista completa e o template.

## Próximos passos

1. Implementar feature `auth` (JWT + refresh token rotacionado) — ver `docs/spec_autenticacao.md`.
2. Implementar features `temas` e `videos`.
3. Portar `legacy/*` pros adapters em `src/pipeline/adapters/`.
4. Remover `legacy/` quando a migração estiver completa.
