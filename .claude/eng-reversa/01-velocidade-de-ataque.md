# Velocidade de ataque (ASPD) — como varia com atributos, classe e arma

> Engenharia reversa do código-fonte (modo **Renewal**, que é o do nosso servidor —
> `RENEWAL_ASPD` definido em `src/config/renewal.hpp:68`).
> Fonte primária: `src/map/status.cpp:2355-2418` (`status_base_amotion_pc`) e
> `src/map/status.cpp:4610-4637` (conversão para `amotion`).

## Resposta curta

**A AGI aumenta a velocidade de ataque de forma QUADRÁTICA, mas com retorno decrescente
por causa de uma raiz quadrada por cima.** Não é linear. Na prática o efeito líquido de
cada ponto de AGI é *sublinear* na faixa alta (cada AGI extra rende menos ASPD que o
anterior), mesmo o termo interno sendo AGI².

## A fórmula (Renewal)

Duas etapas: primeiro calcula-se um valor de ASPD "cru" a partir dos stats, depois
converte-se para o *delay* real entre ataques.

### Etapa 1 — ASPD a partir dos stats

```
Para armas de longo alcance (arco, instrumento, chicote, armas de fogo):
    temp = DEX² / 7 + AGI² / 2

Para todas as outras armas (espadas, adagas, etc):
    temp = DEX² / 5 + AGI² / 2

aspd_stats = √temp × 0.25 + 196
```

(`src/map/status.cpp:2380-2388`)

Depois soma-se o efeito de AGI de novo, agora de forma linear, junto com bônus de
skills/buffs, e subtrai-se a "velocidade base" da combinação classe+arma:

```
aspd = ( aspd_stats + (bônus_skill_buff) × AGI / 200 ) − min(base_arma_classe, 200)
```

(`src/map/status.cpp:2398`)

- `base_arma_classe` = `job->aspd_base[arma]`, vindo de `db/re/job_stats.yml` (campo
  `BaseASPD`). Se a classe não define, usa o default `AMOTION_ZERO_ASPD/10 = 200`
  (`src/map/pc.cpp:13958-13959`). **É por isso que classe e arma importam**: cada classe
  tem uma tabela de "peso" por tipo de arma — uma adaga numa classe ágil tem base baixa
  (rápida), um machado de duas mãos tem base alta (lenta).

### Etapa 2 — conversão para delay real

```
i = 2000 − aspd_stats_convertido × 10          (AMOTION_ZERO_ASPD=2000, AMOTION_INTERVAL=10)
amotion = clamp(i, entre max_aspd/2 e 4000)     (cap pela config max_aspd, default 190)
adelay  = 2 × amotion     ← este é o tempo REAL em milissegundos entre dois ataques
```

(`src/map/status.cpp:4615-4637`, cap em `src/map/battle.cpp:8400` `max_aspd: 190`)

E o número que o client mostra na janela de status:

```
ASPD_exibido = (2000 − amotion) / 10       (vai de 0 a ~193)
```

(`src/map/clif.cpp:4159` envia `amotion`; a divisão por 10 é do lado do client)

## Interpretação: linear ou quadrático?

Tem uma sutileza importante aqui, porque **"ASPD" (o número) e "frequência de ataque"
(ataques por segundo) se comportam de formas OPOSTAS** conforme você sobe AGI:

- O **número de ASPD** (`aspd_stats`) tem o termo `√(AGI²/2 + …) × 0.25`. Como `√(AGI²) = AGI`,
  a raiz "desfaz" o quadrado e o número cresce **quase linear, com leve retorno decrescente**.
- Mas a **frequência real** (ataques/seg) é `1 / adelay`, e `adelay = 2×(2000 − ASPD×10)`.
  Isso é uma relação **inversa**: conforme o ASPD se aproxima do teto, o `adelay` encolhe
  rápido e a frequência **ACELERA** (retorno *crescente*), até bater no cap e parar seco.

> Correção de uma versão anterior deste doc: a frequência **não achata suavemente** perto do
> topo — ela acelera e depois bate numa parede (o cap `max_aspd`). Ver os números abaixo.

