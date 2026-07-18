# Força, ATK da arma e dano final — como eles se combinam

> Engenharia reversa do código-fonte (modo **Renewal**).
> Fontes principais: `src/map/status.cpp:2424-2496` (ATK base de STR),
> `src/map/status.cpp:3910-3960` (ATK bruto da arma, refino),
> `src/map/battle.cpp:2443-2492` (`battle_calc_base_weapon_attack`),
> `src/map/battle.cpp:3895-3945` (montagem dos "pools" de ATK),
> `src/map/battle.cpp:5525-5540` (soma final do dano).

## Respostas curtas

1. **O dano final NÃO é uma multiplicação de "ATK total" — é a SOMA de 5 "potes" de ATK
   separados**, cada um calculado de um jeito diferente: `statusAtk` (da FORÇA/DEX pura),
   `weaponAtk` (do item + refino, com variação), `equipAtk` (bônus fixos de comida/cartas),
   `percentAtk` (bônus percentuais específicos) e `masteryAtk` (skills de maestria de arma).
2. **O ATK da arma NÃO vira uma quantidade fixa/irrelevante conforme os stats sobem** — pelo
   contrário: o ATK bruto da arma (`wa.atk`, o número do item) entra numa fórmula que o
   **multiplica pelo seu STR/200** (ou DEX/200 para armas de longo alcance). Ou seja, uma arma
   de ATK mais alto rende **mais** benefício quanto mais STR você tem — os dois se potencializam
   mutuamente, não competem.
3. **Depende do tipo de "fortalecimento"**: bônus percentual de ATK (`bAtkRate`, ex: cartas
   `+X% ATK`) só multiplica `weaponAtk + equipAtk` — **não toca no seu ATK de STR** (`statusAtk`).
   Já bônus fixo de ATK (`bBaseAtk`, ex: comida) vai para o pote `equipAtk`, que também é
   multiplicado pelo `%ATK`. E skills de maestria de arma (`masteryAtk`) literalmente nascem
   *a partir* do `weaponAtk`, então escalam junto com a arma.

## Os 5 potes de ATK (Renewal)

O dano final de um ataque normal é (`src/map/battle.cpp:5525` + `:5538`):

```
dano = statusAtk + weaponAtk + equipAtk + percentAtk + masteryAtk
```

### 1. `statusAtk` — o ATK vindo da Força (STR)

```
STR_ajustado = (STR×10 + DEX×10/5 + LUK×10/3 + nível×10/4) / 10 + 5×POW
statusAtk = STR_ajustado   (dobrado depois do ajuste elemental)
```

(`src/map/status.cpp:2477`, `src/map/battle.cpp:3899-3910`)

- Não depende do item equipado. É puramente do personagem (STR principal, com um pouco de
  DEX/LUK/nível/POW misturado).
- Para armas de longo alcance (arco, arma de fogo), STR e DEX **trocam de papel** na fórmula
  (`status.cpp:2450-2459`) — quem empunha essas armas usa DEX no lugar de STR aqui.

### 2. `weaponAtk` — o ATK da arma em si (o pote que interage com STR)

Primeiro, o ATK bruto do item + bônus de refino vira `rhw.atk`:

```
rhw.atk  = Atk_do_item (item_db)
rhw.atk2 = bônus_de_refino (tabela refine.yml) [+ bônus de grau de encantamento]
watk = rhw.atk + rhw.atk2
```

(`src/map/status.cpp:3955-3957`)

Depois, na hora do ataque, isso vira o intervalo mín/máx de dano (`battle.cpp:2443-2492`):

```
variance         = 5% × Atk_do_item × nível_da_arma        (± essa variação no dano)
bonus_de_stat    = Atk_do_item × STR / 200        (DEX no lugar de STR p/ arma de longo alcance)

atk_min = watk − variance + bonus_de_stat
atk_max = watk + variance + bonus_de_stat

weaponAtk = crítico/MaximizePower? atk_max : sorteio_entre(atk_min, atk_max)
```

**Aqui está o ponto-chave da sua pergunta:** `bonus_de_stat = Atk_do_item × STR/200`. Isso é
uma **multiplicação direta** entre o ATK do item e seu STR. Dobrar o ATK da arma dobra esse
termo; dobrar o STR também dobra esse termo. **Os dois investimentos se multiplicam entre si**,
não competem — uma arma melhor vale mais quanto mais STR você tem, e vice-versa.

### 3. `equipAtk` — bônus fixos (comida, algumas cartas, flechas)

