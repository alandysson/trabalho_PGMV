# Backend: API REST para Geração de Vídeos Narrados

## Contexto

Tenho um projeto Python funcional (`videos_biblicos`) que gera vídeos curtos narrados de histórias bíblicas (formato faceless: voz IA + vídeos stock do Pexels + legendas sincronizadas + música de fundo). O pipeline executa via linha de comando e envia o resultado por e-mail.

Agora preciso **transformar esse projeto numa API REST (FastAPI)** que será consumida por um aplicativo mobile React Native (Expo). Também preciso **expandir o escopo de temas**: histórias bíblicas continua como tema principal, mas a arquitetura precisa suportar outros temas (mitologia, curiosidades históricas, fábulas) via plugin architecture.

Este projeto é trabalho acadêmico de Sistemas de Informação (disciplina de dispositivos móveis), então **qualidade de arquitetura, documentação e legibilidade são tão importantes quanto funcionalidade**.

**Autenticação**: o backend implementa autenticação completa com JWT (access token) + refresh token rotacionado, com sistema de usuários, login, registro e logout. **A spec detalhada de autenticação está no documento separado `spec_autenticacao.md`** — implementar conforme aquele documento ao chegar nessa parte. Esta spec assume que `Usuario` e `RefreshToken` existem como modelos, e que rotas de vídeos exigem usuário autenticado via dependency `usuario_atual`.

---

## Visão geral da nova arquitetura

```
┌──────────────────────────────────────────────┐
│              FastAPI Backend                 │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │     Auth Layer (JWT + Refresh)         │  │
│  │  POST /auth/registrar                  │  │
│  │  POST /auth/login                      │  │
│  │  POST /auth/refresh                    │  │
│  │  POST /auth/logout                     │  │
│  │  GET  /auth/eu                         │  │
│  │  (detalhe em spec_autenticacao.md)     │  │
│  └────────────────┬───────────────────────┘  │
│                   │                          │
│  ┌────────────────▼───────────────────────┐  │
│  │   Middleware: usuario_atual (Depends)  │  │
│  └────────────────┬───────────────────────┘  │
│                   │                          │
│  ┌────────────────▼───────────────────────┐  │
│  │      Endpoints REST (autenticados)     │  │
│  │  GET  /temas               (público)   │  │
│  │  GET  /temas/{tema_id}     (público)   │  │
│  │  POST /videos/gerar        (auth)      │  │
│  │  GET  /videos/{job_id}/... (auth)      │  │
│  │  GET  /videos              (auth)      │  │
│  └─────────────────┬──────────────────────┘  │
│                    │                         │
│  ┌─────────────────▼──────────────────────┐  │
│  │      Job Manager (assíncrono)          │  │
│  │  - BackgroundTasks do FastAPI          │  │
│  │  - Persistência de status em SQLite    │  │
│  │  - Jobs vinculados a usuario_id        │  │
│  └─────────────────┬──────────────────────┘  │
│                    │                         │
│  ┌─────────────────▼──────────────────────┐  │
│  │      Plugin Architecture (Temas)       │  │
│  │  ├── BaseTemaProvider (abstract)       │  │
│  │  ├── HistoriasBiblicasProvider         │  │
│  │  ├── MitologiaProvider                 │  │
│  │  ├── CuriosidadesProvider              │  │
│  │  └── FabulasProvider                   │  │
│  └─────────────────┬──────────────────────┘  │
│                    │                         │
│  ┌─────────────────▼──────────────────────┐  │
│  │     Pipeline de Geração (compartilhado)│  │
│  │  roteiro → tts → whisper → pexels      │  │
│  │  → ffmpeg → vídeo final                │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

---

## Estrutura de pastas desejada

```
videos_backend/
├── .env / .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml                     # OPCIONAL, configuração formatadores
├── assets/
│   └── music/                         # MP3s instrumentais
├── storage/
│   ├── videos/                        # MP4s gerados
│   └── temp/                          # arquivos temporários por job
├── logs/
├── data/
│   └── jobs.db                        # SQLite de status dos jobs
└── src/
    ├── __init__.py
    ├── main.py                        # FastAPI app + endpoints
    ├── config.py                      # Settings (Pydantic Settings)
    ├── models.py                      # Pydantic models (request/response)
    ├── database.py                    # SQLite setup + ORM (SQLModel)
    ├── job_manager.py                 # Lógica de jobs assíncronos
    │
    ├── auth/                           # Camada de autenticação (ver spec_autenticacao.md)
    │   ├── __init__.py
    │   ├── modelos.py                  # Usuario, RefreshToken (SQLModel)
    │   ├── rotas.py                    # Endpoints /auth/*
    │   ├── servico.py                  # Lógica: gerar tokens, validar, rotacionar
    │   ├── seguranca.py                # bcrypt, JWT encode/decode
    │   └── dependencias.py             # Depends(usuario_atual)
    │
    ├── temas/
    │   ├── __init__.py
    │   ├── base.py                    # BaseTemaProvider (abstract)
    │   ├── registry.py                # Registro de temas disponíveis
    │   ├── historias_biblicas.py      # Tema principal
    │   ├── mitologia.py
    │   ├── curiosidades.py
    │   └── fabulas.py
    │
    └── pipeline/
        ├── __init__.py
        ├── roteiro.py                 # Geração de roteiro com Claude
        ├── narracao.py                # TTS com edge-tts
        ├── legendas.py                # Transcrição com faster-whisper
        ├── pexels.py                  # Busca/download vídeos stock
        └── video.py                   # Composição FFmpeg
