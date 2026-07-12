# rAthena — Passo a passo: servidor em Docker + cliente no Windows

> Decisão registrada em 2026-07-12: **tudo que for possível roda em Docker** (banco, build e os
> 4 servidores); **só o cliente do jogo roda no Windows** (é um .exe DirectX, não containerizável).
> Este documento é o roteiro completo, na ordem de execução. Nada daqui foi executado ainda.

## Visão geral do que vamos montar

```
┌─ Windows ────────────────┐      ┌─ WSL2 / Docker ──────────────────────────────┐
│  Cliente RO (ragexe)     │ TCP  │ rathena-login  :6900 ─┐                      │
│  clientinfo.xml →        ├─────►│ rathena-char   :6121 ─┼─► rathena-db :3306   │
│  127.0.0.1               │      │ rathena-map    :5121 ─┤   (MariaDB)          │
└──────────────────────────┘      │ rathena-web    :8888 ─┘   volume: rathenadb  │
                                  │ rathena-builder (compila os binários)        │
                                  └──────────────────────────────────────────────┘
```

A base é o `tools/docker/docker-compose.yml` que já vem no repo (serviços `db`, `builder`,
`login`, `char`, `map`). Ele **não inclui o `web-server`** — clientes 2021 usam ele para
emblemas de guild, party booking e configs do usuário — então vamos adicioná-lo via
`docker-compose.override.yml` (arquivo novo, não conflita com o upstream).

Pontos que o compose já resolve sozinho (verificado nos arquivos):

- O MariaDB importa **todos os `sql-files/*.sql`** automaticamente no primeiro boot
  (`main.sql`, `logs.sql`, `web.sql`, item/mob dbs) no banco `ragnarok` (user/senha `ragnarok`).
- Os arquivos `tools/docker/asset/*.txt` são montados sobre `conf/import/` nos containers e já
  apontam o SQL para o host `db` e — importante — já anunciam `char_ip: 127.0.0.1` e
  `map_ip: 127.0.0.1` ao cliente, ou seja, **já está configurado para cliente local no Windows**.
- O `builder.sh` compila sozinho na primeira subida (roda `./configure --enable-packetver=20211103
  && make clean server` se os binários não existirem).
- O repo inteiro é montado como volume nos containers → **editar arquivos no WSL reflete
  imediatamente dentro dos containers**, sem rebuild de imagem.

---

## Fase 1 — Pré-requisitos (uma vez só)

1. **Docker funcionando no WSL** — Docker Desktop com integração WSL2 habilitada para a distro
   Ubuntu-26.04, **ou** docker-ce instalado direto no WSL. Testar: `docker info` e
   `docker compose version`.
2. **Porta 3306 livre no host** (sem MySQL/MariaDB local rodando). Também 6900, 6121, 5121, 8888.
3. Confirmar que o repo está no filesystem Linux (está: `~/projetos/terceiros/rathena`) —
   bind mount de `/mnt/c` seria lento.

## Fase 2 — Configurações antes de subir (arquivos a criar/editar)

Tudo nesta fase é edição de arquivo no WSL, nenhum container ainda.

### 2.1 Permitir criação de conta pelo cliente (`_M/_F`)

O padrão do rAthena é `new_account: no`. Criar o arquivo **`conf/import/login_conf.txt`**:

```
new_account: yes
```

(O compose monta os assets sobre `inter/char/map_conf.txt` de `conf/import/`, mas o diretório
`conf/import/` vem do bind mount do repo — este arquivo novo será lido normalmente.)

Com isso, na tela de login do cliente, logar como `meuusuario_M` cria a conta masculina
(`_F` = feminina) com a senha digitada. Depois do primeiro login o sufixo não é mais usado.

### 2.2 Conexão do web-server ao banco

O web-server lê a conexão SQL do `inter_athena.conf` (chaves `web_server_ip/port/id/pw/db`),
que dentro do container padrão apontaria para `127.0.0.1`. Adicionar ao arquivo
**`tools/docker/asset/inter_conf.txt`** (é o que vira `conf/import/inter_conf.txt` nos
containers) as linhas:

```
web_server_ip: db
web_server_port: 3306
web_server_id: ragnarok
web_server_pw: ragnarok
web_server_db: ragnarok
```

### 2.3 Adicionar o serviço web ao compose

