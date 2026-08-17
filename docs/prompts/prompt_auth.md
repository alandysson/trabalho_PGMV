Vamos implementar a feature `auth` completa do backend, seguindo a
arquitetura já estabelecida no projeto.

Primeiro, anexo o documento de referência que você precisa seguir
rigorosamente:

=== DOCUMENTO: ESPECIFICAÇÃO DE AUTENTICAÇÃO ===

- spec_autenticacao.md

=== TAREFA ===

Implementar a feature `auth` em src/auth/ seguindo o padrão arquitetural
já estabelecido (domain → data → service → security → dependencies →
routes → schemas).

Escopo desta sessão:

1. Modelos de domínio (src/auth/domain/):
   - models.py: SQLModel Usuario e RefreshToken conforme spec_autenticacao
   - entities.py: DTOs internos do domínio (AuthTokens, etc)
   - exceptions.py: CredenciaisInvalidas, UsuarioJaExiste, TokenExpirado,
     TokenRevogado, PossivelInvasaoDetectada

2. Camada de dados (src/auth/data/):
   - repository_protocol.py: UsuarioRepositoryProtocol e
     RefreshTokenRepositoryProtocol (interfaces Protocol)
   - repository_sqlmodel.py: implementações concretas com SQLModel
   - Hash de refresh tokens com SHA-256 antes de persistir (NUNCA em plain)

3. Segurança (src/auth/security.py):
   - HashServiceProtocol + BcryptHashService (rounds vindo do settings)
   - JwtServiceProtocol + JoseJwtService (encode/decode com python-jose)
   - Função pra gerar refresh token aleatório (secrets.token_urlsafe)
   - Função pra hashear refresh token (SHA-256)

4. Serviço (src/auth/service.py):
   - AuthService com métodos: registrar, autenticar, refresh, logout,
     logout_tudo, atualizar_perfil
   - Rotação de refresh token com detecção de invasão (se um refresh
     já revogado for usado, revoga TODOS do usuário)
   - Recebe interfaces no construtor (DI explícita)

5. Schemas Pydantic (src/auth/schemas.py):
   - Request: RegistrarRequest, LoginRequest, RefreshRequest,
     LogoutRequest, AtualizarPerfilRequest
   - Response: UsuarioResponse, AuthTokensResponse, EuResponse
   - Validações: email com EmailStr, senha mínimo 8 chars com letra+número

6. Dependências FastAPI (src/auth/dependencies.py):
   - usuario_atual: Depends que extrai e valida JWT do header Authorization
   - Retorna 401 com header X-Token-Expired: true quando o erro é
     especificamente expiração de token (sinaliza pro app fazer refresh)

7. Rotas (src/auth/routes.py):
   - POST /auth/registrar
   - POST /auth/login (com rate limiting via slowapi: 5 tentativas / 15min)
   - POST /auth/refresh
   - POST /auth/logout
   - POST /auth/logout-tudo
   - GET /auth/eu
   - PATCH /auth/eu
   - Função criar_router(container) que retorna APIRouter

8. Interface pública (src/auth/**init**.py):
   - Re-exporta apenas: AuthService, usuario_atual, Usuario
   - NÃO exporta repositórios, schemas internos, security helpers

9. Atualizar src/container.py:
   - Registrar HashService, JwtService
   - Registrar UsuarioRepository, RefreshTokenRepository
   - Registrar AuthService
   - Manter o padrão de factories já estabelecido

10. Atualizar src/main.py:
    - Incluir router de auth:
      app.include_router(criar_router_auth(container), prefix="/auth", tags=["auth"])

11. Atualizar requirements.txt:
    - python-jose[cryptography]>=3.3.0
    - passlib[bcrypt]>=1.7.4
    - email-validator>=2.1.0
    - slowapi>=0.1.9

12. Atualizar .env.example com as variáveis JWT*\*, BCRYPT_ROUNDS, RATE_LIMIT*\*

13. Criar ADRs faltantes em docs/adr/:
    - 0009-jwt-refresh-token-rotacionado.md
    - 0010-securestore-mobile-sha256-backend.md (parte backend só por enquanto)

14. Atualizar README.md do projeto:
    - Adicionar seção "Autenticação" explicando o modelo
    - Atualizar lista de endpoints disponíveis

REGRAS ARQUITETURAIS NÃO-NEGOCIÁVEIS:

- Nenhum arquivo passa de 300 linhas (refatora se passar)
- AuthService NÃO conhece SQLModel, NÃO conhece bcrypt, NÃO conhece JWT
  (só conhece os Protocols)
- Routes NÃO tem lógica de negócio (só serializa/deserializa e chama service)
- Imports só do **init**.py de outras features (mas auth ainda é a primeira)
- Erros do domínio são exceções específicas (CredenciaisInvalidas),
  convertidas pra HTTPException apenas na camada de routes
- Senha NUNCA aparece em log
- Tokens NUNCA aparecem em log (nem hash)
- Logs estruturados em logs/seguranca.log pra eventos de auth

ENTREGA ESPERADA:

1. Apresente o plano detalhado de implementação ANTES de criar qualquer
   arquivo, incluindo:
   - Lista de arquivos a criar/modificar
   - Ordem de criação
   - Estimativa de linhas por arquivo
   - Quais ADRs vão ser criadas
2. Aguarde minha confirmação explícita
3. Após implementar, me forneça:
   - Resumo do que foi feito
   - Comandos curl prontos pra testar todos os 7 endpoints em sequência
   - Como rodar migrações (se houver)
   - Lista de checks que eu devo fazer antes de seguir