```

---

## Especificação dos endpoints REST

### `GET /temas`

Lista todos os temas disponíveis com metadados de exibição.

**Resposta (200):**
```json
{
  "temas": [
    {
      "id": "historias_biblicas",
      "nome": "Histórias com Deus",
      "descricao": "Histórias bíblicas narradas em 1 minuto",
      "icone": "📖",
      "cor_destaque": "#1F3864",
      "exemplos": ["Davi e Golias", "Daniel na cova", "Jonas e a baleia"]
    },
    {
      "id": "mitologia",
      "nome": "Mitos Antigos",
      "descricao": "Mitologia grega, nórdica e egípcia",
      "icone": "⚡",
      "cor_destaque": "#8B0000",
      "exemplos": ["Prometeu", "Thor e Loki", "Ísis e Osíris"]
    },
    {
      "id": "curiosidades",
      "nome": "Você Sabia?",
      "descricao": "Curiosidades históricas e científicas",
      "icone": "💡",
      "cor_destaque": "#D4A843",
      "exemplos": ["Por que o céu é azul", "Origem do café", "Quem foi Cleópatra"]
    },
    {
      "id": "fabulas",
      "nome": "Fábulas",
      "descricao": "Histórias clássicas com lições de vida",
      "icone": "🦊",
      "cor_destaque": "#2E7D32",
      "exemplos": ["A raposa e as uvas", "Lebre e tartaruga", "O lobo e o cordeiro"]
    }
  ]
}
```

### `GET /temas/{tema_id}`

Detalhes de um tema específico (para tela de informações no app).

### `POST /videos/gerar`

Dispara geração assíncrona de um vídeo.

**Request body:**
```json
{
  "tema_id": "historias_biblicas",
  "preferencias": {
    "voz": "pt-BR-AntonioNeural",
    "duracao_alvo": 60
  }
}
```

**Resposta (202 Accepted):**
```json
{
  "job_id": "j_a1b2c3d4",
  "status": "pendente",
  "criado_em": "2026-05-28T15:30:00Z",
  "estimativa_segundos": 120
}
```

A geração roda em background via `BackgroundTasks` do FastAPI. O endpoint retorna imediatamente.

### `GET /videos/{job_id}/status`

Verifica o status de um job em andamento. **Este é o endpoint que o app vai chamar em polling**, então precisa ser rápido.

**Resposta (200):**
```json
{
  "job_id": "j_a1b2c3d4",
  "status": "processando",
  "etapa_atual": "buscando_videos_pexels",
  "progresso_pct": 65,
  "etapas_concluidas": ["escolha_historia", "roteiro", "narracao", "transcricao"],
  "tempo_decorrido_segundos": 47,
  "erro": null
}
```

Status possíveis: `pendente`, `processando`, `concluido`, `falhou`.

Etapas: `escolha_historia`, `roteiro`, `narracao`, `transcricao`, `buscando_videos_pexels`, `compondo_video`, `finalizado`.

### `GET /videos/{job_id}`

Detalhes completos do vídeo gerado (após `status=concluido`).

**Resposta (200):**
```json
{
  "job_id": "j_a1b2c3d4",
  "tema_id": "historias_biblicas",
  "titulo": "Davi e Golias",
  "subtitulo": "1 Samuel 17",
  "roteiro": "Texto completo da narração...",
  "duracao_segundos": 62,
  "criado_em": "2026-05-28T15:30:00Z",
  "url_arquivo": "/videos/j_a1b2c3d4/arquivo",
  "tamanho_bytes": 14523678,
  "thumbnail_url": "/videos/j_a1b2c3d4/thumbnail",
  "creditos": [
    {"fotografo": "John Doe", "url": "https://www.pexels.com/@johndoe"}
  ]
}
```

### `GET /videos/{job_id}/arquivo`

Retorna o MP4 binário com `Content-Type: video/mp4` e headers de cache adequados. Suporta requests parciais (HTTP Range) para o player do app conseguir fazer seek.

### `GET /videos/{job_id}/thumbnail`

Retorna um JPEG com um frame do vídeo (gerado durante a composição usando FFmpeg). Tamanho ~400x711 (proporção 9:16 do vídeo final).

### `GET /videos`

Lista vídeos já gerados, com paginação.

**Query params:** `limit`, `offset`, `tema_id` (filtro opcional), `apenas_concluidos` (boolean, default true).

**Resposta (200):**
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "videos": [
    { "job_id": "...", "titulo": "...", "tema_id": "...", "duracao_segundos": 62, "thumbnail_url": "..." }
  ]
}
```

