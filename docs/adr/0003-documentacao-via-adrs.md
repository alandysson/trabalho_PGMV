# 0003. Documentação via ADRs

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** documentação, processo

## Contexto

Decisões arquiteturais carregam peso desproporcional ao tempo gasto pra tomá-las. Uma escolha entre SQLite e Postgres feita em 30 minutos pode impor restrições por anos. Os motivos costumam viver em **conversas, threads de Slack, comentários soltos em PR** — e desaparecem assim que as pessoas envolvidas saem ou esquecem.

O sintoma clássico: alguém pergunta "por que usamos X em vez de Y?", e a resposta é "acho que foi porque…" — chute, não fato. Decisões viram lendas. Times re-discutem o mesmo tópico a cada 6 meses.

Documentação tradicional (wikis, READMEs, comentários no código) falha por três razões:
1. **Não tem dono claro** — quem garante que está atualizada?
2. **Mistura "o que" com "por que"** — descreve o sistema atual, não a história das escolhas.
3. **Some no fluxo** — não está versionada junto ao código, drifta.

## Decisão

Adotamos **Architecture Decision Records (ADRs)** no formato **MADR** (Markdown Any Decision Records). Cada decisão arquitetural significativa vira um arquivo `.md` em `docs/adr/NNNN-titulo-curto.md`, versionado junto ao código.

Cada ADR contém: **Contexto** (forças/restrições), **Decisão** (escolha em 1-2 sentenças), **Consequências** (positivas/negativas/neutras) e **Alternativas consideradas** (pelo menos uma, com motivo de descarte).

**ADRs são imutáveis em mérito.** Pequenos ajustes de redação são permitidos; mudar a decisão exige uma ADR nova com status `Substituído por ADR-XXXX` na antiga. Isso preserva a história — quem ler daqui a um ano vê tanto a decisão atual quanto a antiga.

## O que vira ADR (e o que não vira)

**Vira ADR:**
- Escolha de framework, banco, padrão arquitetural.
- Mudança de fluxo de auth, modelo de dados crítico.
- Adoção/abandono de biblioteca grande.
- Convenções que cruzam várias features (organização de pastas, estilo de erro, etc.).

**Não vira ADR:**
- Implementação de uma feature específica (vai em código + README da feature).
- Bug fix, refator local, ajuste de dependência menor.
- Convenções de estilo (linter cobre).

## Consequências

### Positivas
- **Histórico defensável:** "por que SQLite?" responde com um link.
- **Onboarding fica concreto:** novo dev lê 10 ADRs e entende a essência do projeto.
- **Discussões focadas:** ao propor mudar algo, alguém precisa contrapor a ADR original.
- **Fica no Git:** sem ferramenta separada, sem login extra. Diff visível.

### Negativas
- **Custo de escrita:** uma ADR boa leva 30-60 minutos. Tempo real.
- **Risco de "ADR teatro":** preencher pra parecer formal sem refletir a decisão real. Mitigado mantendo o formato curto e exigindo alternativas reais.
- **Pode virar burocracia:** se for exigida pra tudo, vira atrito. Mitigado pelo escopo claro acima.

### Neutras
- Vira hábito do time pensar "isto vale ADR?".
- Numeração monotônica — números antigos ficam reservados pra sempre, mesmo se a ADR for descartada.

## Alternativas consideradas

### Alternativa A — Y-statements
Formato compacto: "No contexto X, frente à força Y, decidimos Z, aceitando Q." **Por que foi descartada:** muito denso, perde a seção de **alternativas consideradas**, que é frequentemente a parte mais valiosa. Bom como resumo executivo dentro de uma ADR maior, não como formato único.

### Alternativa B — RFCs longos (estilo IETF)
Documentos de 5-10 páginas com requisitos formais. **Por que foi descartada:** overhead alto demais pra escala de equipe pequena (1-3 devs). RFCs são úteis em projetos cross-team grandes (Rust, Kubernetes). Aqui, MADR é o ponto ideal.

### Alternativa C — Wiki externa (Notion, Confluence)
Documentação fora do repo. **Por que foi descartada:** drifta. Versionamento separado do código gera contradição: código muda, wiki não. ADRs no Git acompanham a evolução naturalmente — e ficam acessíveis offline, no PR, no `grep`.

### Alternativa D — Apenas comentários no código
Anotar decisões inline. **Por que foi descartada:** funciona pra micro-decisões locais, mas comentários espalhados não substituem contexto centralizado. E ninguém lê comentários ao chegar num projeto novo — lê o `docs/`.

## Referências

- [MADR — Markdown Any Decision Records](https://adr.github.io/madr/)
- [Documenting Architecture Decisions — Michael Nygard, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) — texto original que popularizou ADRs.
- [adr.github.io](https://adr.github.io/) — catálogo de formatos.
- Spec do projeto: `docs/spec_arquitetura.md` §Estrutura de ADRs.

## Notas de revisão

Re-avaliar formato se o catálogo crescer pra >30 ADRs e ficar difícil navegar. Pode valer adicionar tags/categorias automatizadas no índice.
