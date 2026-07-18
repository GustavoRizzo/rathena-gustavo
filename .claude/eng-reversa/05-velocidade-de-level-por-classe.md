# Velocidade de subir de nível — por que Novice sobe mais rápido que classes avançadas

> Engenharia reversa de dados (não é código C++ desta vez, é a tabela `db/re/job_exp.yml`).
> Confirma uma observação real sua: **sim, sua percepção está correta** — como Novice/1ª/2ª
> classe (não-trans) você precisa de MENOS EXP por nível do que como classe transcendente
> (ex: Lord Knight), 3ª classe ou 4ª classe, no **mesmo número de nível**.

## Resposta curta

O rAthena não usa uma fórmula matemática única de EXP por nível — usa **tabelas fixas**
(`db/re/job_exp.yml`), uma por "grupo de classes". Existem **4 grupos** com curvas
diferentes, e cada grupo mais avançado pede proporcionalmente **mais EXP** para o mesmo
nível:

| Grupo (tier)                              | Exemplo de classes                    |
|--------------------------------------------|----------------------------------------|
| Novice / 1ª classe / 2ª classe não-trans   | Novice, Swordman, Knight, Priest, Mage |
| 2ª classe **Trans** (High/Rebirth)         | Lord Knight, High Priest, High Wizard  |
| 3ª classe (regular)                        | Rune Knight, Warlock, Arch Bishop      |
| 4ª classe                                   | Dragon Knight, Meister, Arch Mage      |

(`db/re/job_exp.yml:88` primeiro grupo, `:350` segundo, `:573` terceiro, `:1041` quarto)

## Os números reais (EXP necessária por nível, `BaseExp`)

| Nível | Novice/1ª/2ª | 2ª Trans (ex: Lord Knight) | 3ª classe | 4ª classe |
|------:|-------------:|---------------------------:|----------:|----------:|
| 10    | 5.337        | 6.404 (**1.20×**)          | 6.404     | 6.404     |
| 30    | 17.362       | 22.571 (**1.30×**)         | 22.571    | 22.571    |
| 50    | 42.165       | 59.031 (**1.40×**)         | 59.031    | 59.031    |
| 70    | 103.722      | 155.583 (**1.50×**)        | 155.583   | 155.583   |
| 90    | 547.543      | 645.792 (**1.18×**)        | 645.792   | 645.792   |

**EXP total acumulada para chegar do nível 1 ao 90:**

- Como Novice/1ª/2ª classe: **6.583.073**
- Como 2ª classe Trans (ex: Lord Knight): **9.032.273** — **1.37× mais EXP** pro mesmo
  progresso de nível.

Ou seja: exatamente o que você notou. Levar seu personagem até o nível 90 como Novice
(ou Swordman/Knight, sem transcender) custa quase **27% menos EXP total** do que fazer o
mesmo caminho como Lord Knight.

## Por que o jogo foi balanceado assim?

Isso é *by design* do RO oficial, não é bug nem coisa nossa: classes mais avançadas são
objetivamente mais fortes por nível (mais HP, mais ATK, skills melhores — ver `HpFactor` e
afins em `db/re/job_stats.yml`, que também varia por classe). O jogo compensa isso pedindo
mais EXP por nível dessas classes, pra equilibrar a progressão.

## O "muro" do nível 99 (Novice/1ª/2ª só)

Tem um detalhe a mais: no grupo Novice/1ª/2ª (e também no grupo 2ª Trans), o nível 99 tem
`Exp: 9999999` — um valor gigantesco, na prática um **muro intransponível** que força você a
trocar de classe antes de continuar. Já os grupos de 3ª e 4ª classe têm um valor real ali
(`1.272.747`), permitindo continuar passando de 99 sem travar.

> **Isso já não se aplica no nosso servidor a partir do nível 100** — nós adicionamos um
> override em `db/import/job_stats.yml` (ver doc 03 do guia de setup) que dá a **mesma
> tabela de EXP (a de 4ª classe) para todos os 172 jobs**, cobrindo os níveis 100-250. Ou
> seja: a diferença de "Novice sobe mais rápido" que este documento explica **só vale para os
> níveis 1-99** (dados originais do rAthena, intocados). Do nível 100 em diante, todo mundo
> usa a mesma curva, não importa a classe.

## Resumo das conclusões

1. **Sim, sua observação está certa**: como Novice/1ª/2ª classe não-trans você sobe de nível
   com **menos EXP** do que como classe transcendente/3ª/4ª, no mesmo nível — a diferença
   cresce até **1.5×** em alguns níveis e a EXP total acumulada até o nível 90 é **1.37×**
   maior como classe trans.
2. **Não é uma fórmula contínua, são tabelas fixas por "tier" de classe**
   (`db/re/job_exp.yml`), quatro grupos: Novice/1ª/2ª, 2ª Trans, 3ª, 4ª.
3. **É proposital**: classes mais avançadas são mais fortes por nível (mais HP/ATK/skills),
   então pedem mais EXP para compensar — parte do balanceamento oficial do RO.
4. **Novice/1ª/2ª (e 2ª Trans) têm um muro no nível 99** (`Exp: 9999999`, praticamente
   impossível de superar) que força a troca de classe — 3ª e 4ª classe não têm esse muro.
5. **No nosso servidor, essa diferença só existe até o nível 99** — a partir do 100, todo
   mundo usa a mesma curva (a de 4ª classe), por causa do override que fizemos para permitir
   nível até 250. Se quiser levelar o mais rápido possível ATÉ o 99, vale a pena ficar como
   Novice ou 1ª/2ª classe não-trans antes de trocar de profissão.