---

## Plugin Architecture: como os temas funcionam

### `src/temas/base.py`

Define a interface abstrata que cada tema deve implementar:

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class HistoriaEscolhida(BaseModel):
    id: str                    # ex: "davi_e_golias"
    titulo: str                # "Davi e Golias"
    referencia: str            # "1 Samuel 17" (ou equivalente em outros temas)
    personagens: list[str]
    tema_central: str          # "coragem", "fé", etc

class BaseTemaProvider(ABC):
    """Interface abstrata para provedores de tema."""
    
    @property
    @abstractmethod
    def tema_id(self) -> str: ...
    
    @property
    @abstractmethod
    def nome_exibicao(self) -> str: ...
    
    @abstractmethod
    def metadata(self) -> dict:
        """Retorna metadados de exibição (icone, cor, exemplos, etc)"""
    
    @abstractmethod
    def escolher_historia(self, ids_recentes: list[str]) -> HistoriaEscolhida:
        """Escolhe uma história deste tema, evitando repetir as recentes."""
    
    @abstractmethod
    def system_prompt_roteiro(self) -> str:
        """System prompt para guiar o Claude a gerar o roteiro neste tema."""
    
    @abstractmethod
    def restricoes_visuais(self) -> dict:
        """Restrições/preferências pra busca de vídeos no Pexels.
        Ex: período histórico, paleta de cores, ambientação."""
```

### Cada tema implementa essa interface

**`historias_biblicas.py`**: usa a lista de ~50 histórias bíblicas e o system prompt teológico (sem prosperidade, sem denominação).

**`mitologia.py`**: usa lista de ~40 mitos (gregos, nórdicos, egípcios). System prompt enfatiza tom épico, respeitoso com a cultura original.

**`curiosidades.py`**: pool de tópicos pré-definidos + sugestões geradas por Claude. System prompt pede tom didático, com fato surpreendente nos 3 primeiros segundos.

**`fabulas.py`**: lista de fábulas clássicas. System prompt pede final claro com "moral da história".

### `src/temas/registry.py`

```python
TEMAS_DISPONIVEIS = {
    "historias_biblicas": HistoriasBiblicasProvider(),
    "mitologia": MitologiaProvider(),
    "curiosidades": CuriosidadesProvider(),
    "fabulas": FabulasProvider(),
}

