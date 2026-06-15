Este é um novo projeto Python que vai virar um backend FastAPI. Anexo
a especificação arquitetural completa que vai guiar TODAS as decisões
de estrutura. Leia com atenção antes de qualquer ação. Você pode acessar na pasta /docs/spec_arquitetura.md

Nesta primeira sessão, NÃO implemente nenhuma feature ainda
. Crie
APENAS a fundação arquitetural do backend:

1. Estrutura de pastas conforme a spec (src/, src/shared/, src/auth/,
   src/videos/, src/temas/, src/pipeline/ — todas vazias com **init**.py)

2. docs/adr/ com:
   - template.md (template MADR)
   - README.md (índice)
   - 0001-organizacao-feature-sliced.md
   - 0002-solid-pragmatico.md
   - 0003-documentacao-via-adrs.md
   - 0004-fastapi-como-framework.md
   - 0005-di-manual-container-leve.md
   - 0006-sqlite-sqlmodel.md
   - 0007-async-via-background-tasks.md
   - 0008-plugin-architecture-temas.md

   Cada ADR com conteúdo real (Contexto / Decisão / Consequências /
   Alternativas consideradas). Mínimo 30 linhas cada.

3. src/container.py (Container manual conforme spec, funcional mas sem
   registros de features ainda)

4. src/main.py (FastAPI app que sobe vazio, com endpoint /health
   retornando {"status": "ok"})

5. src/config.py (Settings com Pydantic Settings lendo do .env)

6. src/shared/database.py, logging.py, exceptions.py — bases mínimas

7. .env.example com todas as variáveis necessárias documentadas

8. requirements.txt inicial (FastAPI, uvicorn, pydantic, pydantic-settings,
   sqlmodel, python-dotenv — nada de auth ainda)

9. .gitignore (.venv, **pycache**, .env, \*.db, storage/, logs/)

10. README.md raiz com seções: Visão geral, Pré-requisitos, Setup,
    Como rodar, Estrutura do projeto, Link para os ADRs

Apresente o plano detalhado antes de criar qualquer arquivo, com
estimativa de linhas por arquivo. Aguarde minha confirmação antes
de executar.
