# 0010. SecureStore no app + SHA-256 dos refresh tokens no backend

- **Data:** 2026-06-05
- **Status:** Aceito (escopo atual: backend; seção mobile marcada como **TODO** até o app ser tocado)
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, mobile, auth, segurança

## Contexto

Os tokens emitidos por [ADR-0009](./0009-jwt-refresh-token-rotacionado.md) precisam ser **armazenados** em dois lugares:

1. **No cliente (app mobile)** — pra reenviar nas requests autenticadas.
2. **No servidor (banco)** — pra permitir validação, revogação e auditoria de refresh tokens.

Cada lado tem ameaças distintas:

- **No cliente**: app malicioso lendo o sandbox, dispositivo rooted/jailbroken, backup em nuvem expondo storage não-criptografado.
- **No servidor**: vazamento do banco de dados (SQL injection, backup vazado, attacker com acesso ao filesystem).

Decisão precisa endereçar ambos com mecanismos que tornem o ataque inviável **mesmo no pior caso de vazamento**.

## Decisão

Duas medidas complementares:

### Backend (escopo desta sessão)

Refresh tokens são **emitidos em plain** pro cliente, mas **persistidos como SHA-256** no banco. Coluna `refresh_tokens.token_hash` é o hex do SHA-256 do plain; o servidor nunca armazena o valor original.

Implementação:
- `gerar_refresh_token_plain()` → `f"rt_{secrets.token_urlsafe(48)}"` (>256 bits de entropia).
- `hashear_refresh_token(plain)` → `hashlib.sha256(plain.encode()).hexdigest()`.
- Busca no banco sempre por `WHERE token_hash = sha256(plain_recebido)`.

Por que **SHA-256 sem salt** (e não bcrypt como senhas):
- O token plain tem entropia altíssima (>256 bits) — brute force é inviável.
- Precisamos buscar o registro pelo hash → função precisa ser determinística (salt quebraria isso).
- Performance importa: refresh é chamado por todo cliente a cada 15 min.
- Bcrypt seria overkill e prejudicaria latência.

Senha continua com **bcrypt + salt automático** (rounds=12) — natureza diferente: entropia baixa, busca por email não pelo hash.

### Mobile (TODO — escopo de sessão futura)

Quando o app for implementado, a regra é: **`expo-secure-store` (Keychain/Keystore), nunca AsyncStorage**.

Resumo da especificação que será detalhada quando o app entrar em desenvolvimento:
- `tokenStorage.salvarAccess`, `salvarRefresh`, `obterAccess`, `obterRefresh`, `limparTudo` — wrappers tipados sobre `SecureStore`.
- `AsyncStorage` proibido pra tokens (texto plano + leitura por qualquer app no dispositivo rooted).
- Cliente HTTP intercepta 401 + `X-Token-Expired: true` e dispara refresh automático com lock global (evita refreshes concorrentes que invalidam uns aos outros pela rotação).

Esta ADR será revisitada (ou substituída) quando o app for tocado.

## Consequências

### Positivas
- **Vazamento do banco backend não permite uso dos refresh tokens** — atacante teria apenas hashes inúteis.
- **Latência de refresh permanece baixa** (1 hash + 1 SELECT por id, índice cobrindo).
- **Defesa em camadas:** mesmo com SecureStore no cliente comprometido, o atacante ainda enfrenta rotação + detecção de invasão ([ADR-0009](./0009-jwt-refresh-token-rotacionado.md)).
- **Modelo claro de threat:** cada lado tem sua medida e racional.

### Negativas
- **Não dá pra "ver" tokens no banco pra debug** — só hashes. Mitigado pela auditoria via `id`, `usuario_id`, `criado_em`, `ultimo_uso_em`.
- **Mobile precisa de `expo-secure-store`** (já é dependência prevista da stack — sem custo extra).
- **Reset de senha via DBA não funciona pra refresh tokens** — única ação é `revogado=True`. Aceito; é o ponto da imutabilidade.

### Neutras
- Vocabulário: dizer "token plain" pra valor enviado ao cliente, "token_hash" pra valor no banco.

## Alternativas consideradas

### Alternativa A — Armazenar refresh tokens em plain no banco
**Por que foi descartada:** vazamento do banco = todos os refresh tokens utilizáveis até expirar (30 dias). Risco inaceitável.

### Alternativa B — Bcrypt pros refresh tokens
**Por que foi descartada:** bcrypt é não-determinístico (salt aleatório) — não dá pra buscar `WHERE token_hash = ?`. Teríamos que iterar todos os tokens de um usuário e bcrypt.verify cada um. Mata latência.

### Alternativa C — Criptografia simétrica (AES) no banco
Armazenar `aes_encrypt(token_plain, KEK)`. **Por que foi descartada:** chave KEK ficaria no servidor; vazamento simultâneo de banco + chave = mesmo problema do plain. SHA-256 é estritamente melhor: sem chave, sem reversão.

### Alternativa D — Mobile com `AsyncStorage`
**Por que foi descartada:** `AsyncStorage` não é criptografado. Qualquer app rooted/jailbroken consegue ler `/data/data/...`. Em iOS, backups iCloud sem criptografia também expõem. `expo-secure-store` usa **Keychain** (iOS) e **Keystore** (Android) — proteção em hardware quando disponível.

### Alternativa E — Mobile com criptografia simétrica em cima do AsyncStorage
Cifrar antes de salvar. **Por que foi descartada:** onde guardar a chave? Se na AsyncStorage também, é só obfuscação. `expo-secure-store` resolve com Keychain/Keystore nativos — solução pronta, sem reinventar.

## Referências

- [Expo SecureStore docs](https://docs.expo.dev/versions/latest/sdk/securestore/)
- [Apple — Keychain Services](https://developer.apple.com/documentation/security/keychain_services)
- [Android — Keystore system](https://developer.android.com/training/articles/keystore)
- [NIST SP 800-63B §5.1.7](https://pages.nist.gov/800-63-3/sp800-63b.html#sec5) — orientações sobre armazenamento de tokens.
- [ADR-0009 — JWT + refresh token rotacionado](./0009-jwt-refresh-token-rotacionado.md)
- Spec do projeto: `docs/spec_autenticacao.md`.

## Notas de revisão

- **Revisitar a seção mobile** quando o app for implementado, possivelmente substituindo esta ADR por uma `0010b` específica de mobile.
- Avaliar uso de **bcrypt** ou **argon2id** nos refresh tokens se algum dia tivermos motivo pra preferir hash com custo computacional ajustável (ex.: tokens curtos pra confirmação de email com baixa entropia).