def obter_tema(tema_id: str) -> BaseTemaProvider:
    if tema_id not in TEMAS_DISPONIVEIS:
        raise ValueError(f"Tema '{tema_id}' não existe")
    return TEMAS_DISPONIVEIS[tema_id]

def listar_temas() -> list[dict]:
    return [provider.metadata() for provider in TEMAS_DISPONIVEIS.values()]
```

---

## Job Manager: processamento assíncrono

### Por que precisa ser assíncrono

Gerar um vídeo leva 1-3 minutos. O endpoint HTTP não pode segurar a conexão por todo esse tempo (timeout, instabilidade móvel, etc). A solução é processar em background e o cliente faz polling.

### Implementação

Use `BackgroundTasks` do FastAPI para enfileirar a tarefa e processar em outro thread/event loop. Status persistido em **SQLite via SQLModel** (mais simples que ter Redis/Celery pra um trabalho acadêmico individual, e suficiente para 1-2 vídeos em paralelo).

### Tabela `jobs` (SQLite):

```python
class Job(SQLModel, table=True):
    id: str = Field(primary_key=True)      # "j_xxxxx"
    tema_id: str
    status: str                            # pendente/processando/concluido/falhou
    etapa_atual: str | None
    progresso_pct: int = 0
    titulo: str | None = None
    subtitulo: str | None = None
    roteiro: str | None = None
    duracao_segundos: float | None = None
    caminho_arquivo: str | None = None
    caminho_thumbnail: str | None = None
    tamanho_bytes: int | None = None
    creditos_json: str | None = None       # JSON serializado dos créditos Pexels
    erro: str | None = None
    criado_em: datetime
    atualizado_em: datetime
    tempo_total_segundos: float | None = None
```

### Função `processar_job(job_id: str)`

Atualiza o status na tabela conforme avança nas etapas:

```python
async def processar_job(job_id: str):
    job = obter_job(job_id)
    try:
        atualizar(job, status="processando", etapa="escolha_historia", progresso=5)
        provider = obter_tema(job.tema_id)
        historia = provider.escolher_historia(ids_recentes_do_tema(job.tema_id))
        
        atualizar(job, etapa="roteiro", progresso=15)
        roteiro = gerar_roteiro(historia, provider.system_prompt_roteiro())
        
        atualizar(job, etapa="narracao", progresso=30, titulo=historia.titulo, subtitulo=historia.referencia)
        audio_path = gerar_audio(roteiro)
        
        atualizar(job, etapa="transcricao", progresso=45)
        palavras = transcrever(audio_path)
        
        atualizar(job, etapa="buscando_videos_pexels", progresso=60)
        cenas = gerar_cenas(roteiro, num_cenas=6, restricoes=provider.restricoes_visuais())
        videos = buscar_e_baixar_cenas(cenas)
        
        atualizar(job, etapa="compondo_video", progresso=85)
        video_final, thumbnail = montar_video(...)
        
        atualizar(
            job, status="concluido", etapa="finalizado", progresso=100,
            caminho_arquivo=str(video_final), caminho_thumbnail=str(thumbnail),
            roteiro=roteiro, duracao_segundos=duracao(audio_path),
            tamanho_bytes=video_final.stat().st_size,
            creditos_json=json.dumps([v.creditos for v in videos]),
        )
    except Exception as e:
        atualizar(job, status="falhou", erro=f"{type(e).__name__}: {e}")
        raise
```

---

## Configuração e segurança

### `.env.example`

```
# APIs
ANTHROPIC_API_KEY=sk-ant-...
PEXELS_API_KEY=...

