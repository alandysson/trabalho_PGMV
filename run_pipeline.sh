#!/bin/bash
# =========================================================================
# Wrapper de execução da pipeline de vídeos bíblicos.
# Pensado para ser chamado pelo cron diariamente.
#
# Antes de usar, substitua <CAMINHO_DO_PROJETO> abaixo pelo caminho
# absoluto onde este projeto está clonado/copiado.
#
# Exemplo de linha do crontab (rodar todo dia às 06:00):
#   0 6 * * * /caminho/absoluto/videos_biblicos/run_pipeline.sh
# =========================================================================

set -e

cd <CAMINHO_DO_PROJETO> || exit 1

# Ativa o ambiente virtual
source .venv/bin/activate

# Garante que a pasta de logs existe
mkdir -p logs

# Executa a pipeline, redirecionando stdout e stderr para o log diário
python -m src.main >> logs/pipeline.log 2>&1
