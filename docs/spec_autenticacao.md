# Especificação de Autenticação: JWT + Refresh Token

Este documento detalha a camada de autenticação que deve ser implementada no backend (FastAPI) e consumida pelo app (React Native Expo). Foi separado das specs principais por ser denso o suficiente para merecer atenção própria.

---

## Modelo de autenticação adotado

### Estratégia: Access Token (JWT) + Refresh Token (opaco em banco)

- **Access Token**: JWT assinado, validade curta (**15 minutos**). Carrega `user_id`, `email` e `exp` no payload. Stateless: o servidor não precisa consultar banco pra validar — só verifica assinatura e expiração.
- **Refresh Token**: string opaca aleatória (UUID v4 ou bytes random de 32+ chars), validade longa (**30 dias**). Armazenada em banco, pode ser revogada, **rotaciona a cada uso**.

### Por que essa arquitetura

- **Access curto** minimiza dano se vazar (15 min de uso indevido máximo)
- **Refresh em banco** permite revogação real (logout, troca de senha, suspeita de invasão)
- **Rotação de refresh** detecta uso simultâneo (se o legítimo já rotacionou, qualquer uso do antigo é alarme)
- **Stateless no access** mantém performance alta — sem hit no banco pra cada request autenticada

### Por que NÃO outras abordagens

- **Session-based clássico**: exige sticky sessions ou Redis, complexo demais pro escopo
- **Só JWT longo sem refresh**: sem mecanismo de revogação, vazamento = comprometimento total até expirar
- **OAuth/social login**: complexidade desproporcional pra trabalho individual; pode ser extensão futura

---

## Modelo de dados (backend)

### Tabela `usuarios`

```python
class Usuario(SQLModel, table=True):
    id: str = Field(primary_key=True, default_factory=lambda: f"u_{uuid4().hex[:12]}")
    email: str = Field(unique=True, index=True)
    senha_hash: str                        # bcrypt
    nome: str
    criado_em: datetime
    atualizado_em: datetime
    ativo: bool = True                     # soft delete / banimento
    email_verificado: bool = False         # placeholder pra futuro
```

### Tabela `refresh_tokens`

```python
class RefreshToken(SQLModel, table=True):
    id: str = Field(primary_key=True, default_factory=lambda: f"rt_{uuid4().hex}")
    token_hash: str = Field(unique=True, index=True)  # SHA-256 do token (NUNCA o token plain)
    usuario_id: str = Field(foreign_key="usuarios.id", index=True)
    criado_em: datetime
    expira_em: datetime
    revogado: bool = False
    revogado_em: datetime | None = None
    motivo_revogacao: str | None = None   # "logout" / "rotacao" / "seguranca" / "troca_senha"
    substituido_por_id: str | None = None  # rastreabilidade: aponta pro próximo na rotação
    
    # Auditoria leve
    user_agent: str | None = None
    ip: str | None = None
    ultimo_uso_em: datetime | None = None
```

**Decisão importante**: armazenar `token_hash` (SHA-256), não o token em plain. Se o banco vazar, atacante não consegue usar os refresh tokens.

### Atualização da tabela `jobs`

Adicionar `usuario_id` como FK obrigatória. Cada vídeo gerado pertence a um usuário. Filtrar `GET /videos` pelo usuário autenticado.

---

## Endpoints de autenticação

### `POST /auth/registrar`

**Request:**
```json
{
  "email": "usuario@exemplo.com",
  "senha": "MinhaSenh@123",
  "nome": "Maria Silva"
}
```

**Validações:**
- Email formato válido (Pydantic `EmailStr`)
- Senha: mínimo 8 caracteres, pelo menos 1 letra e 1 número
- Nome: 2-100 caracteres
- Email único (verificar antes de inserir)

**Resposta (201):**
```json
{
  "usuario": {
    "id": "u_a1b2c3d4e5f6",
    "email": "usuario@exemplo.com",
    "nome": "Maria Silva",
    "criado_em": "2026-05-28T15:30:00Z"
  },
  "access_token": "eyJhbGc...",
  "refresh_token": "rt_xxxxxxxx",
  "expires_in": 900
}
```

