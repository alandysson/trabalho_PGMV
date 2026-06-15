"""AuthService — orquestração de registro, login, refresh com rotação,
logout e atualização de perfil.

Depende APENAS dos Protocols (`UsuarioRepositoryProtocol`,
`RefreshTokenRepositoryProtocol`, `HashServiceProtocol`,
`JwtServiceProtocol`). Não conhece SQLModel, bcrypt nem jose — quem traz
implementações concretas é o container.

Nenhum log inclui senha ou tokens (nem hash). Eventos vão pro logger
`seguranca` (arquivo separado).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.auth.data.repository_protocol import (
    RefreshTokenRepositoryProtocol,
    UsuarioRepositoryProtocol,
)
from src.auth.domain.entities import AuthTokens
from src.auth.domain.exceptions import (
    CredenciaisInvalidas,
    PossivelInvasaoDetectada,
    SenhaAtualIncorreta,
    TokenExpirado,
    UsuarioInativo,
)
from src.auth.domain.models import RefreshToken, Usuario
from src.auth.security import (
    HashServiceProtocol,
    JwtServiceProtocol,
    gerar_refresh_token_plain,
    hashear_refresh_token,
)


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthService:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryProtocol,
        token_repo: RefreshTokenRepositoryProtocol,
        hash_service: HashServiceProtocol,
        jwt_service: JwtServiceProtocol,
        access_ttl_minutos: int,
        refresh_ttl_dias: int,
        logger_seguranca: logging.Logger,
    ) -> None:
        self._usuario_repo = usuario_repo
        self._token_repo = token_repo
        self._hash = hash_service
        self._jwt = jwt_service
        self._access_ttl_seg = access_ttl_minutos * 60
        self._refresh_ttl = timedelta(days=refresh_ttl_dias)
        self._log = logger_seguranca

    # ----- API pública -----

    def registrar(
        self,
        email: str,
        senha: str,
        nome: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[Usuario, AuthTokens]:
        email_normalizado = email.strip().lower()
        usuario = Usuario(
            email=email_normalizado,
            senha_hash=self._hash.hashear(senha),
            nome=nome.strip(),
        )
        usuario = self._usuario_repo.criar(usuario)
        tokens = self._emitir_par_tokens(usuario, ip=ip, user_agent=user_agent)
        self._log_evento("registro", usuario_id=usuario.id, email=usuario.email, ip=ip)
        return usuario, tokens

    def autenticar(
        self,
        email: str,
        senha: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[Usuario, AuthTokens]:
        email_normalizado = email.strip().lower()
        usuario = self._usuario_repo.buscar_por_email(email_normalizado)
        if usuario is None or not self._hash.verificar(senha, usuario.senha_hash):
            self._log_evento(
                "login_falha",
                email=email_normalizado,
                ip=ip,
                detalhe="credenciais",
            )
            raise CredenciaisInvalidas()
        if not usuario.ativo:
            self._log_evento(
                "login_falha",
                usuario_id=usuario.id,
                email=usuario.email,
                ip=ip,
                detalhe="inativo",
            )
            raise UsuarioInativo()

        tokens = self._emitir_par_tokens(usuario, ip=ip, user_agent=user_agent)
        self._log_evento("login_sucesso", usuario_id=usuario.id, email=usuario.email, ip=ip)
        return usuario, tokens

    def refresh(
        self,
        refresh_token_plain: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[Usuario, AuthTokens]:
        token_hash = hashear_refresh_token(refresh_token_plain)
        registro = self._token_repo.buscar_por_hash(token_hash)
        if registro is None:
            self._log_evento("refresh_falha", ip=ip, detalhe="nao_encontrado")
            raise CredenciaisInvalidas()

        if registro.revogado:
            # Reuso de refresh token revogado = possível invasão.
            # Defesa em profundidade: revogar TODOS os tokens ativos do usuário.
            revogados = self._token_repo.revogar_todos_ativos_do_usuario(
                registro.usuario_id, motivo="seguranca"
            )
            self._log_evento(
                "refresh_reuso_invasao",
                usuario_id=registro.usuario_id,
                ip=ip,
                detalhe=f"revogados={revogados}",
            )
            raise PossivelInvasaoDetectada(usuario_id=registro.usuario_id)

        if registro.expira_em < _agora():
            self._log_evento(
                "refresh_falha",
                usuario_id=registro.usuario_id,
                ip=ip,
                detalhe="expirado",
            )
            raise TokenExpirado()

        usuario = self._usuario_repo.buscar_por_id(registro.usuario_id)
        if usuario is None or not usuario.ativo:
            raise UsuarioInativo()

        novos_tokens, novo_registro_id = self._emitir_par_tokens_com_id(
            usuario, ip=ip, user_agent=user_agent
        )
        self._token_repo.atualizar_ultimo_uso(registro.id)
        self._token_repo.revogar_por_id(
            registro.id, motivo="rotacao", substituido_por_id=novo_registro_id
        )
        self._log_evento("refresh_sucesso", usuario_id=usuario.id, ip=ip)
        return usuario, novos_tokens

    def logout(self, refresh_token_plain: str) -> None:
        token_hash = hashear_refresh_token(refresh_token_plain)
        registro = self._token_repo.buscar_por_hash(token_hash)
        if registro is None or registro.revogado:
            return
        self._token_repo.revogar_por_id(registro.id, motivo="logout")
        self._log_evento("logout", usuario_id=registro.usuario_id)

    def logout_tudo(self, usuario_id: str) -> int:
        revogados = self._token_repo.revogar_todos_ativos_do_usuario(
            usuario_id, motivo="logout_tudo"
        )
        self._log_evento(
            "logout_tudo", usuario_id=usuario_id, detalhe=f"revogados={revogados}"
        )
        return revogados

    def atualizar_perfil(
        self,
        usuario_id: str,
        *,
        nome: str | None = None,
        senha_atual: str | None = None,
        senha_nova: str | None = None,
    ) -> Usuario:
        usuario = self._usuario_repo.buscar_por_id(usuario_id)
        if usuario is None or not usuario.ativo:
            raise UsuarioInativo()

        if senha_nova is not None:
            if senha_atual is None or not self._hash.verificar(senha_atual, usuario.senha_hash):
                raise SenhaAtualIncorreta()
            usuario.senha_hash = self._hash.hashear(senha_nova)
            self._token_repo.revogar_todos_ativos_do_usuario(
                usuario.id, motivo="troca_senha"
            )
            self._log_evento("troca_senha", usuario_id=usuario.id, email=usuario.email)

        if nome is not None:
            usuario.nome = nome.strip()

        return self._usuario_repo.atualizar(usuario)

    # ----- Privados -----

    def _emitir_par_tokens(
        self, usuario: Usuario, *, ip: str | None, user_agent: str | None
    ) -> AuthTokens:
        tokens, _ = self._emitir_par_tokens_com_id(usuario, ip=ip, user_agent=user_agent)
        return tokens

    def _emitir_par_tokens_com_id(
        self, usuario: Usuario, *, ip: str | None, user_agent: str | None
    ) -> tuple[AuthTokens, str]:
        plain = gerar_refresh_token_plain()
        registro = RefreshToken(
            token_hash=hashear_refresh_token(plain),
            usuario_id=usuario.id,
            expira_em=_agora() + self._refresh_ttl,
            ip=ip,
            user_agent=user_agent,
        )
        registro = self._token_repo.criar(registro)
        access = self._jwt.emitir_access(usuario.id, usuario.email)
        tokens = AuthTokens(
            access_token=access,
            refresh_token_plain=plain,
            expires_in=self._access_ttl_seg,
        )
        return tokens, registro.id

    def _log_evento(
        self,
        evento: str,
        *,
        usuario_id: str | None = None,
        email: str | None = None,
        ip: str | None = None,
        detalhe: str | None = None,
    ) -> None:
        partes = [f"evento={evento}"]
        if usuario_id:
            partes.append(f"usuario_id={usuario_id}")
        if email:
            partes.append(f"email={email}")
        if ip:
            partes.append(f"ip={ip}")
        if detalhe:
            partes.append(f"detalhe={detalhe}")
        self._log.info(" | ".join(partes))
