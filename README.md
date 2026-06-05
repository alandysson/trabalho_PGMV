# Vídeos Bíblicos — Pipeline Automatizado

Geração diária e automática de vídeos curtos (50-70s, formato vertical 1080x1920)
narrando histórias bíblicas, prontos para publicação manual no **Kwai** e
**TikTok**.

Formato "faceless": narração + vídeos stock como fundo + legendas
sincronizadas estilo karaoke + música instrumental discreta. Tudo orquestrado
em Python, com a Anthropic (Claude) escolhendo a história e escrevendo o
roteiro, edge-tts gerando a voz, faster-whisper alinhando as legendas
palavra-por-palavra, Pexels fornecendo os clipes de fundo e FFmpeg
compondo o vídeo final.

---

## 1. O que é

Uma pipeline sequencial de 8 etapas. Cada execução produz uma pasta nova em
`output/YYYY-MM-DD_HHMM/` contendo:

- `narracao.mp3` — áudio gerado por TTS
- `legendas.ass` — legendas karaoke palavra-a-palavra
- `stock/cena_XX_*.mp4` — vídeos baixados do Pexels
- `video_final.mp4` — o entregável
- `metadata.json` — tudo que foi feito (história, roteiro, cenas, créditos,
  duração, voz, tempo de execução)

Um e-mail é enviado ao final com o roteiro pronto para colar na descrição
do post, a lista de créditos da Pexels (obrigatória pelos termos de uso) e
o MP4 anexado (se ≤ 20 MB).

---

## 2. Pré-requisitos

- **Python 3.10+**
- **FFmpeg** instalado e no PATH (`brew install ffmpeg` no macOS,
  `apt install ffmpeg` no Linux)
- **Conta Anthropic** com crédito → https://console.anthropic.com/
- **Conta Pexels** (gratuita) → https://www.pexels.com/api/
- **Conta Gmail** com 2FA ativado e **senha de app** gerada →
  https://myaccount.google.com/apppasswords

---

## 3. Instalação passo a passo

```bash
# 1. Entre na pasta do projeto
cd /caminho/para/videos_biblicos

# 2. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Copie o template de variáveis de ambiente
cp .env.example .env

# 5. Edite o .env e preencha suas chaves
# (use seu editor favorito: nano, vim, code, etc.)
```

> **Primeira execução do faster-whisper**: baixa o modelo (`base` ≈ 150 MB)
> automaticamente para `~/.cache/huggingface/`. Próximas execuções já usam
> o cache.

---

## 4. Configuração das chaves

### Anthropic (`ANTHROPIC_API_KEY`)
1. Acesse https://console.anthropic.com/
2. Settings → API Keys → Create Key
3. Copie a chave (começa com `sk-ant-`) e cole no `.env`

### Pexels (`PEXELS_API_KEY`)
1. Acesse https://www.pexels.com/api/
2. Faça login → "Your API Key" aparece direto no painel
3. Cole no `.env`. Plano gratuito: 200 req/h, 20.000/mês — sobra muito.

### Gmail (`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GMAIL_DEST`)
1. Ative 2FA na sua conta Google (obrigatório)
2. Acesse https://myaccount.google.com/apppasswords
3. Crie uma senha de app chamada "videos_biblicos" — copie os 16 caracteres
4. `GMAIL_USER` = seu e-mail; `GMAIL_APP_PASSWORD` = a senha de app;
   `GMAIL_DEST` = onde quer receber (geralmente o próprio e-mail)

---

## 5. Adicionar músicas de fundo

A pipeline sorteia uma trilha de `assets/music/*.mp3` por execução. **Se a
pasta estiver vazia, o vídeo é gerado sem música — sem falhar.**

Recomendado adicionar **10 a 15 trilhas instrumentais** (sem vocais), de
2 a 4 minutos cada, em estilos contemplativos/épicos. Boas fontes
gratuitas com licença livre:

- **Pixabay Music** → https://pixabay.com/music/ (filtrar por "cinematic",
  "ambient", "epic")
- **YouTube Audio Library** → https://www.youtube.com/audiolibrary (filtrar
  por "Sem atribuição obrigatória")
- **Free Music Archive** → https://freemusicarchive.org/

Coloque os arquivos `.mp3` direto em `assets/music/`. Nada mais.

---

## 6. Como rodar manualmente

```bash
cd /caminho/para/videos_biblicos
source .venv/bin/activate
python -m src.main
```

Saída esperada (exemplo):

```
[1/8] Escolhendo história...
  → Davi e Golias (1 Samuel 17)
[2/8] Gerando roteiro (130-160 palavras)...
  → 148 palavras | título: O Gigante Caiu
[3/8] Dividindo em cenas e gerando queries (6 cenas)...
  cena 1: desert valley wide
  cena 2: ancient warrior armor
  ...
[4/8] Gerando narração com edge-tts (voz: pt-BR-AntonioNeural)...
[5/8] Transcrevendo áudio com Whisper (modelo: base)...
[6/8] Buscando vídeos no Pexels (6 cenas)...
[7/8] Compondo vídeo final com FFmpeg...
[8/8] Enviando notificação por e-mail...
✓ Concluído em 142.3s. Vídeo: output/2026-05-18_1430/video_final.mp4
```

