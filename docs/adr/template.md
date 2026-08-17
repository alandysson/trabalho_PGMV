# NNNN. Título da Decisão

- **Data:** YYYY-MM-DD
- **Status:** Proposto | Aceito | Substituído por ADR-XXXX | Obsoleto
- **Decisores:** nome(s) ou papel(éis)
- **Tags:** backend | mobile | infra | segurança | …

## Contexto

Que problema estamos resolvendo? Quais forças (técnicas, de tempo, de pessoas, de
custo, de regulação) nos pressionam? Que restrições existem? Cite trechos
relevantes da spec, links pra discussões, números, dor sentida — qualquer coisa
que ajude alguém daqui a 6 meses a entender por que esta decisão foi tomada.

Evite jargão sem definição. Se mencionar uma tecnologia ou padrão pouco óbvio,
diga em uma linha o que é.

## Decisão

A escolha tomada, em uma ou duas sentenças **claras e diretas**. Não enrole.

Exemplo: "Adotamos FastAPI como framework do backend; rotas serão organizadas
por feature, não por tipo técnico."

## Consequências

### Positivas
- Item 1 — o que ganhamos com isso.
- Item 2 — outro ganho concreto.

### Negativas
- Item 1 — o que perdemos / risco assumido.
- Item 2 — onde isso vai doer mais tarde.

### Neutras
- Item 1 — mudanças que nem são bem boas nem ruins, só são (ex.: novo
  vocabulário no time, nova convenção de pastas).

## Alternativas consideradas

### Alternativa A — Nome curto
Descrição breve. **Por que foi descartada:** motivo objetivo.

### Alternativa B — Nome curto
Descrição breve. **Por que foi descartada:** motivo objetivo.

### Alternativa C — Nome curto (opcional)
…

## Referências (opcional)

- Links pra docs oficiais, RFCs, artigos.
- Discussões internas (issues, PRs).
- ADRs relacionadas: `[ADR-XXXX](./XXXX-titulo.md)`.

## Notas de revisão (opcional)

Se a decisão precisar ser revisitada quando algo mudar, registre aqui o gatilho.
Exemplo: "Re-avaliar quando passarmos de 1.000 usuários ativos diários" ou
"Re-avaliar quando o backend precisar rodar em múltiplos workers".