**Resposta (409 Conflict):** email já cadastrado.

### `POST /auth/login`

**Request:**
```json
{
  "email": "usuario@exemplo.com",
  "senha": "MinhaSenh@123"
}
```

**Lógica:**
- Buscar usuário por email
- Comparar `bcrypt.checkpw(senha, usuario.senha_hash)`
- Se falhar: **resposta genérica** (não revelar se email existe ou senha errada) — 401 com `"Credenciais inválidas"`
- Se sucesso: emitir par de tokens
- **Rate limiting**: máximo 5 tentativas por IP em 15 minutos (placeholder via `slowapi` ou similar)

**Resposta (200):** mesmo formato do registrar.

### `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "rt_xxxxxxxx"
}
```

**Lógica (crítica — implementar com cuidado):**

1. Hashear o token recebido (SHA-256)
2. Buscar registro pelo hash
3. Verificar:
   - Existe? Senão → 401
   - Não está revogado? Se sim → **possível invasão**: revogar TODOS os tokens do usuário, log de segurança, 401
   - Não expirou? Senão → 401
4. **Rotação**: revogar o token atual (`revogado=True`, `motivo='rotacao'`), criar novo refresh token, apontar `substituido_por_id`
5. Emitir novo access token
6. Atualizar `ultimo_uso_em` no anterior
7. Retornar par de tokens

**Resposta (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "rt_yyyyyyyy",
  "expires_in": 900
}
```

**Por que rotacionar:** se um atacante roubar o refresh token e usar antes do legítimo, na próxima vez que o legítimo tentar usar, vai dar erro. Aí sabemos que algo está errado e revogamos tudo (defesa em profundidade).

### `POST /auth/logout`

**Request:**
```json
{
  "refresh_token": "rt_xxxxxxxx"
}
```

**Header opcional:** `Authorization: Bearer <access_token>`

**Lógica:**
- Marcar refresh token como `revogado=True`, `motivo='logout'`
- Access token não é invalidado (vai expirar em ≤15 min naturalmente — o trade-off do stateless)

**Resposta (204 No Content)**.

### `POST /auth/logout-tudo`

Revoga **todos** os refresh tokens do usuário autenticado. Útil pra "sair de todas as sessões".

**Header obrigatório:** `Authorization: Bearer <access_token>`

**Resposta (204)**.

### `GET /auth/eu`

Retorna dados do usuário autenticado.

**Header:** `Authorization: Bearer <access_token>`

**Resposta (200):**
```json
{
  "id": "u_a1b2c3d4e5f6",
  "email": "usuario@exemplo.com",
  "nome": "Maria Silva",
  "criado_em": "2026-05-28T15:30:00Z",
  "videos_gerados": 12
}
```

### `PATCH /auth/eu`

Atualiza nome ou senha. Pra senha, exigir senha atual no body como confirmação.

```json
{
  "nome": "Maria Silva Souza",
  "senha_atual": "MinhaSenh@123",      // obrigatório se mudando senha
  "senha_nova": "OutraSenh@456"        // opcional
}
```

Se senha mudou: revogar todos os refresh tokens (forçar re-login em outros dispositivos).

---

## Middleware de autenticação

### Dependency `usuario_atual`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> Usuario:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        usuario_id = payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado", headers={"X-Token-Expired": "true"})
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")
    
    usuario = session.get(Usuario, usuario_id)
    if not usuario or not usuario.ativo:
        raise HTTPException(401, "Usuário inativo")
    
    return usuario
```

**Detalhe importante**: header customizado `X-Token-Expired: true` quando o erro é especificamente expiração. O app usa esse sinal pra disparar refresh automático sem ambiguidade.

### Aplicação nas rotas

Todas as rotas de vídeos exigem autenticação:

```python
@app.post("/videos/gerar")
async def gerar_video(
    request: GerarVideoRequest,
    usuario: Usuario = Depends(usuario_atual),
    background_tasks: BackgroundTasks = ...,
):
    job = criar_job(usuario_id=usuario.id, tema_id=request.tema_id)
    background_tasks.add_task(processar_job, job.id)
    return job
