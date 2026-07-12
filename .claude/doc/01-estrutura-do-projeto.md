# rAthena — Estrutura do projeto

> Documento gerado em 2026-07-12 a partir da exploração do repositório.

## O que é este projeto

O **rAthena** é um *emulador de servidor* do MMORPG **Ragnarok Online** (continuação do
projeto eAthena), escrito em C++. Ele implementa o lado servidor do jogo: contas, personagens,
mapas, monstros, NPCs, skills, itens, guildas etc.

**Importante:** o repositório contém **apenas o servidor**. O **cliente do jogo** (o executável
Windows com os gráficos, sprites e mapas) **não faz parte** deste projeto — é preciso obter um
cliente RO à parte (ver doc de ambiente de execução).

## Arquitetura: os 4 servidores

O rAthena compila em daemons separados que conversam entre si e com um banco MySQL/MariaDB:

| Binário | Porta padrão | Função |
|---|---|---|
| `login-server` | 6900 | Autenticação de contas. É onde o cliente conecta primeiro. |
| `char-server` | 6121 | Seleção/criação de personagens; ponte entre login e map. |
| `map-server` | 5121 | O jogo em si: mapas, combate, NPCs, skills, drops. É o processo "pesado". |
| `web-server` | 8888 | Servidor HTTP opcional, exigido por clientes mais novos (emblemas de guild, party booking, configurações do usuário na nuvem). |

Fluxo do cliente: `cliente → login (6900) → char (6121) → map (5121)`. O login-server devolve
ao cliente o IP do char-server, e o char devolve o IP do map — por isso a configuração de IP/subnet
importa mesmo jogando sozinho em localhost (`conf/subnet_athena.conf` trata o caso local).

Todos dependem de um **MySQL/MariaDB** com o schema criado a partir de `sql-files/`.

## Mapa de diretórios

```
rathena/
├── src/          Código-fonte C++ dos servidores
├── conf/         Configuração de RUNTIME (regras do jogo, portas, rates)
├── db/           Dados do jogo em YAML (itens, mobs, skills, jobs...)
├── npc/          Scripts do mundo (NPCs, quests, warps, spawns) em linguagem própria
├── sql-files/    Schemas e dados SQL do banco
├── doc/          Documentação oficial (a "bíblia" do scripting está aqui)
├── tools/        Utilitários: docker, conversores, .bat para Windows
├── 3rdparty/     Bibliotecas embutidas (yaml-cpp, httplib, pcre, zlib...)
├── configure     Build autotools (Linux)
├── CMakeLists.txt  Build CMake (alternativa)
└── rAthena.sln   Solution do Visual Studio (build Windows)
```

### `src/` — código-fonte

- `src/login/`, `src/char/`, `src/map/`, `src/web/` — um diretório por servidor.
  `src/map/` é de longe o maior (combate em `battle.cpp`, skills em `skill.cpp` + `src/map/skills/`,
  protocolo cliente em `clif.cpp`, comandos `@` em `atcommand.cpp`, interpretador de script em `script.cpp`).
- `src/common/` — código compartilhado (rede, SQL, timers, leitura de YAML).
- `src/config/` — **configuração em tempo de COMPILAÇÃO** (headers):
  - `renewal.hpp` — liga/desliga o modo **Renewal** (`#define RENEWAL`). Comentar = pre-Renewal
    (ou usar `./configure --enable-prere`).
  - `packets.hpp` — **`PACKETVER`** (padrão atual: `20211103`): a data da versão do cliente
    suportado. **Tem que ser compatível com o .exe do cliente que você for usar.**
  - `secure.hpp`, `core.hpp`, `classes/` — outras opções de source.
- `src/custom/` — ponto de extensão oficial: arquivos `.inc` para adicionar comandos `@`,
  comandos de script e defines **sem tocar no core** (facilita atualizar o repo depois).
- `src/tool/` — utilitários compilados: `csv2yaml`, `yaml2sql`, `yamlupgrade`, `mapcache`.

### `conf/` — configuração de runtime (⭐ regras do jogo editáveis sem recompilar)

- `login_athena.conf`, `char_athena.conf`, `map_athena.conf`, `web_athena.conf` — config de cada
  servidor (portas, IPs, nome do servidor, credenciais interservidor).
- `inter_athena.conf` — conexão com o MySQL (host, usuário, senha, nomes dos bancos).
- `conf/battle/` — **as regras de gameplay**: `exp.conf` (rates de experiência), `drops.conf`
  (taxa de drop), `party.conf`, `guild.conf`, `skill.conf`, `pet.conf`, `feature.conf` (liga/desliga
  features) etc. É o primeiro lugar para "mexer nas regras".
- `groups.yml` / `atcommands.yml` — permissões e comandos `@` (ex.: dar conta GM nível 99).
- `maps_athena.conf` — lista de mapas carregados; `subnet_athena.conf` — resolução de IP local.
- **`conf/import/`** (criado a partir de `conf/import-tmpl/`) — **mecanismo de override**: qualquer
  configuração colocada aqui sobrescreve a padrão e **não gera conflito no `git pull`**.
  Regra de ouro: *não editar os .conf originais; colocar só as diferenças em `conf/import/`*.

