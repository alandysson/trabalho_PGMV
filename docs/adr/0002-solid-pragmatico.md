# 0002. SOLID pragmático

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, mobile, princípios

## Contexto

SOLID é um conjunto de cinco princípios (SRP, OCP, LSP, ISP, DIP) que, aplicados bem, produzem código sustentável. Aplicados mal — dogmaticamente, em todo arquivo — produzem **boilerplate inflado, indireção excessiva e abstrações inúteis**: `IFooFactory` que tem uma implementação só, `IUserService` injetado em `IUserController` injetado em `IRouter`, fábricas de fábricas.

O custo desse excesso é real: quem lê o código gasta tempo seguindo abstrações até encontrar a linha que faz algo. E o ganho de "testabilidade teórica" raramente se converte em testes reais.

Por outro lado, **ignorar SOLID** numa codebase de tamanho não-trivial leva a acoplamento opaco — services importando ORM direto, lógica de negócio misturada com HTTP, módulos que não podem ser tocados sem efeitos colaterais.

Precisamos definir **onde aplicar SOLID com rigor** e onde aceitar simplicidade direta.

## Decisão

Aplicamos SOLID **nos pontos onde há valor mensurável**, não em todo lugar:

1. **DIP (Inversão de Dependência)** é aplicada **só em fronteiras com infraestrutura externa**: banco de dados, HTTP externo (Anthropic, Pexels), storage de arquivos, IA, TTS, transcrição. Essas são as dependências que: (a) podem ser trocadas no futuro; (b) precisam ser mockadas em testes; (c) representam I/O com chance real de falhar. Para elas: Protocol/interface no `domain/`, implementação concreta no `data/` ou `adapters/`, injeção via container.

2. **SRP** orienta a separação de arquivos: `service.py` só lógica, `routes.py` só HTTP, `repository_sqlmodel.py` só SQL. Mas não criamos uma classe nova pra cada verbo — funções e métodos de classes já são unidades SRP.

3. **OCP** aparece onde precisamos extensibilidade explícita: providers de Tema (plugin via Registry — ver [ADR-0008](./0008-plugin-architecture-temas.md)), adapters do pipeline (trocar TTS sem mexer no orchestrator). Não vamos criar `OpenForExtensionFactory` pra coisas que nunca vão se estender.

4. **LSP** é consequência de Protocols bem desenhados — não algo a ser aplicado separadamente.

5. **ISP** vira regra de bom senso: protocols pequenos e específicos (`HashServiceProtocol`, `JwtServiceProtocol`), não um `SecurityProtocol` gigante.

Regra de ouro, herdada da spec: **se uma camada não está agregando valor mensurável, ela não deve existir**.

## Consequências

### Positivas
- Código fica leve onde simplicidade é virtude (CRUD trivial não vira hexagonal).
- Indireção existe onde compensa: trocar SQLite por Postgres = trocar `repository_sqlmodel.py` por `repository_asyncpg.py`, sem tocar services.
- Testes ficam viáveis sem mocks elaborados — mockar 3-4 protocols cobre as fronteiras críticas.
- Decisões caso a caso são explicáveis: "isto tem Protocol porque é I/O", "isto não tem porque é uma função pura".

### Negativas
- Exige **julgamento contínuo** — não há regra mecânica "faça X em todo arquivo". Devs novos precisam absorver o critério.
- Pull requests podem ter discussões sobre "isto merece Protocol?". Combinamos resolver isso na revisão, não no review tardio.
- Refatorar de "sem Protocol" pra "com Protocol" depois pode ser barato ou caro, dependendo de quanto código dependia da implementação concreta.

### Neutras
- Vocabulário comum: "isto vale Protocol?" passa a ser uma pergunta corriqueira em PR.

## Alternativas consideradas

### Alternativa A — SOLID dogmático (Clean Architecture estrita)
Aplicar DIP em **todas** as dependências: cada service tem interface, cada repository tem interface, cada utilitário tem interface. **Por que foi descartada:** o custo de boilerplate excede o benefício em um projeto deste tamanho. Já vimos codebases assim com 3x o código de uma alternativa pragmática e sem testes melhores.

### Alternativa B — Ignorar SOLID
Escrever código direto, sem se preocupar com abstrações. Serviços importam SQLAlchemy diretamente; rotas chamam libs externas. **Por que foi descartada:** funciona até ~5 features, depois vira pesadelo. O projeto já tem 4 features previstas + integração com 5 APIs externas; sem fronteiras claras, ficamos presos a decisões iniciais (ex.: trocar Anthropic por outro LLM exigiria mexer em 10 lugares).

### Alternativa C — SOLID só onde for "óbvio"
Aplicar caso a caso sem critério explícito. **Por que foi descartada:** vira gosto pessoal, gera inconsistência. A regra "fronteiras com infra externa = DIP, resto = pragmatismo" é defensável e simples de ensinar.

## Referências

- *Pragmatic SOLID* — Mark Seemann.
- *Architecture, the lost years* — Robert C. Martin (Clean Arch, contrapondo a versão dogmática que rejeitamos).
- Spec do projeto: `docs/spec_arquitetura.md` §SOLID na prática.
- [ADR-0005 — DI manual via Container leve](./0005-di-manual-container-leve.md) — onde DIP é operacionalizada.

## Notas de revisão

Re-avaliar se virarmos um time grande (>5 devs no backend) onde "julgamento" deixe de ser viável e regras mais mecânicas passem a valer.