```

Rotas que NÃO exigem auth: `/auth/registrar`, `/auth/login`, `/auth/refresh`, `/health`, `/temas` (lista é pública), `/docs`.

---

## Configurações de segurança

### `.env` adicional

```
# Auth
JWT_SECRET_KEY=<gere com: python -c "import secrets; print(secrets.token_urlsafe(64))">
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Rate limiting
RATE_LIMIT_LOGIN_TENTATIVAS=5
RATE_LIMIT_LOGIN_JANELA_MINUTOS=15

# Bcrypt
BCRYPT_ROUNDS=12                          # equilíbrio custo/segurança
```

**Importante**: `JWT_SECRET_KEY` jamais commitada. Em produção, vir de secrets manager (no `eas.json`, Fly.io secrets, etc).

### Dependências novas

```
python-jose[cryptography]>=3.3.0          # JWT
passlib[bcrypt]>=1.7.4                    # hash de senha
slowapi>=0.1.9                            # rate limiting (opcional mas recomendado)
email-validator>=2.1.0                    # validação de email (Pydantic)
```

### Logs de segurança

Eventos a logar (em arquivo separado `logs/seguranca.log`):

- Tentativa de login (sucesso/falha) com IP
- Refresh token reutilizado (possível invasão)
- Logout / logout-tudo
- Troca de senha
- Criação de conta

Não logar tokens (nem hash). Logar `usuario_id` e `email`.

---

## Spec do lado do app (React Native)

### Armazenamento de tokens

**`expo-secure-store`** (não AsyncStorage). Justificativa: AsyncStorage não é criptografado, qualquer app rooted/jailbroken consegue ler.

```typescript
// src/lib/secureStorage.ts
import * as SecureStore from 'expo-secure-store';

const CHAVES = {
  ACCESS_TOKEN: 'auth_access_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  USUARIO: 'auth_usuario',
} as const;

export const tokenStorage = {
  async salvarAccess(token: string): Promise<void> {
    await SecureStore.setItemAsync(CHAVES.ACCESS_TOKEN, token);
  },
  async obterAccess(): Promise<string | null> {
    return SecureStore.getItemAsync(CHAVES.ACCESS_TOKEN);
  },
  async salvarRefresh(token: string): Promise<void> {
    await SecureStore.setItemAsync(CHAVES.REFRESH_TOKEN, token);
  },
  async obterRefresh(): Promise<string | null> {
    return SecureStore.getItemAsync(CHAVES.REFRESH_TOKEN);
  },
  async salvarUsuario(usuario: Usuario): Promise<void> {
    await SecureStore.setItemAsync(CHAVES.USUARIO, JSON.stringify(usuario));
  },
  async obterUsuario(): Promise<Usuario | null> {
    const raw = await SecureStore.getItemAsync(CHAVES.USUARIO);
    return raw ? JSON.parse(raw) : null;
  },
  async limparTudo(): Promise<void> {
    await Promise.all(Object.values(CHAVES).map(k => 
      SecureStore.deleteItemAsync(k).catch(() => {})
    ));
  },
};
```

### Cliente HTTP com refresh automático

```typescript
// src/api/client.ts
import { tokenStorage } from '../lib/secureStorage';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL!;

// Lock para impedir múltiplos refreshes simultâneos
let refreshPromise: Promise<string> | null = null;