### `db/` — dados do jogo (YAML)

- `db/re/` — dados do modo **Renewal** (mecânica atual do RO oficial).
- `db/pre-re/` — dados **pre-Renewal** (mecânica clássica, pré-2010).
- Raiz de `db/` — dados comuns aos dois modos.
- Principais bases: `item_db.yml`, `mob_db.yml`, `skill_db.yml`, `job_stats.yml`, `exp_*.yml`,
  `item_group_db.yml` (o que sai de caixas/presentes), `mob_skill_db.yml`.
- **`db/import/`** (a partir de `db/import-tmpl/`) — mesmo mecanismo de override do conf: itens
  custom, mudanças em mobs etc. vão aqui, não nos arquivos originais.
- `map_cache.dat` / `map_index.txt` — geometria/índice dos mapas usados pelo map-server.

### `npc/` — o mundo do jogo

Scripts na linguagem própria do rAthena (documentada em `doc/script_commands.txt`):

- `cities/`, `quests/`, `merchants/`, `warps/`, `mobs/`, `guild/`, `instances/`, `events/`, `jobs/`, `kafras/`...
- `npc/re/` e `npc/pre-re/` — conteúdo específico de cada modo.
- **`npc/custom/`** — seus NPCs customizados (healer, warper, etc. — já vêm exemplos prontos).
- `scripts_athena.conf`, `scripts_custom.conf`, etc. — listas de quais arquivos o map-server carrega
  (formato `npc: caminho/arquivo.txt`). Para ativar um NPC custom, adicione a linha em
  `scripts_custom.conf`.

### `sql-files/` — banco de dados

- `main.sql` — schema principal (contas, personagens, inventário, guildas...). **Obrigatório.**
- `logs.sql` — tabelas de log (obrigatório se logs SQL habilitados). `web.sql` — para o web-server.
- `item_db*.sql` / `mob_db*.sql` — versões SQL das bases YAML (opcional; por padrão lê YAML).
- `upgrades/` — migrações incrementais ao atualizar o repositório.
- `roulette_default_data.sql`, `compatibility/`, `tools/`.

### `doc/` — documentação oficial

Leitura essencial para modificar o jogo:

- `script_commands.txt` — referência completa da linguagem de script de NPC (~11k linhas).
- `item_bonus.txt` — todos os bônus possíveis em itens/equipamentos.
- `atcommands.txt` — comandos `@` de administração in-game.
- `permissions.txt`, `mapflags.txt`, `status_change.txt`, `mob_db.txt`, `item_db.txt` — formatos das bases.
- `packet_client.txt`, `packet_interserv.txt` — protocolo de rede.

### `tools/` e `3rdparty/`

- `tools/docker/` — `Dockerfile` + `docker-compose.yml` para dev local (MariaDB + builder +
  login/char/map em containers). Ver doc de ambiente.
- `*.bat` (`runserver.bat`, `serv.bat`...) — atalhos para rodar no Windows.
- Conversores: `csv2yaml`, `yaml2sql`, `convert_sql.pl`, `navi.py` (navegação), `mapcache.bat`.
- `3rdparty/` — dependências embutidas no build: `yaml-cpp`, `rapidyaml`, `httplib` (web-server),
  `json`, `libconfig`, `pcre`, `zlib`, headers do conector `mysql`.

## Como compilar (resumo)

- **Linux/WSL:** `./configure && make server` → gera `login-server`, `char-server`, `map-server`,
  `web-server` na raiz. Iniciar com `./athena-start start` (ou cada binário à mão).
  Flags úteis do configure: `--enable-packetver=YYYYMMDD`, `--enable-prere`, `--enable-debug`.
- **CMake:** suportado (`CMakeLists.txt`), alternativa ao autotools.
- **Windows:** abrir `rAthena.sln` no Visual Studio 2017+ e compilar.

Dependências de build (Linux): gcc/g++ (C++17+), make, zlib-dev, libmariadb-dev/libmysqlclient-dev.

## Onde mexer para cada tipo de edição

| Quero mudar... | Onde | Precisa recompilar? |
|---|---|---|
| Rates de EXP/drop, regras de party, features | `conf/import/battle_conf.txt` (valores de `conf/battle/*.conf`) | Não (reiniciar map-server; alguns aceitam `@reloadbattleconf`) |
| Stats de item/mob, novas skills em mob | `db/import/*.yml` | Não (`@reloaditemdb`, `@reloadmobdb`) |
| Criar/alterar NPC, quest, evento | `npc/custom/` + `scripts_custom.conf` | Não (`@loadnpc`, `@reloadscript`) |
| Comando `@` novo, fórmula de dano, mecânica core | `src/custom/` ou `src/map/` | **Sim** |
| Renewal ↔ pre-Renewal, PACKETVER | `src/config/renewal.hpp`, `src/config/packets.hpp` | **Sim** |
| Permissões/GM | `conf/import/groups.yml` (base: `conf/groups.yml`) | Não (`@reload` correspondente) |
