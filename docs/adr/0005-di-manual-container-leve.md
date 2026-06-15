# 0005. DI manual via Container leve

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, di, container

## Contexto

A arquitetura do backend exige Inversão de Dependência ([ADR-0002](./0002-solid-pragmatico.md)) nas fronteiras com infraestrutura: services dependem de **Protocols** (`UsuarioRepositoryProtocol`, `JwtServiceProtocol`, etc.), não de implementações concretas. Alguém precisa **construir** as implementações e **amarrá-las** aos services no startup.

FastAPI já oferece `Depends()` — bom pra resolver dependências por requisição. Mas há nuances:

1. Algumas dependências são **singletons** (engine do banco, JWT service com chave estática, hash service com config fixa). Recriar a cada request é desperdício.
2. **Grafos de dependência crescem rápido**: `AuthService` precisa de `UsuarioRepo + RefreshTokenRepo + HashService + JwtService`. Cada um deles pode ter sub-dependências. Sem centralização, instanciar manualmente vira espaguete.
3. Queremos **um único composition root** ([ADR-0001](./0001-organizacao-feature-sliced.md)) — não 4 arquivos criando suas próprias instâncias.

Opções consideradas: container custom leve, biblioteca dedicada (`dependency-injector`, `punq`, `wireup`), ou usar só `Depends()`.

## Decisão

Implementamos um **container manual leve** em `src/container.py`:

- Classe `Container` com `register_singleton(key, factory)` e `resolve(key)`.
- Factories são closures que recebem o próprio container (permite resolver dependências aninhadas).
- Singletons são cacheados após primeira resolução.
- A construção real (`construir_container(settings)`) vive numa função separada e é o único lugar onde implementações concretas são instanciadas.
- Métodos tipados por feature (`container.auth_service() -> AuthService`) dão type safety no ponto de uso.
- FastAPI consome via `Depends(lambda: container.auth_service())` dentro do `criar_router(container)` de cada feature.

Total esperado do `container.py` quando o sistema estiver completo: ~150-200 linhas. Sem mágica, sem reflection, sem decorators.

## Consequências

### Positivas
- **Zero dependência externa pra DI** — menos uma lib pra debugar, atualizar, conviver com breaking changes.
- **Fluxo explícito:** dá pra ler o `container.py` de cima a baixo e entender o grafo. Sem grafo implícito.
- **Type checking funciona:** `container.auth_service()` retorna `AuthService` real, mypy pega.
- **Fácil de testar:** em testes podemos construir um container alternativo com mocks (`Container` aceita qualquer factory).
- **Combina natural com `Depends()`:** FastAPI cuida do escopo de request, container cuida do escopo de aplicação.

### Negativas
- **Strings como keys ('AuthService')** são frágeis — typo vira `KeyError` em runtime. Mitigado pelos métodos tipados (`auth_service()`) que escondem as strings.
- **Manutenção manual conforme features crescem** — adicionar feature nova exige editar `container.py`. Não é grande coisa, mas é trabalho repetitivo.
- **Sem auto-wiring** — não escaneia classes por type hint. Decisão consciente: explicitude > magia.

### Neutras
- Convenção: **só `main.py` e `container.py` instanciam implementações concretas**. Todo resto recebe via injeção.

## Alternativas consideradas

### Alternativa A — `dependency-injector` (biblioteca madura)
Container declarativo, providers, sub-containers, async support. **Por que foi descartada:** poderosa demais pra escala atual. Adiciona DSL própria (`providers.Factory`, `providers.Singleton`, `Configuration`), curva de aprendizado real, e debug fica mais opaco. O ganho marginal não compensa pra um projeto com ~10-15 dependências singleton.

### Alternativa B — `punq` ou `wireup` (leves, auto-wiring)
Resolução por type hint, registro mais conciso. **Por que foi descartada:** auto-wiring esconde o grafo de dependências. Em uma codebase que vai ter pessoas novas entrando, **ver o grafo é valor**. Container manual força essa visibilidade.

### Alternativa C — Só `Depends()` do FastAPI, sem container
Cada rota declara dependências por composição de `Depends`. **Por que foi descartada:** funciona pra grafos rasos, mas pra montar `AuthService(usuario_repo, token_repo, hash, jwt)` exigiria uma cadeia de funções `Depends` aninhadas espalhadas — perdemos o composition root único. Além disso, singletons de aplicação ficam awkward (FastAPI `Depends` é por request por padrão; `use_cache=True` ajuda mas não é por aplicação).

### Alternativa D — Classes "Service Locator" globais
Variável módulo `auth_service = AuthService(...)`. **Por que foi descartada:** ordem de import vira problema, teste fica difícil (precisa patchear globals), reset entre testes é frágil.

## Referências

- [Mark Seemann — Dependency Injection Principles, Practices, and Patterns](https://www.manning.com/books/dependency-injection-principles-practices-and-patterns) — referência conceitual.
- Spec do projeto: `docs/spec_arquitetura.md` §Injeção de Dependências.
- [ADR-0002 — SOLID pragmático](./0002-solid-pragmatico.md) — onde está o critério de "DIP só em fronteiras de infra".

## Notas de revisão

Re-avaliar se o `container.py` passar de ~250 linhas — sinal de que estamos registrando coisa demais. Investigar se algumas factories podem virar funções locais nas próprias features.
