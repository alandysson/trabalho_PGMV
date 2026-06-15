# 0009. JWT (access curto) + Refresh Token opaco rotacionado

- **Data:** 2026-06-05
- **Status:** Aceito
- **Decisores:** Equipe de arquitetura
- **Tags:** backend, auth, segurança

## Contexto

O backend precisa autenticar requests vindas de um app móvel (React Native/Expo). Restrições do cenário:

1. **App offline-tolerante:** o usuário não quer relogar a cada poucos minutos. Sessões longas (~30 dias) são esperadas.
2. **Performance:** rotas autenticadas serão a maioria das chamadas. Hit no banco a cada validação é caro.
3. **Revogabilidade:** logout precisa funcionar de verdade — não basta deletar local. Roubo de dispositivo precisa permitir invalidar tudo.
4. **Detecção de roubo de token:** se um refresh vazar, precisamos de algum sinal automático.
5. **Time pequeno:** não temos banda pra OAuth + IdP separado.

Modelos de autenticação considerados: sessões clássicas (cookie + server-side), JWT longo sem refresh, JWT curto + refresh em banco rotacionado, OAuth/social login.

## Decisão

Adotamos **JWT HS256 (access) + refresh token opaco em banco (rotacionado a cada uso)**:

- **Access Token (JWT)**: 15 minutos, HS256, payload `{sub, email, iat, exp}`. Stateless — valida com a chave, sem hit no banco.
- **Refresh Token**: string opaca `f"rt_{secrets.token_urlsafe(48)}"`, validade 30 dias, **armazenada como SHA-256 no banco** (ver [ADR-0010](./0010-securestore-mobile-sha256-backend.md)). Pode ser revogada.
- **Rotação obrigatória**: cada `/auth/refresh` revoga o refresh atual (`motivo='rotacao'`) e emite um novo. O `substituido_por_id` registra a cadeia.
- **Detecção de invasão**: se um refresh **já revogado** for apresentado, **todos os refresh tokens ativos do usuário** são revogados (`motivo='seguranca'`), evento é logado e a resposta é 401. Defesa em profundidade contra atacante que copiou um refresh antes do legítimo rotacionar.
- **Header `X-Token-Expired: true`** em respostas 401 quando o erro é especificamente expiração do JWT — sinal não ambíguo pro cliente disparar refresh.

## Consequências

### Positivas
- **Performance alta:** maioria das requests passa por verificação de assinatura JWT, sem banco.
- **Sessões longas viáveis:** 30 dias sem precisar relogar.
- **Revogação real:** logout, troca de senha e detecção de invasão funcionam de verdade.
- **Detecção de invasão automática:** sem precisar de heurísticas complexas (geo-IP, device fingerprint).
- **Independência de Redis/cache externo:** tudo no SQLite ([ADR-0006](./0006-sqlite-sqlmodel.md)).

### Negativas
- **Access token não pode ser revogado** durante seus 15 min. Trade-off aceito: dano de vazamento limitado pela janela curta.
- **Mais complexo que sessão clássica:** dois tokens, rotação, hash, detecção de invasão. Time precisa entender o modelo (mitigado por esta ADR e código com nomes claros).
- **Cliente precisa de lógica de refresh automático** (lock global pra evitar refresh concorrente, retry com flag). Documentado na spec do mobile.
- **Cada refresh é 1 INSERT + 1 UPDATE no banco.** Pra carga prevista, ok; pra alta escala, considerar fila de eventos.

### Neutras
- Chave HMAC (`JWT_SECRET_KEY`) é segredo crítico — vaza, todo mundo emite token válido. Em produção, secrets manager.
- Logs de segurança em arquivo separado (`logs/seguranca.log`) — facilita auditoria, mas exige rotação de arquivo em prod.

## Alternativas consideradas

### Alternativa A — Sessões clássicas (cookie + server-side)
Tabela `sessions` no banco, cookie HttpOnly. **Por que foi descartada:** app móvel não tem boa ergonomia com cookies (precisa de cookie jar nativo, sticky between apps, problemas com webview). Cookies funcionam melhor pra web; pra mobile, Bearer header em SecureStore é idiomático.

### Alternativa B — JWT longo sem refresh
Um único JWT de 30 dias. **Por que foi descartada:** **sem mecanismo de revogação**. Logout vira "delete local sem garantia". Vazamento = comprometimento até expirar. Inaceitável pra qualquer cenário com dado de usuário.

### Alternativa C — JWT + refresh **não-rotacionado**
Refresh dura 30 dias mas não rotaciona. **Por que foi descartada:** sem detecção de roubo. Se atacante copiar o refresh, fica usando junto do legítimo sem alarme. Rotação é a defesa.

### Alternativa D — OAuth / social login (Google, Apple)
Delegar auth pra provedor externo. **Por que foi descartada:** complexidade desproporcional pro escopo atual (1 dev, MVP). Boa **adição futura** (sign-in com Apple é exigência da App Store, então virá), mas não como única opção. Pode coexistir com email/senha próprio.

### Alternativa E — Opaque tokens (sem JWT)
Todo access token também opaco, validado por hit em banco. **Por que foi descartada:** mata o ganho de performance. Aceitamos a janela de 15 min do JWT pra ter validação stateless.

## Referências

- [OWASP — JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [RFC 6749 §1.5](https://datatracker.ietf.org/doc/html/rfc6749#section-1.5) — sobre refresh tokens em OAuth 2.0.
- [Auth0 — Refresh Token Rotation](https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)
- Spec do projeto: `docs/spec_autenticacao.md`.
- [ADR-0010 — SecureStore mobile + SHA-256 backend](./0010-securestore-mobile-sha256-backend.md)

## Notas de revisão

Re-avaliar quando:
- **Volume de refresh** chegar a >100/seg sustentados → considerar fila de eventos em vez de UPDATE síncrono.
- Surgir requisito de **device-level revocation** (revogar só sessão de um dispositivo específico) — hoje o refresh já tem `user_agent`/`ip`, mas a UI ainda não expõe.
- **Sign-in com Apple** for adicionado (provavelmente necessário pra App Store) — esta ADR continua válida pra contas email/senha; ADR nova cobre social login.
