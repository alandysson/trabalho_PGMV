# 0001. Organização Feature-Sliced

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, mobile, organização

## Contexto

Todo projeto Python/Node de tamanho médio para grande enfrenta uma decisão estrutural cedo: **como agrupar arquivos**. As duas abordagens dominantes são:

1. **Por tipo técnico** — `controllers/`, `services/`, `repositories/`, `models/`. Familiar pra quem vem de MVC clássico (Spring, Rails, NestJS default).
2. **Por feature/domínio** — `auth/`, `videos/`, `temas/`, cada uma contendo *suas* rotas, serviços, repositórios, modelos. Padrão *Feature-Sliced Design* no frontend, *Vertical Slice Architecture* no backend.

Este projeto tem 4 features distintas no backend (`auth`, `videos`, `temas`, `pipeline`) e 4 no mobile (`auth`, `temas`, `videos`, `configuracoes`). A maior parte do trabalho de manutenção será **focada numa feature por vez** — adicionar um endpoint de vídeos, ajustar a tela de configurações, debugar o login. Quase nunca um trabalho atravessa todas as camadas técnicas de todas as features ao mesmo tempo.

A pressão prática: ao mexer em "vídeos", quero abrir uma pasta e ter rotas, lógica de negócio, persistência e schemas perto. Não quero caçar 4 arquivos em 4 pastas distantes.

## Decisão

Adotamos **organização Feature-Sliced** como padrão estrutural do projeto. Cada feature é uma pasta autocontida com suas próprias subcamadas internas. Em vez de `src/controllers/auth_controller.py + src/services/auth_service.py + src/repositories/auth_repository.py`, temos `src/auth/{routes,service,data,domain}.py`. O mesmo princípio aplica-se ao app mobile (`src/features/auth/{ui,data,domain,store}`).

## Consequências

### Positivas
- **Coesão alta:** arquivos que mudam juntos vivem juntos. Pull requests ficam mais focados.
- **Onboarding mais rápido:** um dev novo entende uma feature sem precisar mapear 5 pastas.
- **Deleção segura:** descartar uma feature inteira é `rm -rf` numa pasta.
- **Fronteiras explícitas:** o `__init__.py` (ou `index.ts`) declara a interface pública da feature — fica óbvio o que é interno.
- **Escala melhor com o time:** times podem "possuir" features inteiras sem pisar uns nos outros.

### Negativas
- **Repetição percebida:** cada feature tem seu `service.py`, `routes.py` etc. — parece duplicado pra quem está acostumado com o agrupamento por tipo.
- **Código compartilhado precisa de disciplina:** o que é genuinamente reutilizável vai pra `shared/`. Sem rigor, vira gaveta de bagunça.
- **Quebra a expectativa do MVC clássico:** novos contribuintes vindos de Django/Spring podem estranhar no início.

### Neutras
- Vocabulário muda: falamos "feature" como unidade primária, não "controller layer".
- Convenções de import precisam ser ensinadas (só do `__init__.py` da feature alheia).

## Alternativas consideradas

### Alternativa A — Organização por tipo técnico (`controllers/`, `services/`, `repositories/`)
Padrão MVC clássico. **Por que foi descartada:** força você a navegar entre 4 pastas pra entender ou alterar UMA feature. Coesão baixa, acoplamento espalhado. Funciona em projetos com poucas features ou times pequenos, mas envelhece mal.

### Alternativa B — Clean Architecture dogmática (`adapters/`, `usecases/`, `entities/`, `frameworks/`)
Camadas concêntricas estritas, sem agrupamento por feature. **Por que foi descartada:** excelente em sistemas com regras de domínio complexíssimas (banco, seguro), mas neste projeto (uma API que coordena geração de vídeo) o overhead de 4 camadas universais é desproporcional ao benefício. Ver também [ADR-0002](./0002-solid-pragmatico.md).

### Alternativa C — Monolítico plano (`src/*.py`, sem subpastas)
Tudo na raiz de `src/`. **Por que foi descartada:** o pipeline antigo (em `legacy/`) era assim e ficou ilegível com 8 arquivos. Com 20+ arquivos esperados pro backend novo, seria insustentável.

## Referências

- [Vertical Slice Architecture — Jimmy Bogard](https://www.jimmybogard.com/vertical-slice-architecture/)
- [Feature-Sliced Design (frontend)](https://feature-sliced.design/)
- Spec do projeto: `docs/spec_arquitetura.md` §1 e §2.

## Notas de revisão

Re-avaliar se o projeto crescer pra >10 features e começarmos a ver duplicação real entre `service.py`s — nesse cenário, podemos precisar de uma camada `domain/` cross-feature.