Criar **`tools/docker/docker-compose.override.yml`** (o Docker Compose mescla automaticamente
com o `docker-compose.yml`):

```yaml
services:
    web:
        image: "rathena:local"
        container_name: "rathena-web"
        command: sh -c "/bin/wait-for db:3306 -- /rathena/web-server"
        ports:
            - "8888:8888"
        volumes:
            - "../..:/rathena"
            - "./asset/inter_conf.txt:/rathena/conf/import/inter_conf.txt"
        init: true
        tty: true
        stdin_open: true
        depends_on:
            - char
```

*(O `make server` já gera o binário `web-server` junto com os outros três.)*

## Fase 3 — Subir o servidor (ordem dos comandos)

Todos os comandos a partir de **`tools/docker/`** (o compose usa caminhos relativos):

```bash
cd tools/docker

# 1. Construir a imagem base (Alpine + gcc + mariadb-dev). Rápido, ~1x só.
docker compose build

# 2. Subir SÓ o banco primeiro e deixar ele importar os sql-files (primeiro boot demora ~1 min).
docker compose up -d db
docker compose logs -f db        # esperar "ready for connections"; Ctrl+C sai do log

# 3. Compilar o rAthena dentro do builder (primeira vez: ./configure + make, ~5–15 min).
docker compose up -d builder
docker compose logs -f builder   # esperar o make terminar sem erros

# 4. Subir os servidores (a ordem/depends_on já encadeia login → char → map → web).
docker compose up -d login char map web

# 5. Conferir
docker compose ps                # todos "Up"
docker compose logs -f map       # esperar algo como "Server is now online" / NPCs carregados
```

Diagnóstico rápido se algo falhar: `docker compose logs login|char|map|web`. Erros clássicos:
porta 3306 ocupada (parar MySQL local) ou binário inexistente (builder ainda compilando —
subir login/char/map só depois do passo 3 terminar).

### Ciclo de vida no dia a dia

```bash
docker compose up -d      # liga tudo (não recompila se binários existem)
docker compose down       # desliga (banco persiste no volume rathenadb)
docker compose down --volumes   # ⚠️ APAGA o banco (contas/chars) e recomeça do zero
```

## Fase 4 — Cliente no Windows

O servidor foi compilado com **`PACKETVER 20211103`** (fixado no compose via
`BUILDER_CONFIGURE`). O cliente precisa ser um executável **dessa mesma data** (2021-11-03).

1. **Baixar o cliente base (kRO)** — o jogo completo com sprites/mapas (~3–4 GB). Fontes usuais:
   a seção *Client Releases / Client Packs* do fórum rathena.org, que distribui "full clients"
   já com tradução em inglês. Procurar um pack anunciado como compatível com
   **packetver 2021-11-03**. Instalar em algo como `C:\ro-local\` (fora de Program Files,
   para evitar problemas de permissão).
2. **Executável (ragexe) "diffado"** — o .exe original é travado nos servidores oficiais; usa-se
   um exe patchado com WARP/NEMO. Os client packs do fórum já vêm com o exe pronto
   (patches típicos: *Read Data Folder First*, *Disable HShield*, *Use sclientinfo.xml*,
   *Enable DNS support* etc.). Se o pack já traz, não há o que fazer aqui.
3. **Apontar para o servidor local** — editar `data/sclientinfo.xml` (clientes novos; ou
   `clientinfo.xml` em packs antigos), dentro da pasta `data/` do cliente:

   ```xml
   <?xml version="1.0" encoding="euc-kr" ?>
   <clientinfo>
     <servicetype>korea</servicetype>
     <servertype>primary</servertype>
     <connection>
       <display>Servidor Local</display>
       <address>127.0.0.1</address>
       <port>6900</port>
       <version>55</version>
       <langtype>1</langtype>
       <registrationweb>http://127.0.0.1</registrationweb>
       <yellow><admin>2000000</admin></yellow>
     </connection>
   </clientinfo>
   ```

   O que importa: `address 127.0.0.1`, `port 6900`, `langtype 1` (inglês). Docker Desktop
   publica as portas no localhost do Windows; com docker-ce dentro do WSL, o localhost
   forwarding do WSL2 cobre (se não conectar, testar o IP do WSL: `wsl hostname -I`).
4. **Criar a conta e logar** — abrir o exe do cliente, logar como `SEUNOME_M` + senha →
   conta criada (Fase 2.1). Criar personagem e entrar. **Está jogando.**

### Virar GM (necessário para os comandos `@` usados no apêndice)

Com a conta já criada, no WSL:

```bash
docker exec -it rathena-db mariadb -uragnarok -pragnarok ragnarok \
  -e "UPDATE login SET group_id = 99 WHERE userid = 'SEUNOME';"
