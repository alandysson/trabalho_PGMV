# 0008. Plugin architecture para Temas

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, extensibilidade, ocp

## Contexto

A feature `temas` gera vídeos a partir de fontes temáticas distintas. Hoje são quatro previstas: **Histórias Bíblicas**, **Mitologia**, **Curiosidades**, **Fábulas**. Cada uma:

- Tem seu **catálogo próprio** de histórias/conteúdos.
- Pode ter **lógica específica** de escolha (evitar repetir, preferir narrativas curtas, filtrar por idade).
- Pode ter **estilo de narração e prompt** ajustado pro tom (bíblico solene vs. fábula didática).
- Pode ter **fontes diferentes** (lista fixa, Wikipedia, livro público no Project Gutenberg).

E o catálogo de temas **vai crescer** — ideias futuras incluem "ciência pra crianças", "mistérios da história", "literatura clássica resumida". Cada novo tema entra como **nova capacidade** sem desestabilizar os existentes.

A pergunta arquitetural: como estruturar isso para que **adicionar um tema novo seja seguro, isolado e barato**?

Princípios em jogo: OCP (Open/Closed — aberto pra extensão, fechado pra modificação) do [ADR-0002](./0002-solid-pragmatico.md).

## Decisão

Adotamos **arquitetura de plugins via ABC + Registry**:

1. **Interface comum** em `src/temas/domain/provider_protocol.py`: classe abstrata `BaseTemaProvider` declarando os métodos que todo tema implementa (`listar_disponiveis`, `escolher_proximo`, `obter_prompt_roteiro`, `obter_estilo_narracao`, etc.).
2. **Cada tema é uma classe concreta** em `src/temas/providers/`: `HistoriasBiblicasProvider`, `MitologiaProvider`, etc. — todas herdando de `BaseTemaProvider`.
3. **Registry centralizado** em `src/temas/registry.py`: dicionário `nome → instância de provider`, populado no startup pelo container.
4. **Serviço de Temas** (`temas/service.py`) consulta o registry, nunca conhece providers concretos individualmente.

Adicionar tema novo = (a) criar `providers/novo_tema.py` com a classe; (b) registrar uma linha no registry. **Zero modificação no service, no router ou em outros providers.**

## Consequências

### Positivas
- **Open/Closed cumprido:** adicionar tema = criar arquivo + 1 linha. Não há risco de quebrar temas existentes.
- **Isolamento de mudança:** bug específico de Mitologia? Só `providers/mitologia.py` precisa atenção.
- **Testabilidade granular:** cada provider tem seus próprios testes; mock trivial via subclasse de `BaseTemaProvider`.
- **Habilita features por tema dinamicamente:** o registry pode filtrar por flag (ex.: temas "premium" só pra assinantes).
- **API limpa pro frontend:** `GET /temas` retorna a lista pulando o registry — não há lookup hardcoded.

### Negativas
- **Custo de definir a interface certa**: se `BaseTemaProvider` ficar mal projetado, adicionar tema novo vai exigir refatorar o ABC e todos os existentes. Mitigado começando com método mínimo e ampliando só quando há caso real.
- **Dead code latente**: se um tema for descontinuado, o arquivo vira lixo se não removido. Manutenção exige disciplina.
- **Registry estático**: temas são populados no startup, não em tempo de execução. Pra carga dinâmica via DB precisaria evolução adicional. Aceitamos por enquanto.

### Neutras
- Convenção: nomes de provider em snake_case dentro de `providers/`, classes em PascalCase com sufixo `Provider`.

## Alternativas consideradas

### Alternativa A — `if/elif/else` em uma factory
Função `obter_provider(nome: str)` com cadeia `if`. **Por que foi descartada:** quebra OCP — adicionar tema exige editar a factory. Cada nova adição é um diff arriscado em código compartilhado.

### Alternativa B — Entry points via `setuptools`
Plugins descobríveis via metadata de pacote Python. **Por que foi descartada:** overkill pra plugins que vivem dentro do mesmo repositório. Entry points fazem sentido pra ecossistema onde terceiros publicam plugins independentes (ex.: pytest, sphinx). Não é nosso caso.

### Alternativa C — Configuração via YAML/JSON
Temas declarados em `temas.yaml`. **Por que foi descartada:** lógica de escolha por tema **é código** (regras condicionais, escolhas com estado, prompts específicos). Forçar declaração em YAML obrigaria a embutir DSL própria — pior que classes Python claras.

### Alternativa D — Tabela no banco com "template" de prompt
Temas viram linhas no DB com prompts armazenados como string. **Por que foi descartada:** mistura **dados** com **comportamento**. Provider de Histórias Bíblicas tem lógica de "não repetir nas últimas 20" que não cabe em string. Pode caber pra um subconjunto "temas de cobertura simples", mas misturar os dois modelos seria confuso.

## Referências

- [Strategy Pattern (GoF)](https://refactoring.guru/design-patterns/strategy) — base conceitual.
- [Registry pattern (Martin Fowler)](https://martinfowler.com/eaaCatalog/registry.html)
- Spec do projeto: `docs/spec_arquitetura.md` §Estrutura de pastas (feature `temas`).
- [ADR-0001 — Organização Feature-Sliced](./0001-organizacao-feature-sliced.md) — onde a pasta `providers/` vive.
- [ADR-0002 — SOLID pragmático](./0002-solid-pragmatico.md) — origem do compromisso com OCP aqui.

## Notas de revisão

Re-avaliar se atingirmos >10 temas. Pode valer adicionar carregamento dinâmico (ex.: scan automático de `providers/*.py`) pra eliminar a linha do registry.