```
equipAtk = eatk (bônus fixo de "+X ATK", ex: bBaseAtk de comida) + arrow_atk (flechas)
```

(`src/map/battle.cpp:3434-3446`; a fonte do bônus fixo em `src/map/pc.cpp:3772-3778`)

### 4. `percentAtk` — bônus percentuais específicos (`bAtkRate`)

```
percentAtk = (weaponAtk + equipAtk) × atk_rate / 100
```

(`src/map/battle.cpp:3941-3944`)

**Isso responde diretamente sua pergunta sobre fortalecimentos:** um bônus do tipo "+X% ATK"
(`bAtkRate`, comum em cartas/itens) multiplica **apenas** `weaponAtk + equipAtk` — ele **NÃO
multiplica o `statusAtk`** (seu ATK de Força puro fica de fora dessa conta). Ou seja, quanto
mais forte sua arma (e bônus fixos), mais um "+% ATK" rende; a parte do dano vinda de STR puro
não ganha nada com esse tipo específico de bônus.

> Existe também um mecanismo interno (`RE_ALLATK_RATE`/`RE_ALLATK_ADD`, `battle.cpp:3562-3564`)
> que multiplica/soma em **todos** os 5 potes de uma vez — usado por poucos efeitos especiais
> (ex: bola de espírito de Homunculus). A maioria dos bônus de "% ATK" do jogo usa o caminho
> mais restrito acima (só `weaponAtk`+`equipAtk`).

### 5. `masteryAtk` — skills de maestria de arma

```
masteryAtk = battle_addmastery(... baseado no weaponAtk atual ...)
```

(`src/map/battle.cpp:3801`, soma final em `:5538`)

Skills como *Sword Mastery*, *Cart Boost*, estrelas de arma (*Weapon Perfection* etc.) entram
aqui. O ponto importante: a função recebe `weaponAtk` como parâmetro — **skills de maestria
literalmente nascem a partir do ATK da arma**, então uma arma melhor faz essas skills renderem
mais também (mais um caso onde o ATK do item se multiplica com outra fonte, em vez de competir).

## Então, o ATK da arma "se torna irrelevante" com stats altos?

**Não.** Não existe nenhum ponto no código onde o ATK da arma é "descontado" ou perde peso
conforme STR sobe. Pelo contrário: o termo `Atk_item × STR/200` faz o ATK da arma **crescer em
importância absoluta** junto com STR (são multiplicados, não somados independentes). O que
acontece é mais sutil:

- O `statusAtk` (puramente de STR, sem arma) cresce por conta própria com STR/DEX/LUK/nível,
  **mesmo com uma arma fraca**.
- Então, em **termos proporcionais**, se você tiver uma arma muito fraca (ATK baixo) e STR
  muito alto, a fatia de `statusAtk` no total pode dominar — não porque a arma "parou de
  valer", mas porque `statusAtk` não precisa da arma para crescer, enquanto o ganho extra de
  `weaponAtk` (o termo `×STR/200`) depende de ambos precisarem estar altos ao mesmo tempo para
  compensar.
- **Na prática:** trocar de arma (ATK do item) continua sendo um multiplicador direto de dano
  em qualquer nível de stat — nunca fica "de graça" ignorar a arma.

## Resumo das conclusões

1. **Dano = soma de 5 potes independentes** (`statusAtk + weaponAtk + equipAtk + percentAtk +
   masteryAtk`), não uma única fórmula multiplicativa de "ATK total".
2. **ATK da arma NÃO se torna irrelevante** com stats altos — o termo
   `Atk_item × STR/200` faz arma e STR se multiplicarem, então uma arma melhor vale cada vez
   **mais** (não menos) conforme seu STR sobe.
3. **`statusAtk` (de STR) é a única parte 100% independente da arma equipada** — cresce
   sozinha com STR/DEX/LUK/nível, então uma arma fraca não "trava" esse componente.
4. **Fortalecimentos percentuais (`bAtkRate`, "+X% ATK") só multiplicam `weaponAtk +
   equipAtk`** — o `statusAtk` (Força pura) fica de fora. Ou seja: quanto melhor sua arma
   (e bônus fixos de ATK), mais um buff de "%ATK" rende.
5. **Skills de maestria de arma (`masteryAtk`) nascem do próprio `weaponAtk`** — mais um
   mecanismo em que a arma e a skill se multiplicam, não competem.
6. Bônus fixos de ATK (comida, ex: `bBaseAtk`) entram no pote `equipAtk`, que também é alvo do
   multiplicador de `%ATK` (item 4) — diferente do `statusAtk`.