```

Relogar no jogo. `group_id 99` = Super Admin (`conf/groups.yml`); libera `@go`, `@item`,
`@blvl`, `@reload...` etc.

---

## Apêndice — Mods (depois que o jogo vanilla estiver rodando)

Regra geral: **nunca editar os arquivos originais** — usar `conf/import/`, `db/import/` e
`npc/custom/` (ver doc 01). Como o repo é bind mount, editar no WSL + recarregar in-game já
aplica; recompilar só quando mexer em `src/`.

### A) Aumentar taxa de experiência

Criar/editar **`conf/import/battle_conf.txt`** (valores em %, 100 = 1x):

```
// 10x de experiência
base_exp_rate: 1000
job_exp_rate: 1000
```

Aplicar: in-game `@reloadbattleconf`, ou `docker compose restart map`.
(Taxas de drop ficam no mesmo arquivo: `item_rate_common`, `item_rate_equip`, `item_rate_card`
etc. — referência de nomes em `conf/battle/exp.conf` e `conf/battle/drops.conf`.)

### B) Aumentar o limite de level

Três camadas, da mais fácil à mais profunda:

1. **Teto por classe** — o cap de cada job (Renewal: 4ᵃˢ classes vão a 260, outras menos) vem de
   `db/re/job_stats.yml` (`MaxBaseLevel`/`MaxJobLevel`). Override em
   **`db/import/job_stats.yml`**, ex.:

   ```yaml
   Header:
     Type: JOB_STATS
     Version: 3
   Body:
     - Jobs:
         All: true
       MaxBaseLevel: 275
   ```

2. **Tabela de EXP** — subir o cap exige que exista EXP definida para os novos níveis:
   estender em **`db/import/job_exp.yml`** (formato em `db/re/job_exp.yml`).
3. **Hard cap do código** — `MAX_LEVEL 275` em `src/map/map.hpp:78`. Até 275 **não precisa
   recompilar**; acima disso, alterar o define e rodar `make clean server` no builder
   (`docker compose run --rm builder /rathena/tools/docker/builder.sh` após apagar os binários,
   ou entrar no builder e rodar `make server`).

Aplicar (casos 1–2): `@reloaditemdb`/`@reloadmobdb` não cobrem job db — reiniciar o map:
`docker compose restart map`.

### C) NPC de troca de profissão (Job Master)

Já existe pronto: **`npc/custom/jobmaster.txt`** (troca para qualquer classe, incluindo 4ᵃˢ,
com checagem de nível, opção de dar equipamento inicial e skills platinum). Ativar
descomentando a linha 11 de **`npc/scripts_custom.conf`**:

```
npc: npc/custom/jobmaster.txt
```

Aplicar: `docker compose restart map` (ou in-game `@reloadscript`). O NPC aparece em
**Prontera (153,193)** — `@go prontera` para chegar lá. Outros prontos no mesmo diretório que
valem ativar para jogo solo: `healer.txt` (cura grátis), `warper.txt` (teleporte para qualquer
mapa/dungeon), `stylist.txt`, `resetnpc.txt` (reset de stats/skills).

Para trocar de profissão **automaticamente ao atingir o nível** (sem falar com NPC), aí é um
script custom próprio usando o evento `OnPCBaseLvUpEvent` + `jobchange` — escrever em
`npc/custom/` e registrar em `scripts_custom.conf` (referência: `doc/script_commands.txt`).

### Checklist mental para qualquer mod futuro

1. É regra/número? → `conf/import/battle_conf.txt` → `@reloadbattleconf`.
2. É dado de item/mob/skill/job? → `db/import/*.yml` → `@reload...` ou restart do map.
3. É NPC/quest/evento? → `npc/custom/` + `scripts_custom.conf` → `@reloadscript`.
4. É mecânica core/limite de engine? → `src/` → recompilar no builder + restart.
