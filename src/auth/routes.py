"""Endpoints HTTP da feature `auth`.

Camada de transporte pura: deserializa request → chama AuthService →
serializa response. Mapeamento de exceções de domínio → HTTPException
acontece APENAS aqui.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter

from src.auth.dependencies import (
    construir_get_auth_service,
    construir_get_session,
    construir_usuario_atual,
    extrair_metadados_request,
)
from src.auth.domain.exceptions import (
    CredenciaisInvalidas,
    PossivelInvasaoDetectada,
    SenhaAtualIncorreta,
    TokenExpirado,
    UsuarioInativo,
    UsuarioJaExiste,
)
from src.auth.domain.models import Usuario
from src.auth.schemas import (
    AtualizarPerfilRequest,
    AuthTokensResponse,
    EuResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegistrarRequest,
    TokensResponse,
    UsuarioResponse,
)
from src.auth.service import AuthService
from src.container import Container


def criar_router(container: Container, limiter: Limiter) -> APIRouter:
    router = APIRouter()

    get_session = construir_get_session(container)
    get_auth_service = construir_get_auth_service(container, get_session)
    usuario_atual = construir_usuario_atual(container, get_session)

    s = container.settings
    rate_login = f"{s.rate_limit_login_tentativas}/{s.rate_limit_login_janela_minutos}minute"

    # ----- registrar -----

    @router.post(
        "/registrar",
        response_model=AuthTokensResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def registrar(
        body: RegistrarRequest,
        request: Request,
        service: AuthService = Depends(get_auth_service),
    ) -> AuthTokensResponse:
        ip, ua = extrair_metadados_request(request)
        try:
            usuario, tokens = service.registrar(
                email=body.email, senha=body.senha, nome=body.nome, ip=ip, user_agent=ua
            )
        except UsuarioJaExiste as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, exc.mensagem)

        return AuthTokensResponse(
            usuario=UsuarioResponse.model_validate(usuario),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token_plain,
            expires_in=tokens.expires_in,
        )

    # ----- login -----

    @router.post("/login", response_model=AuthTokensResponse)
    @limiter.limit(rate_login)
    def login(
        body: LoginRequest,
        request: Request,
        service: AuthService = Depends(get_auth_service),
    ) -> AuthTokensResponse:
        ip, ua = extrair_metadados_request(request)
        try:
            usuario, tokens = service.autenticar(
                email=body.email, senha=body.senha, ip=ip, user_agent=ua
            )
        except (CredenciaisInvalidas, UsuarioInativo):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")

        return AuthTokensResponse(
            usuario=UsuarioResponse.model_validate(usuario),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token_plain,
            expires_in=tokens.expires_in,
        )

    # ----- refresh -----

    @router.post("/refresh", response_model=TokensResponse)
    def refresh(
        body: RefreshRequest,
        request: Request,
        service: AuthService = Depends(get_auth_service),
    ) -> TokensResponse:
        ip, ua = extrair_metadados_request(request)
        try:
            _, tokens = service.refresh(body.refresh_token, ip=ip, user_agent=ua)
        except (
            CredenciaisInvalidas,
            TokenExpirado,
            PossivelInvasaoDetectada,
            UsuarioInativo,
        ) as exc:
            detail = (
                "Sessão invalidada por segurança"
                if isinstance(exc, PossivelInvasaoDetectada)
                else "Credenciais inválidas"
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail)

        return TokensResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token_plain,
            expires_in=tokens.expires_in,
        )

    # ----- logout -----

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        body: LogoutRequest,
        service: AuthService = Depends(get_auth_service),
    ) -> None:
        service.logout(body.refresh_token)

    # ----- logout-tudo -----

    @router.post("/logout-tudo", status_code=status.HTTP_204_NO_CONTENT)
    def logout_tudo(
        usuario: Usuario = Depends(usuario_atual),
        service: AuthService = Depends(get_auth_service),
    ) -> None:
        service.logout_tudo(usuario.id)

    # ----- /eu -----

    def get_contador(session=Depends(get_session)):
        return container.contador_videos(session)

    @router.get("/eu", response_model=EuResponse)
    def eu(
        usuario: Usuario = Depends(usuario_atual),
        contador=Depends(get_contador),
    ) -> EuResponse:
        return EuResponse.de_usuario(
            usuario, videos_gerados=contador.contar_concluidos_do_usuario(usuario.id)
        )

    @router.patch("/eu", response_model=EuResponse)
    def atualizar_eu(
        body: AtualizarPerfilRequest,
        usuario: Usuario = Depends(usuario_atual),
        service: AuthService = Depends(get_auth_service),
        contador=Depends(get_contador),
    ) -> EuResponse:
        try:
            atualizado = service.atualizar_perfil(
                usuario.id,
                nome=body.nome,
                senha_atual=body.senha_atual,
                senha_nova=body.senha_nova,
            )
        except SenhaAtualIncorreta as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.mensagem)
        except UsuarioInativo as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, exc.mensagem)

        return EuResponse.de_usuario(
            atualizado, videos_gerados=contador.contar_concluidos_do_usuario(atualizado.id)
        )

    return router
