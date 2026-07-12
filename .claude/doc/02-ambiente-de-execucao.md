# rAthena — Ambiente de execução (análise para jogo local/solo)

> Contexto: máquina Windows com WSL2 (Ubuntu 26.04), repo já em `~/projetos/...` (filesystem Linux).
> Objetivo do usuário: **jogar localmente** e **editar regras do jogo**, sem preocupação com
> servidor público/multiplayer.

## Fato que domina toda a decisão: o cliente é Windows

O que este repo fornece é só o **servidor**. Para jogar é preciso um **cliente de Ragnarok**
(um `.exe` Windows com DirectX, GRFs de sprites/mapas — tipicamente o cliente kRO + um pacote
de tradução, ou um "cliente completo" pré-configurado da comunidade rAthena). Esse cliente:

- **Roda no Windows** (nativo). Não faz sentido em WSL/Docker (é jogo com GPU).
- Precisa apontar para o IP do servidor via `clientinfo.xml`/`sclientinfo.xml` dentro do GRF/pasta.
- Precisa ter **a data (packetver) compatível** com o `PACKETVER` compilado no servidor
  (padrão atual do repo: `20211103` — clientes ≥ ~2018 também exigem o `web-server` ativo).

Ou seja: a arquitetura final é sempre **cliente no Windows + servidor em algum lugar acessível
via TCP** (6900/6121/5121 e 8888). A pergunta real é só *onde rodar servidor + banco*.

## Opção A (recomendada): servidor compilado no WSL2 + MariaDB no WSL2

Compilar nativo no Ubuntu (`./configure && make server`) e rodar `./athena-start start`,
com MariaDB instalado via `apt` (ou num container Docker só para o banco).

**Prós**
- O repo já está no filesystem do Linux → build e git rápidos; toolchain gcc/make é o caminho
  oficial e mais simples (no Windows seria Visual Studio).
- Ciclo de edição excelente: editar `conf/`/`db/`/`npc/` e usar `@reload...` in-game; mudanças
  em `src/` são um `make server` (incremental) e restart.
- WSL2 encaminha `localhost` do Windows para o WSL automaticamente (NAT localhost forwarding):
  o cliente Windows conecta em `127.0.0.1:6900` sem configuração extra. (Se falhar, ativar
  `networkingMode=mirrored` no `.wslconfig` ou usar o IP do WSL.)
- Debug fácil com gdb/valgrind.

**Contras**
- Instalar/gerenciar MariaDB no Ubuntu (mitigável: rodar **só o banco** em Docker, 1 comando).
- WSL precisa estar de pé para jogar (irrelevante na prática — o terminal já fica aberto).

## Opção B: tudo em Docker via `tools/docker/docker-compose.yml` (já vem pronto)

O repo traz um compose com 5 serviços: `db` (MariaDB, importa `sql-files/` no primeiro boot),
`builder` (Alpine com gcc para compilar), e `login`/`char`/`map` rodando os binários, com o repo
montado como volume e portas 3306/6900/6121/5121 expostas ao host.

**O que RODA bem em Docker:** os 4 daemons do servidor, o MariaDB, a compilação (builder), os
tools de conversão. Tudo que é lado-servidor.

**O que NÃO roda em Docker:** o **cliente do jogo** (GUI Windows/DirectX) — sempre fora; e o
próprio Docker Desktop/engine, que no fundo roda *dentro* do WSL2 de qualquer forma.

**Prós**
- Zero setup de banco: `docker-compose up -d` cria MariaDB já com schema importado e os
  três servidores conectados (configs de conexão injetadas via `tools/docker/asset/*.txt`).
- Ambiente descartável (`docker-compose down --volumes` zera tudo).

**Contras**
- O compose **não inclui o `web-server`** (necessário para clientes novos ≥ ~2018) — seria
  preciso adicionar o serviço à mão.
- Camada extra para o ciclo de edição: recompilar = entrar no builder; binário é linkado em
  Alpine/musl (não roda fora do container). Logs/console espalhados em 3 containers
  (o console do map-server é útil para ver erros de script).
- O README do próprio rAthena marca esse Docker como "dev only, não para produção".
- Nota: como Docker Desktop usa WSL2, isso **não é uma alternativa ao WSL** — é WSL com mais camadas.

Bom uso híbrido: **usar só o serviço `db` do compose** (MariaDB descartável) e rodar os
servidores nativos no WSL (Opção A).

## Opção C: nativo no Windows (Visual Studio + rAthena.sln)

Caminho oficial para Windows: compilar com VS 2017+ e instalar MySQL/MariaDB no Windows.

**Prós:** servidor e cliente na mesma rede trivialmente (`127.0.0.1` puro); é o método da
maioria dos tutoriais da comunidade.
**Contras:** exige Visual Studio (instalação grande); o repo teria que ser clonado no filesystem
do Windows (o atual está em `~` do WSL — acessá-lo via `\\wsl$` para build do VS é lento e
problemático); ciclo de recompilação e tooling (rg, scripts, git) pior que no Linux para quem
já trabalha no WSL. **Não recomendado** dado o setup atual do usuário.

## E o XAMPP?

XAMPP = Apache + MariaDB + PHP. Ele **não roda o rAthena** — a comparação "Docker vs XAMPP"
na prática é só sobre **onde fica o MySQL/MariaDB**:

- XAMPP serviria apenas como um jeito fácil de ter MariaDB (+ phpMyAdmin) no Windows.
  O servidor no WSL conectaria nele via IP do host.
- O Apache/PHP do XAMPP só teriam utilidade se um dia você quiser o **FluxCP** (painel web em
  PHP para criar contas/administrar — projeto separado, github.com/rathena/FluxCP). Para jogar
  sozinho é desnecessário: conta dá para criar com sufixo `_M`/`_F` no login (se habilitado em
  `login_athena.conf`) ou por INSERT/SQL direto.
- Veredito: **XAMPP não vale a pena aqui.** MariaDB via `apt` no Ubuntu ou container Docker é
  mais limpo, e phpMyAdmin é substituível por DBeaver/CLI.

## Recomendação final

| Componente | Onde rodar |
|---|---|
| login/char/map/web-server | **WSL2, compilado nativo** (`./configure && make server`) |
| MariaDB | WSL2 via `apt` **ou** container Docker (só o `db` do compose) |
| Cliente RO | **Windows**, apontando `clientinfo.xml` para `127.0.0.1` |
| XAMPP / FluxCP | Não usar (só se quiser painel web no futuro) |

### Passos macro para "conseguir jogar" (roteiro)

1. **Servidor:** instalar deps (`build-essential zlib1g-dev libmariadb-dev`), `./configure`,
   `make server`.
2. **Banco:** MariaDB up; criar DB `ragnarok` + usuário; importar `sql-files/main.sql`,
   `logs.sql` e `web.sql`.
3. **Config:** criar `conf/import/` a partir de `conf/import-tmpl/` com credenciais do banco
   (`inter_conf.txt`), userid/senha interservidor (`char_conf.txt`/`map_conf.txt`) e
   `login_conf.txt` (ex.: `new_account: yes` para criar conta com `_M`).
4. **Cliente:** baixar um cliente compatível com packetver `20211103` (ou recompilar o servidor
   com `--enable-packetver=` da data do seu exe); editar `clientinfo.xml` → `127.0.0.1`.
5. `./athena-start start` no WSL, abrir o cliente no Windows, logar.
6. **Editar regras:** `conf/import/battle_conf.txt` (rates), `db/import/` (itens/mobs),
   `npc/custom/` (NPCs) — ver doc 01, seção "Onde mexer".
