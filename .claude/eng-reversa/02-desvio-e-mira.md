# Desvio (Flee) e Mira (Hit) — fórmulas e proporções

> Engenharia reversa do código-fonte (modo **Renewal**).
> Fontes: `src/map/status.cpp:2638-2648` (cálculo dos stats Hit e Flee) e
> `src/map/battle.cpp:3228-3316` (`is_attack_hitting`, onde Hit e Flee se enfrentam).

## Resposta curta

**Hit e Flee crescem LINEARMENTE com os atributos** (ao contrário da ASPD). A chance de
acerto é uma diferença simples `Hit_do_atacante − Flee_do_alvo`, somada a uma base, e depois
limitada entre um piso e um teto.

## Os dois stats (Renewal)

### Hit (mira / precisão) — do atacante

```
Hit = nível_base + DEX + (LUK / 3) + 175 + 2×CON
```

(`src/map/status.cpp:2640-2642`; o `+175` é a base de jogador, `2×CON` só afeta 4ª classe)

- **DEX**: +1 de Hit por ponto (linear, peso 1).
- **LUK**: +1 de Hit a cada 3 pontos (linear, peso 1/3).
- **Nível base**: +1 por nível.

### Flee (desvio / esquiva) — do alvo

```
Flee = nível_base + AGI + (LUK / 5) + 100 + 2×CON
```

(`src/map/status.cpp:2645-2647`; o `+100` é base de jogador, `2×CON` só 4ª classe)

- **AGI**: +1 de Flee por ponto (linear, peso 1).
- **LUK**: +1 de Flee a cada 5 pontos (linear, peso 1/5).
- **Nível base**: +1 por nível.

> Pré-Renewal é mais simples ainda: `Hit = nível + DEX`, `Flee = nível + AGI`
> (`src/map/status.cpp:2705-2711`), sem contribuição de LUK. Nosso servidor é Renewal.

## Como Hit e Flee se enfrentam (a chance de acerto real)

Em `src/map/battle.cpp:3258-3316`:

```
hitrate = 0            (Renewal; em pré-Renewal a base é 80)
hitrate += Hit_atacante − Flee_alvo
hitrate = clamp(hitrate, min_hitrate, max_hitrate)   → default 5% a 100%

acerta se:  rnd()%100 < hitrate
```

(caps em `src/map/battle.cpp:8421-8422`: `min_hitrate: 5`, `max_hitrate: 100`)

### Proporção / interpretação

- É uma **corrida linear direta**: cada ponto de Hit seu cancela exatamente 1 ponto de Flee
  do inimigo. A "chance de errar" é `Flee_alvo − Hit_atacante` pontos percentuais.
- Por causa do `min_hitrate: 5`, **você sempre tem no mínimo 5% de chance de acertar**, por
  mais alto que seja o Flee do alvo (a não ser skills especiais).
- E `max_hitrate: 100` significa que uma vez que seu Hit supera o Flee do alvo em 100+, você
  acerta 100% (ataques normais).
- Penalidade de multidão (`agi_penalty_*`): quando 3+ inimigos batem no mesmo alvo, o Flee
  do alvo cai (`src/map/battle.cpp:3266-3276`) — relevante para mobs cercados, não pra você
  sozinho.

## Perfect Dodge (Flee2) — o "desvio de sorte"

Existe um segundo tipo de esquiva, **independente** do Hit do atacante:

```
Flee2 (perfect dodge) = LUK / 10 + 10       (em décimos: cada 10 LUK = +1% de perfect dodge)
```

(`src/map/status.cpp:2735-2738`; exibido como `flee2/10` em `src/map/clif.cpp:4157`)

Perfect dodge é rolado antes da conta de hitrate e, se der, o ataque erra **independente da
mira do atacante** — é o espelho do critical (ver doc 03). Escala LINEARMENTE com LUK, bem
devagar (10 LUK = 1%).

---

## Resumo das conclusões

1. **Hit e Flee são LINEARES** nos atributos (sem retorno decrescente, ao contrário da
   velocidade). `Hit ≈ nível + DEX + LUK/3 + 175`; `Flee ≈ nível + AGI + LUK/5 + 100`.
2. **DEX** é o motor da mira (peso 1); **AGI** é o motor do desvio (peso 1); **LUK** ajuda os
   dois de leve (1/3 no Hit, 1/5 no Flee).
3. A chance de acerto é uma **corrida direta**: `chance% = Hit_seu − Flee_inimigo`, limitada
   entre **5% (piso) e 100% (teto)**. Cada ponto seu cancela 1 do inimigo.
4. Sempre há no mínimo **5% de acerto** e, se seu Hit superar o Flee inimigo em 100+, **100%**
   de acerto (ataques normais).
5. **Perfect Dodge** (Flee2 = LUK/10 + 10, em %) é uma esquiva independente da mira do
   atacante — fura a conta de Hit/Flee e até esquiva de críticos (ver doc 03).