**Onde deixa de valer a pena:** não é um ponto suave de "diminishing returns" como eu havia
escrito. É um **teto rígido** (`max_aspd`, default 190 → `adelay` mínimo de 190 ms ≈ 5.26
ataques/seg). Antes do cap, cada ponto de AGI vale *mais* que o anterior para a frequência;
ao atingir o cap, o próximo ponto de AGI vale **exatamente zero**. DEX contribui também, com
peso menor (`DEX²/5` ou `/7` contra `AGI²/2`).

---

## Estudo secundário — quanto de AGI para dobrar / quadruplicar a frequência

Simulação da fórmula exata do código, DEX fixo em 40, sem bônus de skill/buff, comparando uma
arma "leve" e uma "pesada" **do mesmo personagem** (Lord Knight, valores reais de
`db/re/job_aspd.yml`):

### Adaga (BaseASPD 49 — tipo de arma rápido)

| AGI | ataques/seg | × da frequência inicial |
|----:|------------:|------------------------:|
| 1   | 1.03        | 1.00× (base)            |
| 50  | 1.16        | 1.13×                   |
| 100 | 1.44        | 1.40×                   |
| 150 | 1.92        | 1.86×                   |
| 200 | 2.88        | 2.79×                   |
| 255 | 5.26        | 5.11× (no cap)          |

- **Dobrar (2×) a frequência inicial:** ~AGI **161**
- **Quadruplicar (4×):** ~AGI **230** (já bem perto do cap)

### Lança de duas mãos (BaseASPD 60 — tipo de arma lento)

| AGI | ataques/seg | × da frequência inicial |
|----:|------------:|------------------------:|
| 1   | 0.84        | 1.00× (base)            |
| 100 | 1.09        | 1.30×                   |
| 200 | 1.76        | 2.10×                   |
| 255 | 2.67        | 3.18× (nem chega no cap)|

- **Dobrar (2×):** ~AGI **193**
- **Quadruplicar (4×):** **impossível** só com AGI — nem no AGI 255 (cap de stat do nosso
  servidor) a lança pesada chega a 4× a frequência inicial.

Repare no efeito acelerador: para a adaga, ir de AGI 200→255 salta de 2.79× para 5.11× — os
últimos 55 pontos rendem **mais** que os primeiros 150. Isso é o oposto de "diminishing
returns"; é a relação inversa `1/adelay` explodindo perto do cap.

## O peso da arma influencia a velocidade?

**NÃO.** Confirmado no código: a função `status_base_amotion_pc` (`src/map/status.cpp:2355-2418`)
não usa em nenhum lugar o peso (`weight`) da arma — só o **tipo** dela (`BaseASPD[tipo]`).

> Duas armas do **mesmo tipo** (ex: duas 1hSword), uma pesada e uma leve, atacam **exatamente
> na mesma velocidade**. O que muda a velocidade é o *tipo* de arma (adaga vs espada vs
> machado vs lança), não o peso individual. Peso só afeta o quanto você carrega no inventário.

Cada classe tem uma tabela de `BaseASPD` por tipo de arma em `db/re/job_aspd.yml` — é lá que
está o "essa classe é rápida com adaga, lenta com machado".

---

## Resumo das conclusões

1. **AGI é o principal fator de velocidade**, seguido de longe por DEX. A relação é
   `√(AGI²/2)` no número de ASPD, mas na **frequência real** (ataques/seg) o efeito **acelera**
   conforme sobe, por causa da relação inversa `1/adelay`.
2. **Não há "diminishing returns" na frequência** — pelo contrário, cada AGI vale mais que o
   anterior, até bater no **teto rígido** `max_aspd` (default 190 ≈ 5.26 ataques/seg), onde
   AGI extra passa a valer **zero**.
3. **Dobrar a frequência inicial** custa muita AGI: ~161 (arma leve) a ~193 (arma pesada).
   **Quadruplicar** só é viável com arma leve (~AGI 230); com arma pesada é impossível dentro
   do cap de stat 255.
4. **Peso da arma NÃO afeta a velocidade** — só o *tipo* de arma (via `BaseASPD` da classe).
5. Para mudar o teto de velocidade, ajuste `max_aspd` em `conf/import/battle_conf.txt`
   (lembrando: recalculado só no **restart do map-server**, não no `@reloadbattleconf`).