async function tentarRefresh(): Promise<string> {
  // Se já tem refresh em andamento, aguarda ele em vez de iniciar outro
  if (refreshPromise) return refreshPromise;
  
  refreshPromise = (async () => {
    try {
      const refreshToken = await tokenStorage.obterRefresh();
      if (!refreshToken) throw new SemRefreshTokenError();
      
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      
      if (!res.ok) {
        // Refresh falhou — sessão acabou
        await tokenStorage.limparTudo();
        emitirEventoLogoutForcado();      // EventEmitter pro AuthContext reagir
        throw new SessaoExpiradaError();
      }
      
      const data = await res.json();
      await tokenStorage.salvarAccess(data.access_token);
      await tokenStorage.salvarRefresh(data.refresh_token);
      return data.access_token;
    } finally {
      refreshPromise = null;
    }
  })();
  
  return refreshPromise;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit & { _retry?: boolean } = {}
): Promise<T> {
  const access = await tokenStorage.obterAccess();
  
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(access ? { 'Authorization': `Bearer ${access}` } : {}),
      ...options.headers,
    },
  });
  
  // 401 + header de expiração + ainda não tentou refresh = tentar refresh
  if (
    res.status === 401 &&
    res.headers.get('X-Token-Expired') === 'true' &&
    !options._retry
  ) {
    await tentarRefresh();
    return apiRequest<T>(path, { ...options, _retry: true });
  }
  
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  
  return res.json();
}
```

**Detalhes críticos da implementação:**

1. **Lock global de refresh** (`refreshPromise`): se 5 requests dispararem simultaneamente e todas der 401, só uma faz refresh; as outras esperam. Sem isso, você dispara 5 refreshes em paralelo, todos invalidando uns aos outros pela rotação.

2. **Flag `_retry`**: previne loop infinito se o refresh também devolver 401 por algum motivo.

3. **Header `X-Token-Expired`**: distingue "token expirado" de "sem permissão". Sem esse sinal, qualquer 401 dispararia refresh.

4. **Logout forçado via evento**: quando o refresh falha, o app precisa navegar pra tela de Login. Usar `EventEmitter` ou Zustand store que o AuthContext escuta.

### AuthContext / Store

Usar **Zustand** com persistência (já está na stack do app):

```typescript
// src/stores/authStore.ts
import { create } from 'zustand';
import { tokenStorage } from '../lib/secureStorage';

interface AuthState {
  usuario: Usuario | null;
  carregando: boolean;
  autenticado: boolean;
  
  inicializar: () => Promise<void>;     // chamado no boot do app
  login: (email: string, senha: string) => Promise<void>;
  registrar: (dados: RegistrarRequest) => Promise<void>;
  logout: () => Promise<void>;
  logoutForcado: () => Promise<void>;   // chamado pelo cliente HTTP quando refresh falha
  atualizarUsuario: (dados: Partial<Usuario>) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  usuario: null,
  carregando: true,
  autenticado: false,
  
  inicializar: async () => {
    set({ carregando: true });
    const access = await tokenStorage.obterAccess();
    const usuario = await tokenStorage.obterUsuario();
    
    if (access && usuario) {
      // Valida access token chamando /auth/eu (que vai refresh automático se expirou)
      try {
        const u = await apiRequest<Usuario>('/auth/eu');
        set({ usuario: u, autenticado: true, carregando: false });
      } catch {
        await tokenStorage.limparTudo();
        set({ usuario: null, autenticado: false, carregando: false });
      }
    } else {
      set({ carregando: false });
    }
  },
  
