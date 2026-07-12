# CLAUDE.md — rAthena (fork local)

## Contexto deste fork

Emulador de servidor de Ragnarok Online em C++ (upstream: github.com/rathena/rathena).
**Objetivo do dono do repo:** jogar localmente (single-player) e customizar regras do jogo —
NÃO é um servidor público/produção. Prioridade: ciclo de edição rápido, não escalabilidade.

Documentação de estudo deste repo (ler antes de mudanças grandes):
- `.claude/doc/01-estrutura-do-projeto.md` — o que é cada pasta, onde mexer para cada edição.
- `.claude/doc/02-ambiente-de-execucao.md` — análise das opções de ambiente.
- `.claude/doc/03-passo-a-passo-docker.md` — **decisão vigente**: servidor todo em Docker
  (compose de `tools/docker/` + override com web-server), cliente no Windows. Roteiro completo
  de subida + apêndice de mods.

## Arquitetura em 1 parágrafo

Quatro daemons + MySQL/MariaDB: `login-server` (6900) → `char-server` (6121) → `map-server`
(5121, o jogo em si) + `web-server` (8888, exigido por clientes novos). Dados do jogo em YAML
(`db/`), mundo em scripts próprios (`npc/`), regras de runtime em `conf/`. Cliente do jogo é
externo (Windows) e deve ter packetver compatível com `src/config/packets.hpp` (hoje `20211103`).

## Build e execução (Docker — caminho adotado)

Tudo via Docker Compose a partir de `tools/docker/` (detalhes e ordem exata no doc 03):

```bash
cd tools/docker
docker compose build              # imagem Alpine com toolchain
docker compose up -d db           # MariaDB; importa sql-files/ no 1º boot
docker compose up -d builder      # compila (configure --enable-packetver=20211103 + make)
docker compose up -d login char map web   # web vem do docker-compose.override.yml (não versionado no upstream)
```

- O repo é bind mount nos containers: editar conf/db/npc no WSL reflete na hora; só `src/`
  exige recompilar no builder.
- Banco: user/senha/db `ragnarok`, host `db` (containers) ou `localhost:3306` (host).
- `docker compose down --volumes` APAGA o banco (contas/personagens) — não usar sem confirmar.
- Cliente do jogo roda no Windows apontando para `127.0.0.1` (não é parte deste repo).

## Convenções OBRIGATÓRIAS para customização

O rAthena tem mecanismo de override para não conflitar com `git pull` do upstream. **Sempre**
preferir estes pontos de extensão em vez de editar arquivos originais:

- Regras/config → `conf/import/` (templates em `conf/import-tmpl/`); nunca editar
  `conf/*.conf` ou `conf/battle/*.conf` diretamente.
- Dados (itens, mobs, skills...) → `db/import/*.yml`; nunca editar `db/re/`, `db/pre-re/`
  ou raiz de `db/` diretamente.
- NPCs/quests custom → `npc/custom/` + registrar em `npc/scripts_custom.conf`.
- Código-fonte: preferir os hooks de `src/custom/` (`.inc` para @commands e script commands);
  mudanças de mecânica core vão em `src/map/` (aí sim editando o core, inevitável).
- `conf/import/` e `db/import/` podem não existir ainda (só os `-tmpl`); criar quando necessário.

Recarga sem recompilar: mudanças em conf/db/npc aplicam com restart do map-server ou in-game
via `@reloadbattleconf`, `@reloaditemdb`, `@reloadmobdb`, `@reloadscript`/`@loadnpc`.
Mudanças em `src/` exigem `make server` + restart.

## Referências internas essenciais

- `doc/script_commands.txt` — linguagem de script de NPC (consultar antes de escrever NPC).
- `doc/item_bonus.txt` — bônus de itens; `doc/atcommands.txt` — comandos `@`.
- Renewal vs pre-Renewal: `src/config/renewal.hpp` decide o modo; dados correspondentes em
  `db/re|pre-re` e `npc/re|pre-re`. O repo está em modo **Renewal** (padrão).

## Estilo de código (ao mexer em src/)

- C++ moderno mas conservador; seguir o estilo do arquivo vizinho (tabs, chaves, nomes
  `snake_case`, structs/enums do padrão rAthena como `map_session_data`, `e_*` enums).
- Comentários e identificadores em inglês (padrão do upstream), mesmo que a conversa seja em PT-BR.
- Commits pequenos; não commitar `conf/import/` com senhas de banco.
