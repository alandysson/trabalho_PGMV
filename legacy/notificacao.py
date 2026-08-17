"""
Notificação por e-mail via Gmail SMTP.

Duas funções públicas:

  - `enviar_email_post`: ao final de uma execução bem-sucedida, envia o
    roteiro, créditos da Pexels e o MP4 anexado (se ≤ 20 MB).

  - `enviar_email_alerta`: em caso de exceção no pipeline, envia o
    traceback para o e-mail do dono.

Credenciais lidas do .env:
  - GMAIL_USER          → remetente (também usado como login SMTP)
  - GMAIL_APP_PASSWORD  → senha de app (16 caracteres, gerada em
                          myaccount.google.com/apppasswords)
  - GMAIL_DEST          → destinatário (geralmente igual ao GMAIL_USER)
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
TAMANHO_MAX_ANEXO_BYTES = 20 * 1024 * 1024  # 20 MB


def _credenciais() -> tuple[str, str, str]:
    user = os.environ.get("GMAIL_USER")
    senha = os.environ.get("GMAIL_APP_PASSWORD")
    dest = os.environ.get("GMAIL_DEST", user)
    if not user or not senha:
        raise RuntimeError(
            "GMAIL_USER e GMAIL_APP_PASSWORD precisam estar no .env "
            "(senha gerada em myaccount.google.com/apppasswords)"
        )
    return user, senha, dest


def _enviar(msg: EmailMessage) -> None:
    user, senha, _ = _credenciais()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(user, senha)
        smtp.send_message(msg)


def enviar_email_post(
    titulo_historia: str,
    referencia: str,
    roteiro: str,
    creditos: list[str],
    video_path: Path,
    post: dict | None = None,
) -> None:
    """
    E-mail de sucesso, com roteiro pronto para colar na descrição do post.

    Args:
        titulo_historia: ex.: "Davi e Golias".
        referencia: ex.: "1 Samuel 17".
        roteiro: texto completo do roteiro.
        creditos: lista de strings já formatadas, ex.:
                  ["Vídeo por John Doe (Pexels) - https://www.pexels.com/..."]
        video_path: caminho do MP4 final.
        post: dict com 'legenda' e 'hashtags' (lista). Quando passado, gera o
              bloco "COPIAR E COLAR" pronto para a descrição do Kwai/TikTok.
    """
    user, _, dest = _credenciais()

    tamanho = video_path.stat().st_size if video_path.exists() else 0
    anexar = tamanho > 0 and tamanho <= TAMANHO_MAX_ANEXO_BYTES

    creditos_txt = "\n".join(f"  - {c}" for c in creditos) if creditos else "  (nenhum)"

    corpo_partes: list[str] = [
        f"História: {titulo_historia}",
        f"Referência: {referencia}",
        "",
    ]

    if post and post.get("legenda"):
        # Bloco pronto para copiar e colar na descrição da postagem.
        legenda = post["legenda"].strip()
        hashtags = post.get("hashtags") or []
        creditos_inline = "\n".join(creditos) if creditos else ""

        postagem_blocos = [legenda, "", " ".join(hashtags)]
        if creditos_inline:
            postagem_blocos += ["", "Créditos:", creditos_inline]
        postagem_txt = "\n".join(postagem_blocos)

        corpo_partes += [
            "============ POSTAGEM (COPIAR E COLAR) ============",
            postagem_txt,
            "",
        ]

    corpo_partes += [
        "============ ROTEIRO ============",
        roteiro,
        "",
        "============ CRÉDITOS PEXELS (obrigatório no post/bio) ============",
        creditos_txt,
        "",
        "============ ARQUIVO ============",
        f"Caminho local: {video_path}",
        f"Tamanho: {tamanho / (1024 * 1024):.2f} MB",
    ]

    if anexar:
        corpo_partes.append("(MP4 anexado a este e-mail.)")
    else:
        corpo_partes.append(
            "(MP4 NÃO anexado — acima do limite ou arquivo ausente. "
            "Abra a pasta acima manualmente.)"
        )

    corpo_partes += [
        "",
        "============ PRÓXIMOS PASSOS ============",
        "1. Revisar o vídeo antes de publicar.",
        "2. Postar no Kwai e TikTok no formato vertical.",
        "3. Copiar o bloco POSTAGEM acima e colar na descrição.",
    ]

    msg = EmailMessage()
    msg["Subject"] = f"[Vídeos Bíblicos] {titulo_historia}"
    msg["From"] = user
    msg["To"] = dest
    msg.set_content("\n".join(corpo_partes))

    if anexar:
        with open(video_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="video",
                subtype="mp4",
                filename=video_path.name,
            )

    _enviar(msg)


def enviar_email_alerta(titulo: str, traceback_str: str) -> None:
    """E-mail de falha — contém apenas o título do erro e o traceback completo."""
    user, _, dest = _credenciais()

    # Cabeçalhos SMTP não aceitam quebras de linha; achata e trunca.
    titulo_safe = " ".join(titulo.split())[:180] or "erro sem mensagem"

    msg = EmailMessage()
    msg["Subject"] = f"[Vídeos Bíblicos] FALHA: {titulo_safe}"
    msg["From"] = user
    msg["To"] = dest
    msg.set_content(
        "A pipeline de vídeos bíblicos falhou.\n\n"
        f"Resumo: {titulo}\n\n"
        "Traceback completo:\n"
        "---------------------------------\n"
        f"{traceback_str}\n"
    )

    _enviar(msg)


# =========================================================================
# Teste rápido isolado
# =========================================================================
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    print("Enviando e-mail de teste de alerta...")
    enviar_email_alerta(
        "teste de notificação",
        "Traceback (most recent call last):\n  ... (apenas um teste)",
    )
    print("OK. Confira a caixa de entrada.")
