# Sorte e Crítico — probabilidade de crítico e a relação com a mira

> Engenharia reversa do código-fonte (modo **Renewal**).
> Fontes: `src/map/status.cpp:2723-2733` (stat Cri a partir de LUK),
> `src/map/battle.cpp:3017-3155` (`is_attack_critical`, cálculo da chance),
> `src/map/battle.cpp:3236-3240` (a prova de que crítico ignora a mira).

## Respostas curtas

1. **A chance de crítico cresce LINEARMENTE com LUK** (cada 1 LUK ≈ +0.3% de crítico).
2. **SIM — quando você tira um crítico, o golpe acerta SEMPRE**, mesmo que sua mira (Hit)
   seja menor que o desvio (Flee) do inimigo. O crítico é checado *antes* da conta de
   acerto e faz `return true` imediato. Crítico ignora Flee.

## O stat Cri (chance base de crítico)

```
Cri = 10 + LUK×3 + (nível_base / 10)         (Renewal, em "permil" — milésimos)
```

(`src/map/status.cpp:2725-2730`)

- O valor é guardado em **milésimos** (base 1000). O client mostra `Cri/10`
  (`src/map/clif.cpp:4158`), então o número da janela de status é a porcentagem real.
- `LUK×3` em milésimos = **+0.3% de crítico por ponto de LUK** → totalmente linear.
- `+10` base = 1% inicial. `nível/10` é uma contribuição pequena do nível base.

Exemplo: LUK 100 → `Cri = 10 + 300 + nível/10 ≈ 310+` milésimos ≈ **~31% de crítico base**.

### Tabela de crítico por faixa de LUK (sem bônus de arma/carta)

| LUK | crítico @ nível 100 | crítico @ nível 250 |
|----:|--------------------:|--------------------:|
| 0   | 2.0%                | 3.5%                |
| 10  | 5.0%                | 6.5%                |
| 30  | 11.0%               | 12.5%               |
| 50  | 17.0%               | 18.5%               |
| 70  | 23.0%               | 24.5%               |
| 100 | 32.0%               | 33.5%               |
| 130 | 41.0%               | 42.5%               |
| 160 | 50.0%               | 51.5%               |
| 200 | 62.0%               | 63.5%               |
| 255 | 78.5%               | 80.0%               |

## Vai chegar uma hora que não vale mais a pena subir LUK? (≠ da velocidade!)

**Não do mesmo jeito que a AGI.** O crítico é **perfeitamente linear**: cada +10 de LUK dá
sempre **+3% de crítico**, do começo ao fim (veja a coluna: 10→30→50 LUK sobe exatos +6% a
cada +20). Não existe o "retorno decrescente" da velocidade — cada ponto de LUK vale o mesmo
que o anterior.

O que existe é um **teto de 100%** (a rolagem é `rnd()%1000 < cri`, satura em 1000 milésimos):

- No nosso servidor, com o cap de stat em **LUK 255**, você chega a **~80% de crítico** só de
  LUK (nível 250). Para 100% puro de LUK precisaria de ~322 de LUK — **acima do cap 255**,
  então **não dá pra "desperdiçar" LUK batendo no teto** só com stat.
- Ou seja: **todo ponto de LUK até 255 rende crítico de verdade** (nunca vira desperdício por
  overflow, ao contrário da AGI que satura no cap de velocidade bem antes do 255).

**Os dois "freios" reais do crítico** (não são retorno decrescente, são subtrações):

1. **LUK do alvo:** `cri −= LUK_alvo × 2` (`battle.cpp:3061`). Contra inimigos de sorte alta,
   parte do seu crítico é anulada — 1 ponto de LUK dele cancela ~0.2% do seu crítico.
2. **Skills que cortam pela metade** (Cross Impact e afins, `battle.cpp:3141`) — situacional.

Então a decisão "vale a pena mais LUK?" para crítico é **estratégica** (quão perto de 100%
você quer chegar, e qual a sorte dos inimigos que enfrenta), **não** um limite matemático de
retorno decrescente como na velocidade de ataque.

## A rolagem de crítico (o que realmente acontece no ataque)

Em `src/map/battle.cpp:3046-3152`:

```
cri = Cri_do_atacante
cri += bônus de carta/arco/skills (critaddrace, arrow_cri, etc)
cri −= LUK_do_alvo × 2          (o alvo resiste com a própria sorte!)
... ajustes por skill (alguns dobram, outros cortam pela metade) ...

crítico se:  rnd()%1000 < cri
```

(`src/map/battle.cpp:3152`)

Pontos importantes:

- **A LUK do alvo reduz sua chance de crítico**: `cri −= LUK_alvo × 2` (linha 3061). Ou seja,
  crítico é uma disputa de sorte: sua LUK sobe, a LUK do inimigo desce.
- Contra um alvo controlado por outro jogador atacado por mob, o fator vira ×3 em vez de ×2
  (detalhe de PvE/PvP, `battle.cpp:3061`).
- Alvo dormindo (`SC_SLEEP`) → sua chance de crítico **dobra** (linha 3064).
- Várias skills ajustam: Auto Counter dobra, Sharp Shooting soma +300 milésimos (+30%),
  Cross Impact e afins dividem por 2 (linhas 3066-3145).

## A prova de que crítico ignora a mira

A função de acerto, `is_attack_hitting` (`src/map/battle.cpp:3228`), começa assim:

```c
if (is_attack_critical(...))
    return true;          // ← acerto garantido, nem calcula hitrate
```

(`src/map/battle.cpp:3240`)

Só **depois** disso, se não foi crítico, é que ela vai calcular `hitrate = Hit − Flee` e rolar
o dado de acerto (ver doc 02). Portanto:

> **Um golpe crítico nunca "erra" por falta de mira.** A ordem é: (1) rola o crítico; se deu
> crítico, acerta com dano crítico e acabou; (2) se não deu, aí sim disputa Hit vs Flee.

O espelho disso do lado defensivo é o **Perfect Dodge** (Flee2, ver doc 02): se o alvo tirar
perfect dodge, ele esquiva **mesmo de um ataque que seria crítico** — perfect dodge e critical
são as duas "jogadas de sorte" que furam a conta normal de Hit/Flee, uma pra cada lado.

## Resumo das proporções (tudo escala com LUK, tudo linear)

| Efeito                    | Fórmula (por ponto de LUK)     | Referência                   |
|---------------------------|--------------------------------|------------------------------|
| Chance de crítico         | +0.3% (LUK×3 em milésimos)      | `status.cpp:2730`            |
| Resistência a crítico     | −0.2% no crítico do inimigo (×2)| `battle.cpp:3061`            |
| Hit (mira)                | +1 a cada 3 LUK                 | `status.cpp:2641`            |
| Flee (desvio)             | +1 a cada 5 LUK                 | `status.cpp:2646`            |
| Perfect Dodge (Flee2)     | +1% a cada 10 LUK               | `status.cpp:2737`            |

LUK é o atributo "curinga": mexe em crítico, esquiva perfeita, mira, desvio e resistência a
crítico ao mesmo tempo — mas cada efeito individual é fraco e linear. É o oposto da AGI, que
é forte mas com retorno decrescente (ver doc 01).

---

## Resumo das conclusões

1. **Crítico é LINEAR com LUK**: sempre **+0.3% por ponto** (+3% a cada 10 LUK), do início ao
   fim — **sem retorno decrescente**, diferente da velocidade de ataque (AGI).
2. **Não vale a pena parar de subir LUK por "saturação"**: no cap de stat 255 você chega a
   **~80% de crítico** (nível 250); 100% puro de LUK exigiria ~322 (acima do cap), então
   **nenhum ponto de LUK vira desperdício por overflow**.
3. **Crítico ignora a mira**: um golpe crítico **sempre acerta**, mesmo com Hit < Flee
   (`battle.cpp:3240` retorna acerto antes de calcular hitrate).
4. O único jeito de um crítico não conectar é o alvo tirar **Perfect Dodge** (a jogada de
   sorte espelhada — ver doc 02).
5. Os freios do crítico são **subtrações** (LUK do alvo × 2; skills que cortam pela metade),
   **não** retorno decrescente. A decisão de subir mais LUK é estratégica (proximidade dos
   100% e sorte dos inimigos), não um limite matemático.