### Testar módulos isoladamente

Cada módulo tem um `if __name__ == "__main__":` para teste rápido:

```bash
python -m src.historias       # pede uma escolha ao Claude
python -m src.roteiro         # gera roteiro + cenas de Davi e Golias
python -m src.narracao        # gera um MP3 curto em /tmp
python -m src.pexels          # busca "desert sunset silhouette" e baixa
python -m src.legendas /tmp/teste_narracao.mp3
python -m src.notificacao     # envia um e-mail de teste
```

---

## 7. Automação via cron

1. Edite o `run_pipeline.sh` substituindo `<CAMINHO_DO_PROJETO>` pelo caminho
   absoluto onde está este projeto.

2. Abra o crontab:
   ```bash
   crontab -e
   ```

3. Adicione uma linha (exemplo: rodar todo dia às 06:00):
   ```cron
   0 6 * * * /caminho/absoluto/videos_biblicos/run_pipeline.sh
   ```

Os logs ficam em `logs/pipeline.log` (append a cada execução). Falhas
disparam e-mail automático com o traceback.

---

## 8. Estrutura do projeto

```
videos_biblicos/
├── .env                       # suas chaves (NÃO commitar)
├── .env.example               # template
├── .gitignore
├── README.md                  # este arquivo
├── requirements.txt
├── run_pipeline.sh            # wrapper para cron
├── historias_recentes.json    # gerado automaticamente (últimas 20 histórias)
├── assets/
│   └── music/                 # você adiciona os MP3s instrumentais
├── output/
│   └── 2026-05-18_1430/       # uma pasta por execução
│       ├── narracao.mp3
│       ├── legendas.ass
│       ├── stock/
│       ├── video_final.mp4
│       └── metadata.json
├── logs/
│   └── pipeline.log
└── src/
    ├── __init__.py
    ├── historias.py           # ~50 histórias de referência + escolha via Claude
    ├── roteiro.py             # roteiro + divisão em cenas + queries Pexels
    ├── narracao.py            # TTS via edge-tts
    ├── legendas.py            # transcrição word-level + .ass karaoke
    ├── pexels.py              # busca e download de vídeos stock
    ├── video.py               # composição FFmpeg
    ├── notificacao.py         # e-mail SMTP Gmail
    └── main.py                # orquestrador das 8 etapas
```

---

## 9. Custos estimados (por vídeo)

| Serviço | Custo aproximado |
|---|---|
| Anthropic — Haiku (escolha história) | ~US$ 0,0005 |
| Anthropic — Sonnet (roteiro + cenas) | ~US$ 0,005 |
| Pexels (vídeos stock) | Grátis |
| edge-tts (Microsoft) | Grátis |
| faster-whisper (local, CPU) | Grátis (só CPU/eletricidade) |
| Gmail SMTP | Grátis |
| **Total por execução** | **~US$ 0,01 (~R$ 0,05)** |

Rodando uma vez por dia: ~R$ 1,50/mês. Bem dentro de qualquer hobby budget.

---

## 10. Atribuição obrigatória da Pexels API

Os termos de uso da Pexels exigem **crédito visível** aos fotógrafos/cineastas
sempre que o conteúdo for redistribuído. A pipeline já cuida disso:

- Cada execução registra os autores no `metadata.json` (campo
  `creditos_pexels`).
- O e-mail enviado ao final contém o bloco pronto para colar na descrição
  do post ou na bio do canal:

  ```
  Vídeos por John Doe (Pexels) - https://www.pexels.com/...
  Vídeos por Jane Smith (Pexels) - https://www.pexels.com/...
  ```

**É sua responsabilidade colar esses créditos** ao publicar. Se a descrição
da rede não couber, ponha na bio do perfil — também atende.

---

## 11. Limitações conhecidas e próximos passos

### Hoje
- Não publica automaticamente — a postagem no Kwai/TikTok é manual.
- Sem interface web ou GUI.
- Sem testes unitários (cada módulo tem só um teste manual via
  `if __name__ == "__main__":`).
- Whisper roda em CPU — em máquinas modestas, a etapa 5 pode ser a mais
  lenta do pipeline (~30-60s para 60s de áudio).

### Possíveis evoluções
- **Voz premium**: trocar edge-tts por **ElevenLabs** para vozes mais
  expressivas (custo: ~US$ 0,05 por vídeo).
- **Imagens IA**: para cenas que não existem no acervo Pexels (e.g.
  "menino segurando funda no vale"), gerar via **Replicate/SDXL** ou
  **Imagen** e usar como still com Ken Burns.
- **Pontuação no roteiro**: alimentar o modelo com feedback de qual roteiro
  performou melhor nas redes para melhorar a curadoria automática.
- **Publicação automática**: quando o Kwai/TikTok liberarem APIs públicas,
  integrar `notificacao.py` com upload direto.
- **Variação de vozes**: alternar entre vozes masculina e feminina por
  história, dependendo do narrador implícito.

---

Feito com Python, FFmpeg, Claude, edge-tts, faster-whisper e Pexels.