  login: async (email, senha) => {
    const res = await apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, senha }),
    });
    await tokenStorage.salvarAccess(res.access_token);
    await tokenStorage.salvarRefresh(res.refresh_token);
    await tokenStorage.salvarUsuario(res.usuario);
    set({ usuario: res.usuario, autenticado: true });
  },
  
  // ... outros métodos análogos
  
  logout: async () => {
    const refresh = await tokenStorage.obterRefresh();
    if (refresh) {
      await apiRequest('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refresh }),
      }).catch(() => {}); // ignora erro — vai limpar local de qualquer jeito
    }
    await tokenStorage.limparTudo();
    set({ usuario: null, autenticado: false });
  },
  
  logoutForcado: async () => {
    await tokenStorage.limparTudo();
    set({ usuario: null, autenticado: false });
  },
}));
```

No `App.tsx`, chamar `inicializar()` antes de renderizar telas. Mostrar splash enquanto `carregando === true`.

### Navegação condicional

```typescript
// src/navigation/index.tsx
function RootNavigator() {
  const { autenticado, carregando } = useAuthStore();
  
  if (carregando) return <SplashScreen />;
  
  return (
    <NavigationContainer>
      {autenticado ? <AppStack /> : <AuthStack />}
    </NavigationContainer>
  );
}
```

**AuthStack** (não autenticado):
- LoginScreen
- RegistrarScreen
- EsqueciSenhaScreen (placeholder, podendo ficar desabilitada nesta versão)

**AppStack** (autenticado):
- Tudo que já estava nas specs

### Telas novas

**LoginScreen:**
- Logo do app no topo
- Inputs: email, senha (com toggle de mostrar/ocultar)
- Botão "Entrar"
- Link "Não tem conta? Cadastre-se"
- Loading state durante a request
- Mensagens de erro amigáveis ("Email ou senha incorretos" — genérico, não revela qual)
- Validação client-side antes de enviar (formato de email, senha mínima)

**RegistrarScreen:**
- Inputs: nome, email, senha, confirmação de senha
- Indicador de força de senha (visual)
- Validações em tempo real
- Checkbox de aceite dos termos (texto interno)
- Após sucesso: já loga automaticamente e vai pra Home

**Nova seção em ConfiguracoesScreen:**
- Bloco "Minha conta" no topo: nome, email, "Editar"
- "Sair desta sessão" (logout normal)
- "Sair de todas as sessões" (logout-tudo) — útil pra "perdi meu celular"
- "Trocar senha" (modal)
- "Deletar conta" (placeholder, pode ser não implementado nesta versão)

### Dependências adicionais do app

```
expo-secure-store
react-hook-form                          # validação de formulários (login/registro)
zod                                      # schemas de validação compartilhados
@hookform/resolvers                      # integração zod + react-hook-form
```

---

## Fluxos importantes documentados

### Fluxo 1: Login

```
[App: LoginScreen]
  ↓ (usuário submete)
[POST /auth/login]
  ↓
[Backend: valida bcrypt, gera tokens]
  ↓ (200 + tokens)
[App: salva em SecureStore, atualiza authStore]
  ↓
[App: navega pra Home]
```

### Fluxo 2: Request com refresh automático

```
[App: chama apiRequest('/videos')]
  ↓ (envia Bearer <access_expirado>)
[Backend: detecta JWT expirado]
  ↓ (401 + X-Token-Expired: true)
[App: client intercepta, chama tentarRefresh()]
  ↓ (POST /auth/refresh com refresh_token)
[Backend: valida, rotaciona, emite novos tokens]
  ↓ (200 + tokens novos)
[App: salva novos tokens, refaz request original]
  ↓ (envia Bearer <access_novo>)
[Backend: retorna dados]
  ↓ (200)
[App: resolve a promise original com os dados]
```

**Tudo transparente pro usuário.**

### Fluxo 3: Sessão expirou (refresh token também)

```
[App: chama apiRequest, access expirado]
  ↓
[Backend: 401 + X-Token-Expired]
  ↓
[App: tenta refresh]
  ↓ (POST /auth/refresh)
[Backend: refresh expirado/revogado, 401]
  ↓
[App: limpa SecureStore, emite evento logoutForcado]
  ↓
[authStore: autenticado = false]
  ↓
[Navegação: troca pra AuthStack]
  ↓
[App: LoginScreen com mensagem "Sua sessão expirou, faça login novamente"]
```

### Fluxo 4: Detecção de invasão (refresh rotation)

```
[Atacante usa refresh_token_1]
  ↓
[Backend: rotaciona, emite refresh_token_2]
  ↓
[Atacante agora tem token_2, mas o legítimo ainda tem token_1]
  ↓
[Legítimo tenta usar token_1]
  ↓
[Backend: token_1 já revogado (motivo=rotacao)]
  ↓
[Backend: REVOGA TODOS os tokens do usuário, log de segurança]
  ↓
