# Especificação de Arquitetura — Sistema Histórias com Deus

> Documento de referência arquitetural. Define organização modular, princípios SOLID aplicados, injeção de dependências explícita e estrutura de ADRs (Architecture Decision Records) para backend FastAPI e app React Native (Expo).

---

## Sumário

1. [Princípios norteadores](#princípios-norteadores)
2. [Arquitetura do Backend](#arquitetura-do-backend)
3. [Arquitetura do App Mobile](#arquitetura-do-app-mobile)
4. [Injeção de Dependências](#injeção-de-dependências)
5. [SOLID na prática](#solid-na-prática)
6. [Estrutura de ADRs](#estrutura-de-adrs)
7. [Como o Claude Code deve implementar](#como-o-claude-code-deve-implementar)

---

## Princípios norteadores

Estas são as regras que valem pra **backend e app**, e devem ser respeitadas em qualquer decisão:

### 1. Organização por domínio, não por tipo técnico

**RUIM** (organização por tipo):
```
src/
├── controllers/
├── services/
├── repositories/
└── models/
```

**BOM** (organização por feature/domínio):
```
src/
├── auth/
│   ├── routes.py
│   ├── service.py
│   ├── repository.py
│   └── models.py
├── videos/
└── temas/
```

Por quê: ao alterar a funcionalidade de "vídeos", você abre **uma pasta** e tem tudo. Não precisa caçar arquivos espalhados em 4 pastas.

### 2. Dependa de abstrações, não de implementações concretas

Toda dependência externa (HTTP, banco, storage, APIs) deve ser **injetada via interface/protocol**. O código de domínio não importa de bibliotecas concretas — recebe instâncias prontas.

### 3. Cada módulo tem uma fronteira clara

Módulos se comunicam por **interfaces públicas** definidas (um `__init__.py` no backend, um `index.ts` no mobile que re-exporta o público). Nada de importar arquivos internos de outro módulo.

### 4. Inversão de Dependência onde agrega valor

Vamos aplicar DI nos pontos críticos: **infraestrutura externa** (banco, HTTP, IA, storage). Não vamos injetar tudo dogmaticamente — usaremos bom senso.

### 5. Decisões importantes têm ADR

Tudo que mereceu uma escolha consciente entre alternativas vira ADR. Isso garante que daqui a 6 meses você (e quem ler) entenda o "porquê".

### 6. Não sobre-engenheirar

A regra de ouro: **se uma camada não está agregando valor mensurável, ela não deve existir**. Vamos justificar cada camada na ADR correspondente.

---

## Arquitetura do Backend

### Estrutura de pastas

```
videos_backend/
├── docs/
│   └── adr/                              # ADRs (ver seção dedicada)
│       ├── README.md                     # índice
│       ├── 0001-feature-sliced-organization.md
│       ├── 0002-fastapi-as-framework.md
│       ├── ...
│       └── template.md
├── src/
│   ├── __init__.py
│   ├── main.py                           # FastAPI app + wiring (composition root)
│   ├── config.py                         # Settings global (Pydantic Settings)
│   │
│   ├── shared/                           # Código compartilhado entre features
│   │   ├── __init__.py
│   │   ├── database.py                   # Engine SQLModel, session factory
│   │   ├── exceptions.py                 # Exceptions base do projeto
│   │   ├── logging.py                    # Setup de logging estruturado
│   │   └── types.py                      # Tipos comuns (IDs, datetime helpers)
│   │
│   ├── container.py                      # Container manual de DI (ver seção)
│   │
│   ├── auth/                             # FEATURE: Autenticação
│   │   ├── __init__.py                   # Interface pública (re-exports)
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                 # Usuario, RefreshToken (SQLModel)
│   │   │   ├── entities.py               # DTOs/Value Objects do domínio
│   │   │   └── exceptions.py             # CredenciaisInvalidas, etc
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── repository_protocol.py    # Interface (Protocol)
│   │   │   └── repository_sqlmodel.py    # Implementação concreta
│   │   ├── service.py                    # AuthService (lógica de negócio)
│   │   ├── security.py                   # bcrypt, JWT encode/decode
│   │   ├── dependencies.py               # FastAPI Depends(usuario_atual)
│   │   ├── routes.py                     # Endpoints /auth/*
│   │   └── schemas.py                    # Pydantic request/response
│   │
│   ├── videos/                           # FEATURE: Vídeos
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── models.py                 # Job (SQLModel)
│   │   │   └── entities.py
│   │   ├── data/
│   │   │   ├── repository_protocol.py
│   │   │   ├── repository_sqlmodel.py
│   │   │   ├── storage_protocol.py       # Interface pra storage de arquivos
│   │   │   └── storage_filesystem.py     # Implementação local
│   │   ├── service.py                    # VideosService
│   │   ├── job_processor.py              # Processamento async
│   │   ├── routes.py
│   │   └── schemas.py
│   │
│   ├── temas/                            # FEATURE: Temas
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── provider_protocol.py      # BaseTemaProvider (ABC)
│   │   │   └── entities.py
│   │   ├── providers/
│   │   │   ├── historias_biblicas.py
│   │   │   ├── mitologia.py
│   │   │   ├── curiosidades.py
│   │   │   └── fabulas.py
│   │   ├── registry.py                   # Registry de providers
│   │   ├── service.py
│   │   ├── routes.py
│   │   └── schemas.py
│   │
│   └── pipeline/                         # FEATURE: Pipeline de geração
│       ├── __init__.py
│       ├── domain/
│       │   ├── roteiro_generator_protocol.py
│       │   ├── tts_provider_protocol.py
│       │   ├── transcription_protocol.py
│       │   ├── stock_video_protocol.py
│       │   └── video_composer_protocol.py
│       ├── adapters/                     # Implementações concretas
│       │   ├── claude_roteiro_generator.py
│       │   ├── edge_tts_provider.py
│       │   ├── whisper_transcription.py
│       │   ├── pexels_stock_video.py
│       │   └── ffmpeg_video_composer.py
│       └── orchestrator.py               # Coordena as 5 etapas via interfaces
│
└── (outros: .env, requirements.txt, README.md, alembic.ini se usar, etc)
```

### Estrutura interna de cada feature

Cada feature do backend segue o padrão **Domain / Data / Service / Routes**:

- **`domain/`**: o que é eterno e não muda com tecnologia. Modelos de dados, entidades, exceptions específicas do domínio. NÃO importa nada de infraestrutura.
- **`data/`**: como persistir. Define **Protocol** (interface) e implementações. Trocar SQLite por Postgres = trocar a implementação aqui sem mexer no service.
- **`service.py`**: lógica de negócio. Recebe as interfaces injetadas no construtor, usa elas pra fazer o que precisa. **Não conhece HTTP, não conhece SQL.**
- **`routes.py`**: camada de transporte HTTP. Converte request → chamada de service → response. Não tem lógica de negócio.
- **`schemas.py`**: Pydantic models pra request/response (DTOs HTTP). Separado dos modelos de domínio.
- **`dependencies.py`** (opcional): factory pra montar instâncias da feature (usadas via FastAPI Depends).

### Composition Root: `src/main.py`

O **único lugar** onde implementações concretas são criadas e amarradas. Toda a aplicação é "montada" aqui no startup:

```python
# src/main.py
from fastapi import FastAPI
from src.config import Settings
from src.container import construir_container
from src.auth.routes import criar_router as criar_router_auth
from src.videos.routes import criar_router as criar_router_videos
from src.temas.routes import criar_router as criar_router_temas

def criar_app() -> FastAPI:
    settings = Settings()
    container = construir_container(settings)
    
    app = FastAPI(title="Vídeos Narrados API", version="1.0.0")
    
    # Middlewares (CORS, logging, etc)
    configurar_middlewares(app, settings)
    
    # Inclui routers de cada feature, injetando dependências via Depends
    app.include_router(criar_router_auth(container), prefix="/auth", tags=["auth"])
    app.include_router(criar_router_videos(container), prefix="/videos", tags=["videos"])
    app.include_router(criar_router_temas(container), prefix="/temas", tags=["temas"])
    
    return app

app = criar_app()
```

**Princípio**: nenhum outro arquivo do projeto deveria criar instâncias de repositórios ou services. Tudo vem do container, injetado.

### Interface pública de cada feature

O `__init__.py` de cada feature re-exporta o que é público pra outros módulos:

```python
# src/auth/__init__.py
"""
Interface pública do módulo de autenticação.

Outros módulos devem importar APENAS daqui:
    from src.auth import AuthService, usuario_atual, Usuario
"""
from src.auth.service import AuthService
from src.auth.dependencies import usuario_atual
from src.auth.domain.models import Usuario

__all__ = ["AuthService", "usuario_atual", "Usuario"]
```

**Regra**: módulos externos só podem importar do `__init__.py`. Importar `src.auth.data.repository_sqlmodel` direto de outro módulo é violação arquitetural.

### Exemplo concreto: feature `auth`

**Protocol** (interface):
```python
# src/auth/data/repository_protocol.py
from typing import Protocol
from src.auth.domain.models import Usuario, RefreshToken

class UsuarioRepositoryProtocol(Protocol):
    async def criar(self, usuario: Usuario) -> Usuario: ...
    async def buscar_por_email(self, email: str) -> Usuario | None: ...
    async def buscar_por_id(self, usuario_id: str) -> Usuario | None: ...
    async def atualizar(self, usuario: Usuario) -> Usuario: ...

class RefreshTokenRepositoryProtocol(Protocol):
    async def criar(self, token: RefreshToken) -> RefreshToken: ...
    async def buscar_por_hash(self, token_hash: str) -> RefreshToken | None: ...
    async def revogar_por_id(self, token_id: str, motivo: str) -> None: ...
    async def revogar_todos_do_usuario(self, usuario_id: str, motivo: str) -> int: ...
```

**Implementação SQLModel**:
```python
# src/auth/data/repository_sqlmodel.py
from sqlmodel import Session, select
from src.auth.data.repository_protocol import UsuarioRepositoryProtocol
from src.auth.domain.models import Usuario

class UsuarioRepositorySqlModel:
    def __init__(self, session: Session) -> None:
        self._session = session
    
    async def buscar_por_email(self, email: str) -> Usuario | None:
        statement = select(Usuario).where(Usuario.email == email)
        return self._session.exec(statement).first()
    
    # ... outros métodos
```

**Service** (lógica de negócio, depende só das interfaces):
```python
# src/auth/service.py
from src.auth.data.repository_protocol import UsuarioRepositoryProtocol, RefreshTokenRepositoryProtocol
from src.auth.domain.exceptions import CredenciaisInvalidas
from src.auth.security import HashServiceProtocol, JwtServiceProtocol

class AuthService:
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryProtocol,
        token_repo: RefreshTokenRepositoryProtocol,
        hash_service: HashServiceProtocol,
        jwt_service: JwtServiceProtocol,
    ) -> None:
        self._usuario_repo = usuario_repo
        self._token_repo = token_repo
        self._hash = hash_service
        self._jwt = jwt_service
    
    async def autenticar(self, email: str, senha: str) -> AuthTokens:
        usuario = await self._usuario_repo.buscar_por_email(email)
        if not usuario or not self._hash.verificar(senha, usuario.senha_hash):
            raise CredenciaisInvalidas()
        return await self._emitir_tokens(usuario)
    
    # ... outros métodos
```

Repare: o `AuthService` não conhece SQLModel, não conhece bcrypt, não conhece JWT. Recebe interfaces. **Pode ser testado com mocks triviais** se quisermos.

### Routes (transporte HTTP):
```python
# src/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException
from src.auth.service import AuthService
from src.auth.schemas import LoginRequest, AuthResponse

def criar_router(container: Container) -> APIRouter:
    router = APIRouter()
    
    def obter_auth_service() -> AuthService:
        return container.auth_service()
    
    @router.post("/login", response_model=AuthResponse, status_code=200)
    async def login(
        request: LoginRequest,
        service: AuthService = Depends(obter_auth_service),
    ) -> AuthResponse:
        try:
            tokens = await service.autenticar(request.email, request.senha)
            return AuthResponse.from_tokens(tokens)
        except CredenciaisInvalidas:
            raise HTTPException(401, "Credenciais inválidas")
    
    return router
```

A rota só faz: deserializar → chamar service → serializar. **Zero lógica de negócio.**

---

## Arquitetura do App Mobile

### Estrutura de pastas (Feature-Sliced)

```
videos_app/
├── docs/
│   └── adr/                              # ADRs do app (alguns compartilhados com backend)
├── src/
│   ├── App.tsx                           # Composition root
│   ├── navigation/
│   │   ├── index.tsx
│   │   ├── AuthStack.tsx
│   │   ├── AppStack.tsx
│   │   └── types.ts
│   │
│   ├── shared/                           # Infraestrutura compartilhada
│   │   ├── api/
│   │   │   ├── httpClient.ts             # Interface (type) + instância exportada
│   │   │   ├── ApiError.ts
│   │   │   └── interceptors.ts           # Lógica de refresh automático
│   │   ├── storage/
│   │   │   ├── secureStorage.ts          # Interface + instância (expo-secure-store)
│   │   │   ├── keyValueStorage.ts        # Interface + instância (AsyncStorage)
│   │   │   └── tokenStorage.ts           # Wrapper específico pra tokens
│   │   ├── notifications/
│   │   │   └── notificationService.ts    # Interface + instância (expo-notifications)
│   │   ├── filesystem/
│   │   │   └── fileSystemService.ts      # Interface + instância (expo-file-system)
│   │   ├── sharing/
│   │   │   └── sharingService.ts         # Interface + instância (expo-sharing)
│   │   ├── theme/
│   │   │   ├── colors.ts
│   │   │   ├── typography.ts
│   │   │   └── useTheme.ts
│   │   ├── components/                   # Componentes UI genéricos
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── ErroComRetry.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── Skeleton.tsx
│   │   ├── hooks/                        # Hooks genéricos
│   │   │   ├── useDebounce.ts
│   │   │   └── useNetInfo.ts
│   │   └── lib/                          # Utilidades puras
│   │       ├── formatters.ts
│   │       ├── validators.ts
│   │       └── result.ts                 # Type Result<T,E> pra error handling
│   │
│   ├── features/
│   │   ├── auth/
│   │   │   ├── index.ts                  # API pública
│   │   │   ├── domain/
│   │   │   │   ├── entities.ts           # Usuario, AuthTokens
│   │   │   │   ├── errors.ts
│   │   │   │   └── interfaces.ts         # AuthRepository (type/interface)
│   │   │   ├── data/
│   │   │   │   ├── authRepository.ts     # Implementação concreta (consome httpClient)
│   │   │   │   ├── dtos.ts               # Tipos exatos da API
│   │   │   │   └── mappers.ts            # DTO ↔ Entity
│   │   │   ├── ui/
│   │   │   │   ├── screens/
│   │   │   │   │   ├── LoginScreen.tsx
│   │   │   │   │   └── RegistrarScreen.tsx
│   │   │   │   ├── components/
│   │   │   │   │   ├── LoginForm.tsx
│   │   │   │   │   └── ForcaSenhaIndicator.tsx
│   │   │   │   └── hooks/
│   │   │   │       ├── useLogin.ts       # Lógica de auth + chamada do repo
│   │   │   │       ├── useRegistrar.ts
│   │   │   │       └── useLogout.ts
│   │   │   └── store/
│   │   │       └── authStore.ts          # Zustand store da feature
│   │   │
│   │   ├── temas/
│   │   │   ├── index.ts
│   │   │   ├── domain/
│   │   │   ├── data/
│   │   │   └── ui/
│   │   │
│   │   ├── videos/                       # geração + player + galeria
│   │   │   ├── index.ts
│   │   │   ├── domain/
│   │   │   ├── data/
│   │   │   └── ui/
│   │   │       ├── screens/
│   │   │       │   ├── GeracaoScreen.tsx
│   │   │       │   ├── PlayerScreen.tsx
│   │   │       │   └── GaleriaScreen.tsx
│   │   │       └── components/
│   │   │
│   │   └── configuracoes/
│   │       ├── index.ts
│   │       └── ui/
│   │           ├── screens/ConfiguracoesScreen.tsx
│   │           └── components/
│   │
│   └── app/                              # Composição final
│       ├── App.tsx
│       └── providers/                    # QueryProvider, ThemeProvider, etc
```

### Camadas dentro de cada feature

Cada feature segue **3 camadas** (Feature-Sliced + leve clean):

#### `domain/`
- **Entities**: tipos de domínio puros. Sem dependência de React, sem dependência de bibliotecas externas.
- **Interfaces**: tipos/interfaces TypeScript pras fontes de dados (`AuthRepository`, etc).
- **Errors**: exceptions/erros específicos da feature.

#### `data/`
- **Repositories** (implementações): consomem serviços de `shared/` (httpClient, storage). Implementam as interfaces definidas em `domain/interfaces.ts`.
- **DTOs**: tipos que batem **exatamente** com a API.
- **Mappers**: funções que convertem DTO ↔ Entity (mantém domain isolado de mudanças na API).

#### `ui/`
- **Screens**: telas. Consomem hooks da feature.
- **Components**: componentes específicos da feature.
- **Hooks**: React hooks que orquestram chamadas a repositories e atualizações de stores.

#### `store/`
- Zustand store da feature. Estado **somente** dessa feature. Importado via `index.ts`.

### Princípio chave: separação clara de camadas, mas idiomática

**Interface no domain:**

```typescript
// src/features/auth/domain/interfaces.ts
import type { AuthTokens, Usuario } from './entities';

export interface AuthRepository {
  autenticar(email: string, senha: string): Promise<AuthTokens>;
  registrar(nome: string, email: string, senha: string): Promise<{ usuario: Usuario; tokens: AuthTokens }>;
  refresh(refreshToken: string): Promise<AuthTokens>;
  logout(refreshToken: string): Promise<void>;
  obterEu(): Promise<Usuario>;
}
```

**Implementação no data (consome shared via import):**

```typescript
// src/features/auth/data/authRepository.ts
import { httpClient } from '@/shared/api';
import type { AuthRepository } from '../domain/interfaces';
import type { LoginResponseDto } from './dtos';
import { tokensDtoParaEntity, usuarioDtoParaEntity } from './mappers';

export const authRepository: AuthRepository = {
  async autenticar(email, senha) {
    const dto = await httpClient.post<LoginResponseDto>('/auth/login', { email, senha });
    return tokensDtoParaEntity(dto);
  },
  
  async registrar(nome, email, senha) {
    const dto = await httpClient.post<RegistrarResponseDto>('/auth/registrar', { nome, email, senha });
    return {
      usuario: usuarioDtoParaEntity(dto.usuario),
      tokens: tokensDtoParaEntity(dto),
    };
  },
  
  async refresh(refreshToken) {
    const dto = await httpClient.post<RefreshResponseDto>('/auth/refresh', { refresh_token: refreshToken });
    return tokensDtoParaEntity(dto);
  },
  
  async logout(refreshToken) {
    await httpClient.post('/auth/logout', { refresh_token: refreshToken });
  },
  
  async obterEu() {
    const dto = await httpClient.get<UsuarioDto>('/auth/eu');
    return usuarioDtoParaEntity(dto);
  },
};
```

**Hook que orquestra (sem container, idiomático):**

```typescript
// src/features/auth/ui/hooks/useLogin.ts
import { useMutation } from '@tanstack/react-query';
import { authRepository } from '../../data/authRepository';
import { tokenStorage } from '@/shared/storage';
import { useAuthStore } from '../../store/authStore';

export function useLogin() {
  const setAutenticado = useAuthStore(s => s.setAutenticado);
  
  return useMutation({
    mutationFn: async ({ email, senha }: { email: string; senha: string }) => {
      const tokens = await authRepository.autenticar(email, senha);
      await tokenStorage.salvar(tokens);
      return tokens;
    },
    onSuccess: (tokens) => setAutenticado(tokens),
  });
}
```

**Notas importantes:**

- Hook depende de `authRepository` (que é `AuthRepository` interface) — não da implementação concreta de HTTP
- `tokenStorage` é exposto como instância única do `shared/storage`, com interface clara
- A lógica de negócio (sequência: autenticar → salvar tokens → marcar autenticado) está no hook, idiomático em RN
- Para casos mais complexos, a lógica pode ir pra uma função pura em `domain/usecases.ts`, recebendo dependências por parâmetro

### Quando criar uma "função use case" pura

Se a lógica orquestra **3+ chamadas** ou tem **regras de negócio não-triviais**, extraia para uma função pura em `domain/usecases.ts`:

```typescript
// src/features/auth/domain/usecases.ts
import type { AuthRepository } from './interfaces';
import type { TokenStorage } from '@/shared/storage';

export async function executarLogin(
  deps: { auth: AuthRepository; storage: TokenStorage },
  input: { email: string; senha: string },
): Promise<AuthTokens> {
  const tokens = await deps.auth.autenticar(input.email, input.senha);
  await deps.storage.salvar(tokens);
  return tokens;
}
```

**Quando aplicar:** se a função vale a pena ter testes unitários, ou se a lógica é complexa o suficiente que misturar com React traria confusão. Para CRUD simples, **deixe no hook**.

### Interface pública de uma feature

```typescript
// src/features/auth/index.ts
// Re-exporta o que é público pra outras features e pra navegação

export { LoginScreen } from './ui/screens/LoginScreen';
export { RegistrarScreen } from './ui/screens/RegistrarScreen';
export { useAuthStore } from './store/authStore';
export type { Usuario, AuthTokens } from './domain/entities';

// NÃO exporta: repositories, hooks internos, DTOs, mappers
```

Outras features importam **apenas** de `@/features/auth`, não dos arquivos internos.

---

## Injeção de Dependências

### Princípio fundamental

O Princípio de Inversão de Dependência (DIP) é aplicado nos dois lados, mas com **abordagens diferentes** apropriadas a cada plataforma:

- **Backend (Python/FastAPI)**: Container manual leve com tokens e registros centralizados, alinhado ao padrão idiomático de aplicações backend e à integração natural com `Depends()` do FastAPI.
- **Mobile (React Native/TypeScript)**: DI implícita via imports + interfaces TypeScript, padrão idiomático do ecossistema React. Use cases simples vivem nos hooks; lógica complexa vira função pura recebendo dependências por parâmetro.

Essa diferença é **intencional** — está documentada na ADR-0013.

### Container do Backend

```python
# src/container.py
from typing import Callable, TypeVar
from sqlmodel import Session
from src.config import Settings

T = TypeVar('T')

class Container:
    """Container manual de DI. Ver ADR-0005."""
    
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._singletons: dict[str, object] = {}
        self._factories: dict[str, Callable[['Container'], object]] = {}
    
    def register_singleton(self, key: str, factory: Callable[['Container'], T]) -> None:
        self._factories[key] = factory
    
    def resolve(self, key: str) -> object:
        if key in self._singletons:
            return self._singletons[key]
        if key not in self._factories:
            raise KeyError(f"Token não registrado: {key}")
        instance = self._factories[key](self)
        self._singletons[key] = instance
        return instance
    
    # Métodos tipados pra cada dependência (melhor type safety)
    def auth_service(self) -> 'AuthService':
        return self.resolve('AuthService')  # type: ignore
    
    def videos_service(self) -> 'VideosService':
        return self.resolve('VideosService')  # type: ignore


def construir_container(settings: Settings) -> Container:
    from src.shared.database import criar_session_factory
    from src.auth.data.repository_sqlmodel import UsuarioRepositorySqlModel, RefreshTokenRepositorySqlModel
    from src.auth.security import BcryptHashService, JoseJwtService
    from src.auth.service import AuthService
    
    c = Container(settings)
    
    session_factory = criar_session_factory(settings.database_url)
    c.register_singleton('SessionFactory', lambda _: session_factory)
    
    # Hash + JWT
    c.register_singleton('HashService', lambda _: BcryptHashService(rounds=settings.bcrypt_rounds))
    c.register_singleton('JwtService', lambda c: JoseJwtService(
        secret=c.settings.jwt_secret_key,
        algorithm=c.settings.jwt_algorithm,
        access_ttl=c.settings.access_token_expire_minutes,
    ))
    
    # Auth
    c.register_singleton('UsuarioRepository', lambda c: UsuarioRepositorySqlModel(c.resolve('SessionFactory')()))
    c.register_singleton('RefreshTokenRepository', lambda c: RefreshTokenRepositorySqlModel(c.resolve('SessionFactory')()))
    c.register_singleton('AuthService', lambda c: AuthService(
        usuario_repo=c.resolve('UsuarioRepository'),
        token_repo=c.resolve('RefreshTokenRepository'),
        hash_service=c.resolve('HashService'),
        jwt_service=c.resolve('JwtService'),
    ))
    
    # ... outros registros
    
    return c
```

### Como FastAPI consome o container

FastAPI tem `Depends()` nativo. Combinamos os dois: o container resolve as dependências e a `Depends()` injeta nos endpoints:

```python
# src/auth/routes.py
def criar_router(container: Container) -> APIRouter:
    router = APIRouter()
    
    def get_service() -> AuthService:
        return container.auth_service()
    
    @router.post("/login")
    async def login(req: LoginRequest, service: AuthService = Depends(get_service)):
        ...
    
    return router
```

### DI no Mobile (padrão idiomático)

No mobile, **não há container**. A inversão de dependência é garantida por três mecanismos:

#### 1. Interfaces TypeScript no domain layer

```typescript
// src/features/auth/domain/interfaces.ts
export interface AuthRepository {
  autenticar(email: string, senha: string): Promise<AuthTokens>;
  registrar(nome: string, email: string, senha: string): Promise<{ usuario: Usuario; tokens: AuthTokens }>;
  refresh(refreshToken: string): Promise<AuthTokens>;
  logout(refreshToken: string): Promise<void>;
}
```

Use cases e hooks dependem dessa interface, **não** da implementação concreta.

#### 2. Instâncias únicas exportadas de cada módulo de `shared/`

```typescript
// src/shared/api/httpClient.ts
import { HttpClient } from './types';
import { criarFetchHttpClient } from './fetchHttpClient';

// Interface exposta como tipo
export type { HttpClient };

// Instância única exposta como singleton (padrão idiomático JS)
export const httpClient: HttpClient = criarFetchHttpClient({
  baseUrl: process.env.EXPO_PUBLIC_API_URL!,
});
```

```typescript
// src/shared/storage/tokenStorage.ts
import { SecureStorage } from './secureStorage';
import { expoSecureStorage } from './expoSecureStorage';

export interface TokenStorage {
  salvar(tokens: AuthTokens): Promise<void>;
  obter(): Promise<AuthTokens | null>;
  limpar(): Promise<void>;
}

export const tokenStorage: TokenStorage = {
  async salvar(tokens) {
    await expoSecureStorage.setItem('access_token', tokens.accessToken);
    await expoSecureStorage.setItem('refresh_token', tokens.refreshToken);
  },
  // ...
};
```

#### 3. Funções use case puras pra lógica complexa

Quando a lógica vai além de "chama repo, salva resultado", extrai para função pura:

```typescript
// src/features/auth/domain/usecases.ts
import type { AuthRepository } from './interfaces';
import type { TokenStorage } from '@/shared/storage/tokenStorage';
import type { AuthTokens } from './entities';

// Função pura recebe deps explicitamente. Testável sem mock framework.
export async function executarLogin(
  deps: { auth: AuthRepository; storage: TokenStorage },
  input: { email: string; senha: string },
): Promise<AuthTokens> {
  const tokens = await deps.auth.autenticar(input.email, input.senha);
  await deps.storage.salvar(tokens);
  return tokens;
}
```

#### Hook consome diretamente (sem container)

```typescript
// src/features/auth/ui/hooks/useLogin.ts
import { useMutation } from '@tanstack/react-query';
import { authRepository } from '../../data/authRepository';
import { tokenStorage } from '@/shared/storage/tokenStorage';
import { useAuthStore } from '../../store/authStore';
import { executarLogin } from '../../domain/usecases';

export function useLogin() {
  const setAutenticado = useAuthStore(s => s.setAutenticado);
  
  return useMutation({
    mutationFn: ({ email, senha }: { email: string; senha: string }) =>
      executarLogin({ auth: authRepository, storage: tokenStorage }, { email, senha }),
    onSuccess: (tokens) => setAutenticado(tokens),
  });
}
```

**Por que essa abordagem está correta arquiteturalmente:**

1. **DIP cumprido**: a função `executarLogin` depende de **interfaces** (`AuthRepository`, `TokenStorage`), não de implementações concretas.
2. **Testável**: `executarLogin({ auth: mockAuth, storage: mockStorage }, ...)` — trivial.
3. **Idiomático**: padrão do ecossistema React Native, fácil de manter.
4. **Sem boilerplate**: nada de tokens, registros, providers de container.
5. **Composição clara**: hook orquestra (UI), use case executa (domain), repository acessa dados (data).

---

## SOLID na prática

### Single Responsibility (SRP)

**Backend**: cada arquivo tem um propósito único — `repository_sqlmodel.py` SÓ persiste, `service.py` SÓ tem lógica, `routes.py` SÓ traduz HTTP, `security.py` SÓ lida com hash/JWT.

**Mobile**: cada hook expõe uma operação (`useLogin`, `useGerarVideo`). Cada componente tem responsabilidade visual única. Use cases têm uma única razão pra mudar.

### Open/Closed (OCP)

**Backend**: `BaseTemaProvider` permite adicionar tema novo sem modificar código existente. Mesma coisa pros `Adapter`s do pipeline (trocar ElevenLabs por edge-tts é só registrar outro adapter no container).

**Mobile**: features se conectam pela interface pública (`index.ts`). Adicionar feature nova não exige tocar nas existentes.

### Liskov Substitution (LSP)

**Backend**: qualquer implementação de `UsuarioRepositoryProtocol` é intercambiável. `AuthService` funciona igual com `UsuarioRepositorySqlModel` ou `UsuarioRepositoryInMemory` (útil pra testes).

**Mobile**: qualquer `SecureStorage` (Expo, mock, in-memory) é trocável.

### Interface Segregation (ISP)

**Backend**: temos protocols pequenos e específicos: `HashServiceProtocol`, `JwtServiceProtocol` — não um `SecurityProtocol` gigante.

**Mobile**: hooks são granulares. Não temos `useEverything()` — temos `useLogin`, `useRegistrar`, `useLogout`, separados.

### Dependency Inversion (DIP)

**Backend**: services dependem de `Protocol`s, não de classes concretas. Implementações são injetadas pelo container manual.

**Mobile**: hooks e use cases dependem de interfaces TypeScript (`AuthRepository`, `TokenStorage`), não das implementações concretas. As implementações são instâncias singleton exportadas pelos módulos de `shared/` e `features/*/data/`. Sem container — o sistema de módulos do JavaScript serve como composition root natural.

---

## Estrutura de ADRs

### Formato adotado: MADR (Markdown Any Decision Records)

Cada ADR é um arquivo `.md` em `docs/adr/NNNN-titulo-curto.md`.

### Template

```markdown
# NNNN. Título da Decisão

Data: YYYY-MM-DD
Status: Aceito | Substituído por ADR-XXXX | Obsoleto

## Contexto

Que problema estamos resolvendo? Que forças nos levaram a essa decisão?
Quais restrições (técnicas, de tempo, de conhecimento)?

## Decisão

A escolha tomada, em uma ou duas sentenças claras.

## Consequências

### Positivas
- ...

### Negativas
- ...

### Neutras
- ...

## Alternativas consideradas

### Alternativa A
Por que foi descartada.

### Alternativa B
Por que foi descartada.

## Referências (opcional)
- Links pra docs, artigos, RFCs.
```

### ADRs propostas (~12)

**ADRs compartilhadas (sistema todo):**

1. **0001 - Adoção de organização Feature-Sliced**
   - Por que feature-sliced em vez de organização por tipo técnico.
2. **0002 - Aplicação pragmática de SOLID**
   - Como vamos aplicar SOLID sem dogmatismo.
3. **0003 - Documentação via ADRs**
   - Por que ADRs, formato escolhido, quando criar uma nova.

**ADRs do backend:**

4. **0004 - FastAPI como framework do backend**
   - Vs Flask, Django, Litestar. Justificativa.
5. **0005 - DI manual via Container leve**
   - Vs dependency-injector, punq, ou Depends puro do FastAPI.
6. **0006 - SQLite + SQLModel pra persistência**
   - Vs Postgres, vs SQLAlchemy puro.
7. **0007 - Processamento async via BackgroundTasks**
   - Vs Celery + Redis. Trade-offs e escopo.
8. **0008 - Plugin architecture pra temas**
   - Como ABC + Registry resolve extensibilidade.

**ADRs de segurança/auth:**

9. **0009 - JWT + Refresh Token rotacionado**
   - Justificativa do modelo, alternativas (sessões, JWT longo, etc).
10. **0010 - SecureStore no app, hash SHA-256 no backend**
    - Por que tokens não vão em AsyncStorage. Por que hash em vez de plain.

**ADRs do mobile:**

11. **0011 - Expo Managed Workflow**
    - Vs bare React Native, vs nativo. Trade-offs.
12. **0012 - Zustand pra estado, TanStack Query pra server state**
    - Vs Redux, vs Context puro, vs SWR.
13. **0013 - DI idiomática React Native (sem container)**
    - Decisão consciente de NÃO replicar o container do backend no mobile. Justifica padrão idiomático: interfaces TypeScript + instâncias singleton exportadas + funções use case puras. Mostra maturidade em adaptar princípios ao contexto de cada plataforma.

### `docs/adr/README.md` (índice)

```markdown
# Architecture Decision Records

Este diretório contém todas as decisões arquiteturais significativas do projeto.

## Convenções
- Arquivos seguem padrão `NNNN-titulo-curto.md`
- Cada ADR usa o template `template.md`
- ADRs antigas nunca são editadas — quando substituídas, marcar status

## Índice
- [0001 - Organização Feature-Sliced](./0001-organizacao-feature-sliced.md)
- [0002 - SOLID pragmático](./0002-solid-pragmatico.md)
- ...
```

---

## Como o Claude Code deve implementar

### Ordem de implementação recomendada

**Fase 0 — Documentação arquitetural**
Antes de qualquer código, criar a estrutura `docs/adr/` com:
- O `template.md`
- O `README.md` (índice)
- As ADRs 0001-0003 (compartilhadas)
- As ADRs específicas do que vai implementar primeiro (backend ou mobile)

**Fase 1 — Backend**

1. Estrutura de pastas vazia + `__init__.py`s
2. `src/shared/` (database, logging, exceptions base)
3. `src/config.py` + `.env.example`
4. `src/container.py` (esqueleto sem registros ainda)
5. `src/main.py` (FastAPI app sem rotas)
6. Feature `auth/` completa (domain → data → service → routes)
7. Registrar `auth` no container, plugar router no `main.py`
8. Testar com curl
9. ADRs relacionadas a auth criadas
10. Feature `temas/` (mais simples, sem persistência pesada)
11. Feature `videos/` (a maior, depende das anteriores)
12. Feature `pipeline/` (adapters pras APIs externas)

**Fase 2 — Mobile**

1. Estrutura de pastas + Expo setup
2. `src/shared/` (httpClient, secureStorage, etc — interfaces + instâncias singleton exportadas)
3. Feature `auth/` (LoginScreen + repository + use cases + hooks + store)
4. Navegação condicional (AuthStack vs AppStack)
5. Feature `temas/`
6. Feature `videos/` (geração + player + galeria)
7. Feature `configuracoes/`
8. ADRs do mobile

### Princípios não-negociáveis durante implementação

1. **Nenhum arquivo passa de 300 linhas.** Se passar, refatorar em arquivos menores.
2. **Imports só do `__init__.py` / `index.ts`** de outras features.
3. **Domínio nunca importa de data ou ui.** Use cases nunca importam de UI.
4. **Tudo que é interface termina com `Protocol` (Python) ou começa sem prefixo (TS).** Implementações têm sufixo descritivo (`SqlModel`, `Expo`, `Fetch`).
5. **Backend: composition root é o único lugar onde instanciamento direto de classes concretas acontece** (`main.py` + `container.py`). Mobile: instâncias singleton são criadas nos módulos de `shared/` e `features/*/data/`, e importadas onde necessárias.
6. **Cada feature tem testes mínimos.** Não testes unitários elaborados — mas um teste por use case mostrando que a arquitetura permite testar facilmente.

### Antes de implementar, apresentar:

1. Plano completo da fase escolhida (backend ou mobile primeiro)
2. Ordem de criação dos arquivos
3. Quais ADRs serão criadas em cada etapa
4. Estimativa de linhas/complexidade por arquivo
5. **Aguardar confirmação antes de codificar**

### Documentação de cada feature

Cada feature tem um `README.md` interno (`src/auth/README.md`) com:

- Responsabilidade da feature
- Diagrama das camadas (ASCII)
- API pública (o que outros módulos podem importar)
- Como adicionar novos casos de uso
- Decisões específicas da feature (ou link pras ADRs)

---

## Anexo: Diagrama de dependências (backend)

```
┌──────────────────────────────────────────────┐
│                  main.py                     │
│           (Composition Root)                 │
└─────────────────┬────────────────────────────┘
                  │ instancia
                  ▼
┌──────────────────────────────────────────────┐
│                container.py                  │
│   (registra factories, resolve instâncias)   │
└─────────────────┬────────────────────────────┘
                  │ injeta em
                  ▼
┌──────────────────────────────────────────────┐
│              src/auth/routes.py              │
│        src/videos/routes.py                  │
│        (camada de transporte HTTP)           │
└─────────────────┬────────────────────────────┘
                  │ chama
                  ▼
┌──────────────────────────────────────────────┐
│           src/auth/service.py                │
│         src/videos/service.py                │
│      (lógica de negócio — não conhece HTTP)  │
└────────┬─────────────────────┬───────────────┘
         │ depende de          │ depende de
         ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ data/Protocol    │  │ domain/entities  │
│ (interfaces)     │  │ (modelos puros)  │
└─────────┬────────┘  └──────────────────┘
          │ implementadas por
          ▼
┌──────────────────────────────────────────────┐
│  data/repository_sqlmodel.py                 │
│  data/storage_filesystem.py                  │
│  (implementações concretas — SQL, FS, etc)   │
└──────────────────────────────────────────────┘
```

A seta sempre aponta da implementação pra abstração. **A lógica de negócio (service) nunca conhece a implementação (sqlmodel)** — só conhece o Protocol.

---

## Resumo executivo

| Aspecto | Backend | Mobile |
|---------|---------|--------|
| Organização | Feature-Sliced (`auth/`, `videos/`, `temas/`, `pipeline/`) | Feature-Sliced (`features/auth`, `features/videos`, etc) |
| Camadas internas | domain / data / service / routes | domain / data / ui / store |
| Interfaces | `Protocol` (Python typing) | `interface` (TypeScript) |
| DI | Container manual em `container.py` | Idiomática: instâncias singleton em módulos + imports |
| Composition Root | `main.py` + `container.py` | Sistema de módulos JS (cada `shared/*` e `data/*` exporta sua instância) |
| Comunicação entre módulos | Só via `__init__.py` da feature | Só via `index.ts` da feature |
| Documentação | ADRs em `docs/adr/` | ADRs em `docs/adr/` (sistema unificado) |
| Limite de arquivo | 300 linhas | 300 linhas |
| Princípios SOLID | Todos, com pragmatismo | Todos, com pragmatismo |
