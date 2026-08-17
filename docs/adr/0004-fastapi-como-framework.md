# 0004. FastAPI como framework do backend

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, framework

## Contexto

O backend precisa expor uma API HTTP/JSON consumida por um app React Native (Expo). As features previstas envolvem:

- **Autenticação** com JWT + refresh token rotacionado (ver spec de auth).
- **Upload + processamento async** de jobs de geração de vídeo.
- **Listagem/CRUD** de temas e vídeos por usuário.
- **Integração com APIs externas** (Anthropic, Pexels, edge-tts, Whisper local, FFmpeg).

Requisitos não-funcionais relevantes:
- Tipagem forte (Pydantic models como contratos de entrada/saída).
- Documentação automática (OpenAPI/Swagger) — o app móvel precisa do schema.
- Suporte async nativo (chamadas a IA são I/O bound; bloquear o event loop é caro).
- Time de 1-3 devs, baixo orçamento operacional, alvo de prototipagem rápida.

Frameworks Python considerados: FastAPI, Flask (com extensões), Django (DRF), Litestar.

## Decisão

Adotamos **FastAPI** como framework HTTP do backend.

Os pesos decisivos:
1. **Tipagem nativa via Pydantic 2** — request/response models são código tipado, não decoradores soltos. Validações implícitas em parâmetros de rota.
2. **OpenAPI gerado automaticamente** — `/docs` e `/openapi.json` saem grátis. O app pode gerar clients tipados (orval, openapi-typescript) sem esforço manual.
3. **Async nativo** — `async def` em endpoints, suporte a `await` sem hacks. Integra naturalmente com clientes HTTP async (httpx).
4. **`Depends()` é o suficiente como injeção de transporte** — combinamos com o container manual ([ADR-0005](./0005-di-manual-container-leve.md)) sem fricção.
5. **Comunidade ativa, mantenedor responsivo, ecossistema maduro** (SQLModel, dependências comuns).

## Consequências

### Positivas
- Type checking real em rotas (mypy/pyright pegam erro antes do runtime).
- Documentação OpenAPI sem código adicional — perfeita pro contrato com o mobile.
- Performance nativa boa (Starlette under the hood, ASGI, async).
- Curva de aprendizado curta pra quem sabe Python tipado.
- `BackgroundTasks` resolve nosso caso de processamento assíncrono leve ([ADR-0007](./0007-async-via-background-tasks.md)).

### Negativas
- **Pydantic 2 tem dor de migração** — bibliotecas antigas podem ainda assumir Pydantic 1. Mitigado fixando versão.
- **Ecossistema "ORM-friendly" menos maduro que Django** — não temos admin pronto, scaffolding de CRUD, migrations integradas. Pra um projeto desta escala, ok.
- **Magic do `Depends()`** — pode confundir devs vindos de Flask puro. Mitigado documentando padrão no README de cada feature.

### Neutras
- Stack ASGI em vez de WSGI — uvicorn como server padrão, gunicorn opcional.
- Estrutura de testes muda: `TestClient` ou `httpx.AsyncClient` em vez de cliente de teste do Flask.

## Alternativas consideradas

### Alternativa A — Flask + extensões (Flask-RESTX, marshmallow, flask-jwt-extended)
Framework minimalista, ecossistema gigante. **Por que foi descartada:** async é "bolted on" (Flask 2.x), documentação OpenAPI exige extensão ou geração manual, tipagem depende de mais boilerplate. Pra nossa carga de I/O async, FastAPI vence.

### Alternativa B — Django + Django REST Framework (DRF)
Bateria completa: ORM, admin, auth, migrations, DRF maduro. **Por que foi descartada:** **muito grande** pra nosso escopo. Modelo síncrono dominante (async ainda é incompleto em 2026 fora de views específicas). Estrutura monolítica conflita com nossa organização feature-sliced (apps do Django são similares, mas trazem peso). Vale pena se tivéssemos painel admin como requisito, mas não temos.

### Alternativa C — Litestar (ex-Starlite)
Moderno, async-nativo, design parecido com FastAPI. **Por que foi descartada:** comunidade ~10x menor, menos respostas no Stack Overflow, menos integrações testadas (SQLModel, etc). FastAPI tem a mesma base ergonômica com maturidade superior **hoje** — não há ganho concreto que justifique trocar.

### Alternativa D — Node.js (NestJS, Fastify)
Mudar stack pra TypeScript no backend também. **Por que foi descartada:** o pipeline antigo já é Python (Anthropic SDK, edge-tts, faster-whisper, FFmpeg via subprocess); migrar pra Node forçaria reescrita de tudo ou camada glue. Python permite reaproveitar `legacy/` direto nos adapters.

## Referências

- [FastAPI docs](https://fastapi.tiangolo.com/)
- [Pydantic v2 migration guide](https://docs.pydantic.dev/latest/migration/)
- Spec do projeto: `docs/spec_backend.md`.

## Notas de revisão

Re-avaliar se o time crescer e a falta de "admin Django-style" virar dor. Pode caber um Django Admin standalone consumindo o mesmo DB, ou um painel custom em React.