[Tanto atacante quanto legítimo são deslogados]
  ↓
[Legítimo precisa fazer login novamente — com senha que o atacante não tem]
```

---

## Considerações de segurança (pra incluir no README e na defesa)

1. **Senhas com bcrypt + salt automático** (rounds=12)
2. **Tokens nunca em logs** — filtrar em qualquer logger
3. **HTTPS obrigatório em produção** — TLS termination no Fly.io/Render é grátis
4. **Refresh tokens armazenados como SHA-256 no banco** — vazamento do banco não compromete os tokens
5. **Access token curto (15min)** — janela de exposição mínima
6. **Refresh token rotation** — detecção de roubo
7. **Rate limiting em /login** — previne brute force
8. **Resposta genérica em login falho** — não revela se email existe
9. **SecureStore no cliente** — Keychain (iOS) / Keystore (Android)
10. **Logout invalida refresh no servidor** — não confia em "delete local"

---

## Atualizações necessárias nas specs anteriores

### `spec_backend.md`

**Adicionar à seção "Endpoints REST" os endpoints de `/auth/*`** definidos aqui.

**Adicionar `usuario_id` em todas as rotas de vídeos**:
- Job tem dono (FK obrigatória)
- `GET /videos` filtra por `usuario_id` do usuário autenticado
- `POST /videos/gerar` registra o `usuario_id`
- `GET /videos/{job_id}` rejeita (403) se o job pertence a outro usuário

**Adicionar à seção "Configuração e segurança":** trocar a auth simples por header `X-API-Key` para JWT Bearer (mantendo `X-API-Key` opcionalmente como dupla camada se quiser).

**Adicionar a `data/jobs.db`**: tabelas `usuarios` e `refresh_tokens` no mesmo SQLite.

**Adicionar à seção "Dependências"**: `python-jose`, `passlib[bcrypt]`, `email-validator`, `slowapi`.

**Adicionar nova seção no README**: "Autenticação" explicando o modelo, fluxos, e decisões de segurança.

### `spec_app_mobile.md`

**Adicionar telas de Auth (`LoginScreen`, `RegistrarScreen`)** no `src/screens/`.

**Adicionar `src/lib/secureStorage.ts`** e remover qualquer menção de salvar tokens em AsyncStorage.

**Adicionar `src/stores/authStore.ts`** com a lógica de Zustand.

**Atualizar `src/api/client.ts`** com a lógica de refresh automático.

**Atualizar a navegação**: dois stacks (AuthStack e AppStack) com switch baseado em `authStore.autenticado`.

**Adicionar dependências**: `expo-secure-store`, `react-hook-form`, `zod`, `@hookform/resolvers`.

**Adicionar fluxo de onboarding atualizado**: depois de aceitar termos, vai pra tela de Login (não direto pra Home).

**Adicionar à seção "Configurações"**: bloco de gerenciamento de conta (logout, logout-tudo, trocar senha).

**Adicionar à seção "Tratamento de erros consistente"**: tratamento específico de `SessaoExpiradaError` (redirecionar pra Login com toast amigável).

---

## Entrega esperada

1. **Primeiro o backend de auth** (sem isso, app não tem como autenticar). Implementar e testar via curl/Insomnia antes de mexer no app.
2. **Depois o app**: começar pela tela de Login, validar fluxo de login + chamada autenticada simples (`/auth/eu`), depois implementar refresh automático, por último adicionar o resto das telas autenticadas.

## Como testar manualmente o backend

```bash
# Registrar
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@exemplo.com","senha":"Teste1234","nome":"Teste"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@exemplo.com","senha":"Teste1234"}'

# Salvar tokens da resposta. Depois:
curl http://localhost:8000/auth/eu \
  -H "Authorization: Bearer <access_token>"

# Esperar 16 minutos (ou alterar expiração pra 30s temporariamente)
# Repetir o curl acima — vai dar 401 + X-Token-Expired

# Refresh
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'

# Pegar novos tokens, repetir /auth/eu — vai funcionar
```
