# 0007. Processamento assíncrono via BackgroundTasks

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, async, jobs

## Contexto

Gerar um vídeo bíblico envolve uma cadeia de etapas custosas em tempo real:
1. Pedir roteiro pro Claude (~3-5 segundos).
2. Gerar narração com edge-tts (~5-10 segundos).
3. Transcrever com Whisper local (~30-60 segundos em CPU).
4. Buscar e baixar vídeos do Pexels (~10-30 segundos).
5. Compor vídeo final com FFmpeg (~30-60 segundos).

Total: **~90 a 180 segundos por vídeo.** Um cliente HTTP que esperasse a request inteira teria timeout em qualquer reverse proxy razoável. O usuário precisa receber resposta imediata "job criado, processando" e poder consultar status depois.

A pergunta arquitetural: como rodar esse processamento em background?

Opções consideradas: `BackgroundTasks` do FastAPI, `asyncio.create_task` direto, Celery + Redis/RabbitMQ, RQ, Dramatiq, Arq.

## Decisão

Adotamos **`BackgroundTasks` do FastAPI** como mecanismo de execução assíncrona.

Fluxo previsto:
1. POST `/videos/gerar` recebe parâmetros, cria registro `Job(status='pendente')` no SQLite, enfileira `BackgroundTasks.add_task(processar_job, job_id)`, responde 202 + `job_id`.
2. `processar_job` roda em segundo plano, atualiza o `status` no banco em cada etapa.
3. Cliente consulta `GET /videos/jobs/{job_id}` pra acompanhar.

## Consequências

### Positivas
- **Zero infra extra:** sem Redis, sem RabbitMQ, sem worker separado. Tudo no mesmo processo do uvicorn.
- **Setup local trivial:** roda em qualquer máquina sem `docker-compose`.
- **Suficiente pra carga prevista:** com 1-3 usuários ativos por hora gerando ~1 vídeo cada, paralelismo mínimo basta.
- **Reaproveita código async-friendly do FastAPI sem boilerplate de fila.**

### Negativas
- **Sem durabilidade:** se o processo do uvicorn cai durante o processamento, o job vira "fantasma" — status fica `processando` pra sempre. Mitigado com um job watchdog que marca jobs órfãos como `falhou` no startup.
- **Sem retry automático:** falha numa etapa = job morre. Mitigado escrevendo `processar_job` com try/except por etapa e gravação de erro no DB.
- **Sem escala horizontal real:** múltiplas instâncias do backend não compartilham fila. Mitigado: a partir desta sessão, **rodamos só 1 instância**. Se virar limite, migrar.
- **Compartilhamento de event loop:** tasks pesadas (Whisper em CPU, FFmpeg via subprocess) bloqueiam workers HTTP. Mitigado usando `asyncio.to_thread` ou `ProcessPoolExecutor` pra trabalho pesado.

### Neutras
- A camada de "fila" é o próprio banco — o `Job(status, payload)` substitui um broker.
- Logs de processamento ficam no mesmo stdout do servidor — observabilidade simples.

## Quando re-avaliar (gatilhos explícitos)

Migrar pra **Celery + Redis** quando ocorrer **qualquer um** destes:
1. Precisarmos rodar >1 instância do backend (zero-downtime deploys, escala horizontal).
2. **Retry automático com backoff** virar requisito (ex.: SLA de geração com retentativa).
3. Filas separadas por prioridade (ex.: jobs gratuitos vs. premium).
4. >50 jobs simultâneos em pico — gerência manual do event loop fica insuficiente.

Migração: extrair `processar_job` pra função pura recebendo dependências (já é o plano via `orchestrator.py`), e envolver com um worker Celery. Mudança contida.

## Alternativas consideradas

### Alternativa A — Celery + Redis desde o dia 1
Maduro, durável, retry, monitoring (Flower). **Por que foi descartada:** custo operacional alto pra começar — exige Redis em dev, em CI, em prod. Configurações de broker, result backend, serialização. Gargalo de bootstrapping superior ao ganho enquanto o sistema é pequeno.

### Alternativa B — Dramatiq ou Arq (alternativas mais leves)
Mais simples que Celery, ainda usam Redis. **Por que foi descartada:** ainda exige Redis. Se a gente vai pagar o custo de um broker, vale ir pra Celery direto pelo ecossistema. Se não vai, `BackgroundTasks` é mais leve ainda.

### Alternativa C — `asyncio.create_task` direto, sem `BackgroundTasks`
Spawn de coroutines manuais. **Por que foi descartada:** `BackgroundTasks` já é açúcar pra isso, com integração com lifecycle do FastAPI (resposta vai antes da task começar). Reinventar não traz ganho.

### Alternativa D — RQ
**Por que foi descartada:** mesmo motivo do Dramatiq — exige Redis. Sem ganho relevante.

### Alternativa E — Threads do `concurrent.futures.ThreadPoolExecutor`
**Por que foi descartada:** funciona pra workload puro CPU, mas mistura mal com `async def`. `BackgroundTasks` + `asyncio.to_thread` cobre os mesmos cenários de forma mais idiomática no FastAPI.

## Referências

- [FastAPI — Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Distributed Task Queue Tradeoffs — Brandon Rhodes](https://rhodesmill.org/brandon/) (palestras sobre Celery vs alternativas).
- Spec do projeto: `docs/spec_arquitetura.md` §Arquitetura do Backend.

## Notas de revisão

Revisitar **necessariamente** se atingirmos qualquer um dos gatilhos listados acima. Nessa hora, esta ADR será marcada como `Substituído por ADR-XXXX`.
