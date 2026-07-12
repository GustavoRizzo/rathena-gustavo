# rAthena — Melhorando a experiência (single-player)

> Registrado em 2026-07-12, depois do servidor rodando com o client FROSTUBE (ver doc 04).
> Aqui ficam os atalhos de produtividade (Makefile de dev) e os comandos in-game úteis agora
> que toda conta já nasce **Admin** (`group_id 99`, ver doc 04) — ou seja, todos os comandos
> `@` abaixo já funcionam sem precisar de setup extra.

## Atalhos via `tools/docker/dev.mk`

Arquivo separado do `Makefile` de build do rAthena (esse fica na raiz e é gerado pelo
`./configure`, não mexer nele). Uso sempre com `-f`:

```bash
cd /home/grizzo/projetos/terceiros/rathena   # ou onde estiver o repo

# Criar um personagem novo direto no banco (pula a tela de criação do client)
make -f tools/docker/dev.mk new-char NAME=Foo SLOT=1

# Resetar a posição de TODOS os personagens (de todas as contas) para um ponto seguro
make -f tools/docker/dev.mk reset-positions
# customizando o destino:
make -f tools/docker/dev.mk reset-positions MAP=geffen X=120 Y=65

# Listar personagens existentes (útil pra achar char_id e slots livres)
make -f tools/docker/dev.mk list-chars
```

`reset-positions` é o comando pra usar sempre que o personagem ficar "preso" perto de algo que
crasha o client (ver problema conhecido no doc 04) — muda `last_map`/`save_map` no banco sem
precisar do jogo aberto.

Parâmetros aceitos por `new-char`: `NAME`, `SLOT` (0-8), `ACCOUNT_ID` (default `2000000` =
`gustavo`), `MAP`/`X`/`Y` (default `prontera 155,185`).

## Comandos `@` mais úteis para jogo solo

Todos digitados no chat do jogo. Como sua conta é Admin, todos funcionam de cara.

### Taxas de XP e drop (via conf, não comando)

Rates não são `@command`, ficam em `conf/import/battle_conf.txt` (criar se não existir) e
recarregam com `@reloadbattleconf` sem precisar reiniciar o map-server:

```
// 10x experiência
base_exp_rate: 1000
job_exp_rate: 1000

// 5x chance de drop (itens comuns, equipamentos, cards, MVP)
item_rate_common: 500
item_rate_equip: 500
item_rate_card: 500
item_rate_mvp: 500
```

Valores são em porcentagem: `100` = taxa normal (1x), `1000` = 10x. Os defaults atuais (todos
`100`) estão em `conf/battle/exp.conf` e `conf/battle/drops.conf` — **não editar esses
diretamente**, sempre via `conf/import/battle_conf.txt`.

### Teleporte

```
@go prontera              # lista de cidades pré-definidas (@go sem argumento mostra a lista)
@go 0                     # também aceita o índice numérico
@warp prontera 155 185    # qualquer mapa, com coordenada exata
@jump                     # teleporte aleatório dentro do mapa atual
@jump 150 200             # teleporte pra coordenada específica no mapa atual
@jumpto NomeDoPersonagem  # teleporta até outro personagem (útil sozinho só se tiver 2 chars logados)
```

### Gerar itens no inventário

```
@item Red_Potion 50           # por nome (aceita nome interno do item db)
@item 501 50                  # por ID numérico
@item2 1201 1 1 7 0 0 0 0     # item com refino/atributo/cards específicos (arma +7, ex: Knife)
@itemreset                    # limpa todo o inventário (cuidado, é destrutivo)
```

Nome/ID dos itens: `db/re/item_db.yml` (ou `db/import/item_db.yml` para custom). `@iteminfo
<nome>` mostra ID e detalhes de um item sem precisar abrir o YAML.

### Trocar de classe / profissão

```
@jobchange Swordsman     # por nome
@jobchange 4001           # por ID de job
@jobchange 4001 1         # com upper=1 (classe avançada/trans, se aplicável)
```

Isso é redundante agora com a mudança que fizemos no `char.cpp` (client já deixa escolher
classe na criação — ver doc 04), mas é a forma padrão de trocar depois de já ter o personagem
criado. Alternativa in-game sem comando: o NPC `npc/custom/jobmaster.txt` já existe pronto no
repo, só falta descomentar a linha dele em `npc/scripts_custom.conf` (ver apêndice do doc 03).

### Outros úteis para testar mecânicas rápido

```
@heal 9999 9999      # cura HP/SP totais
@allskill             # aprende todas as skills da build atual (útil pra testar builds)
@stpoint 100           # adiciona pontos de status pra distribuir
@skpoint 100           # adiciona pontos de skill
@speed 0                # velocidade de movimento máxima (0 = mais rápido)
@zeny 1000000            # adiciona zeny
@refine <posição> <+n>  # refina um equipamento já equipado
@produce <item> <elem> <very>  # forja arma com atributo elemental
@hide                    # fica invisível (útil pra observar mobs/NPCs sem interagir)
```

Lista completa em `doc/atcommands.txt` na raiz do repo — vale grepar lá antes de perguntar,
é o catálogo oficial de todos os comandos com a sintaxe exata.

## Fluxo recomendado pra testar algo novo

1. Se for número/regra (rate, drop, etc.) → `conf/import/battle_conf.txt` + `@reloadbattleconf`.
2. Se for item/mob/skill/job → `db/import/*.yml` + `@reloaditemdb`/`@reloadmobdb`/restart do map.
3. Se for posição/estado de personagem específico → direto no banco via `dev.mk` ou SQL manual
   (mais rápido que reconstruir estado via comandos in-game toda vez).
4. Se for NPC/quest → `npc/custom/` + `scripts_custom.conf` + `@reloadscript`.