# Servidor
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development                  # development / production
CORS_ORIGINS=http://localhost:8081,exp://...  # origens permitidas (Expo dev)

# Storage
STORAGE_DIR=./storage
DATABASE_URL=sqlite:///./data/jobs.db

# Pipeline defaults
TTS_VOICE=pt-BR-AntonioNeural
WHISPER_MODEL=base
MAX_JOBS_PARALELOS=2

# Autenticação (ver spec_autenticacao.md)
JWT_SECRET_KEY=                          # gerar com: python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12
RATE_LIMIT_LOGIN_TENTATIVAS=5
RATE_LIMIT_LOGIN_JANELA_MINUTOS=15
```

### Autenticação

**JWT (access token de 15min) + Refresh Token rotacionado (30 dias)** com sistema completo de usuários. Implementação detalhada em **`spec_autenticacao.md`**.

Pontos críticos pra esta spec:

- Todas as rotas de vídeos (`/videos/*`) exigem `Depends(usuario_atual)`
- Rotas de temas (`GET /temas`, `GET /temas/{id}`) permanecem **públicas** (catálogo)
- Jobs ficam vinculados ao `usuario_id`; `GET /videos` filtra automaticamente
- `GET /videos/{job_id}` retorna 403 se o job pertencer a outro usuário
- Health check e Swagger UI também permanecem públicos

### CORS

Configurar `CORSMiddleware` permitindo origens listadas em `CORS_ORIGINS`. Pra desenvolvimento com Expo, incluir `exp://` e `http://localhost:8081`.

---

## Logs e observabilidade

- Logger Python padrão com formato estruturado (timestamp, nível, módulo, mensagem)
- Logs em arquivo (`logs/api.log`) com rotação
- Logs por job num arquivo separado (`logs/jobs/{job_id}.log`) — facilita debug quando um job específico falha
- Endpoint `GET /health` retornando status do servidor (200 sempre se vivo)
- Endpoint `GET /metrics` (opcional, simples): total de jobs criados/concluídos/falhados nas últimas 24h

---

## Dependências (requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
sqlmodel>=0.0.16
python-multipart>=0.0.6
anthropic>=0.40.0
edge-tts>=6.1.0
faster-whisper>=1.0.0
requests>=2.31.0
python-dotenv>=1.0.0
mutagen>=1.47.0
aiofiles>=23.2.0

# Autenticação (ver spec_autenticacao.md)
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
email-validator>=2.1.0
slowapi>=0.1.9
```

---

## README.md (estrutura desejada)

1. Visão geral do projeto e arquitetura
2. Pré-requisitos (Python 3.10+, FFmpeg instalado, contas Anthropic + Pexels)
3. Instalação passo a passo
4. Configuração do `.env`
5. Como rodar em desenvolvimento (`uvicorn src.main:app --reload`)
6. Documentação dos endpoints (apontar pro Swagger UI em `/docs`)
7. Diagrama da arquitetura (em ASCII art ou descrição)
8. Plugin Architecture: como adicionar um novo tema (passo a passo)
9. Decisões de arquitetura: por que SQLite, por que polling em vez de WebSocket, por que sem Celery
10. Deploy: instruções pra Fly.io e Render
11. Limitações conhecidas

---

## O que NÃO fazer

- Não implementar OAuth social (Google/Apple) — autenticação local com email/senha é suficiente (extensão futura)
- Não usar Celery/Redis (BackgroundTasks do FastAPI suficientes pro escopo)
- Não implementar streaming de progresso via WebSocket (polling é mais simples e didático)
- Não criar interface web — só API REST
- Não usar PostgreSQL (SQLite atende e simplifica setup)
- Não implementar verificação de e-mail por enquanto (placeholder no modelo)

---

## Entrega esperada

1. Apresente primeiro um **plano de implementação** com ordem dos arquivos a criar
2. Aguarde confirmação antes de codificar
3. Após criar, me dê: resumo, checklist de pré-requisitos, comando exato pra primeiro teste (curl pegando lista de temas + curl disparando job + curl checando status)
4. Tempo estimado de implementação total
