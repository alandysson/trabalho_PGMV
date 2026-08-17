# Legacy — Pipeline procedural de geração de vídeos

Esta pasta abriga o **pipeline original** do projeto: 8 scripts Python procedurais que, em sequência, geravam um vídeo curto bíblico por execução (escolha de história → roteiro → narração → legendas → busca de stock → composição FFmpeg → notificação por e-mail).

## Por que está aqui

A partir desta sessão, o projeto está sendo reorganizado como um **backend FastAPI feature-sliced** (ver `docs/spec_arquitetura.md`). O código procedural daqui não será descartado — ele será **portado para `src/pipeline/adapters/`** quando a feature `pipeline` for implementada, transformando cada script atual em um adapter que implementa um Protocol:

| Script aqui | Vira (no futuro) |
|---|---|
| `historias.py`, `roteiro.py` | `src/pipeline/adapters/claude_roteiro_generator.py` |
| `narracao.py` | `src/pipeline/adapters/edge_tts_provider.py` |
| `legendas.py` | `src/pipeline/adapters/whisper_transcription.py` |
| `pexels.py` | `src/pipeline/adapters/pexels_stock_video.py` |
| `video.py` | `src/pipeline/adapters/ffmpeg_video_composer.py` |
| `notificacao.py` | (provavelmente vira um notificador opcional, fora do pipeline) |
| `main.py` | `src/pipeline/orchestrator.py` |

Até essa migração acontecer, o pipeline continua rodável daqui.

## Como rodar (modo legado)

Pré-requisitos: `.env` preenchido com `ANTHROPIC_API_KEY`, `PEXELS_API_KEY`, `GMAIL_*`, FFmpeg no PATH, dependências instaladas (`pip install -r requirements.txt`).

```bash
python -m legacy.main
```

A saída fica em `output/YYYY-MM-DD_HHMM/`. Logs em `logs/pipeline.log`. Detalhes completos (cron, custos, atribuição Pexels, troca de voz, modelos Whisper) estão no histórico do README raiz — `git log -- README.md`.

## Atenção

- Este código **não segue** as regras arquiteturais do backend novo (feature-sliced, DI, Protocols). Não use como referência de estilo pro `src/` novo.
- Quando os adapters forem escritos, esta pasta deve ser removida.
