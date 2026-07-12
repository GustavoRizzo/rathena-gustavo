# rAthena — Cliente usado e descoberta do packetver

> Registrado em 2026-07-12, depois da primeira subida bem-sucedida do servidor (ver doc 03).
> Este documento existe porque o processo de descobrir o client/packetver certos foi bem mais
> longo e cheio de tentativa-e-erro do que o roteiro original previa. Serve de referência para
> não repetir o mesmo caminho da próxima vez (reset de ambiente, troca de client, etc).

## Cliente em uso

**Localização (Windows):** `C:\entretenimento\r2\Client 2021_FROSTUBE\Client 2020_CLEAN\`

**Executável principal:** `login.exe` (existe também um `login_ANTIGO.exe` idêntico em bytes —
provavelmente backup de quando alguém trocou o exe do pack; pode ignorar).

**⚠️ Disclaimer importante — antes de abrir o `login.exe` pela primeira vez:**
Rode o **`Setup.exe`** (também na raiz da pasta do client) uma vez, antes do primeiro login.
Esse setup configura as informações de placa de vídeo/DirectX do seu PC — sem isso o client
pode não abrir, abrir com renderização quebrada, ou crashar direto na tela de loading. Só
precisa rodar uma vez por instalação do client, não a cada sessão de jogo.

O client é da linhagem **kRO / Ragexe genérica**, montado num pack de terceiros ("FROSTUBE") —
não é o pack "RuneHost 2025" testado inicialmente (esse foi descartado, ver seção abaixo).

Detalhes técnicos identificados por engenharia reversa leve (headers do exe, timestamps,
arquivos internos):
- Login usa **modo SSO** (Single Sign-On / token), não o CA_LOGIN clássico usuário+senha.
  Isso muda como contas são autenticadas no login-server (ver seção de patches abaixo).
- Sistemas presentes nos `.lub` do client (`PetEvolutionCln_true.lub`,
  `PrivateAirplane_True.lub`) confirmam que é **pós-2019**.
- O exe tem seção `.xdiff`, sinal de que já passou por algum patcher tipo Nemo/WARP em algum
  momento da vida dele — não é um Ragexe oficial "puro".
- `#start.bat` na pasta mostra o padrão de inicialização: `login.exe -t:SUASENHA SEULOGIN -1rag1`.

## Client descartado: "RuneHost 2025"

Tentativa inicial usou um client em `C:\entretenimento\ragnarok\Client 2025 RuneHost\`.
**Foi abandonado** porque o exe fechava sozinho logo após a confirmação do UAC do Windows,
sem erro nenhum — sintoma clássico de **GameGuard** (o `GameGuard.des` ainda vinha no pack),
anticheat antigo da Gravity que é extremamente incompatível com Windows 10/11 modernos.
Não vale a pena tentar reaproveitar esse pack sem antes remover/neutralizar o GameGuard
(e mesmo assim não há garantia — o pack nunca chegou a autenticar no login-server).

## A saga do packetver: como chegamos em `20200902`

O `docker-compose.yml` original do repo já vinha com `--enable-packetver=20211103` fixado
(decisão de quem montou esse setup, não documentada). Isso não bateu com nenhum dos clients
testados. Linha do tempo:

1. **`20211103`** (valor original do repo) + client RuneHost 2025 → nunca chegou a testar
   packetver de fato, o client morria antes por causa do GameGuard.
2. **`20231101`** (chute baseado numa data-string `"Wed Nov 1 10:04:03 2023"` encontrada dentro
   do exe do RuneHost 2025) → mesmo problema do GameGuard, chute nunca foi validado.
3. Trocamos para o client FROSTUBE. Voltamos para **`20211103`** (valor original) só por
   já estar configurado → o login-server rejeitou com `Received unknown packet 0x4547`
   (packet SSO não reconhecido — mismatch real de protocolo).
4. Chutamos **`20231101`** de novo (mesma lógica do RuneHost) → login aceitou o pacote SSO
   sem erro, mas a criação/entrada não avançava (mismatch mais sutil, não travava na porta).
5. Voltamos a **`20211103`** → o pacote SSO passou a ser aceito (`Request for connection (SSO
   mode)`), conta era reconhecida, mas ao **entrar no mundo** o map-server rejeitava:
   ```
   clif_parse: Received packet 0x0436 with expected packet length 23, but only 19 bytes
   remaining, disconnecting session #8.
   ```
   Esse foi o sinal decisivo. O pacote `0x0436` é o `WantToConnection`/`CZ_ENTER` (entrada no
   mapa). No código (`src/map/clif_shuffle.hpp`), esse pacote muda de **19 para 23 bytes**
   exatamente no corte `PACKETVER_RE >= 20211103` — ou seja, **o próprio valor que estávamos
   usando é o marco da mudança**. Um client mandando 19 bytes é necessariamente anterior a essa
   data.
6. Escolhemos **`20200902`** — um dos packetvers oficialmente testados pelo CI do rAthena
   (`.github/workflows/build_servers_packetversions.yml`), o mais próximo abaixo do corte.
   **Funcionou**: personagem entrou no mundo, andou entre mapas (prontera → prt_fild05) sem
   erro de pacote.

**Valor atual, fixado em `tools/docker/docker-compose.override.yml`:**
```yaml
services:
    builder:
        environment:
            BUILDER_CONFIGURE: "--enable-packetver=20200902"
```

### Se precisar trocar de client/packetver de novo

Não adianta só chutar a partir do nome da pasta ou de datas soltas dentro do exe (tentamos e
não bateu). O sinal mais confiável é observar o **log do map-server** na primeira tentativa de
entrar no mundo: qualquer `clif_parse: Received packet 0x... with expected packet length X,
but only Y bytes remaining` informa exatamente qual pacote não bate, e dá pra grepar esse
opcode em `src/map/clif_shuffle.hpp`/`src/map/packets.hpp` para achar a faixa exata de
PACKETVER onde o tamanho muda — é assim que fechamos o `20200902`.

## Patches feitos no core (`src/`) para viabilizar o login com esse client

Como é servidor single-player, aplicamos alguns bypasses direto no código-fonte (não são
hooks de `src/custom/`, porque mexem em fluxo de autenticação/criação que não tem ponto de
extensão pronto). Documentando aqui porque **não é comportamento padrão do rAthena** e é bom
lembrar disso ao atualizar (`git pull`) ou reportar bugs upstream.

- **`src/login/login.cpp`** (`login_mmo_auth`):
  - Conta desconhecida deixou de ser rejeitada — é **criada automaticamente** (sexo M,
    `group_id 99` = Admin) na hora, mesmo sem o sufixo `_M`/`_F` (necessário porque o client
    usa modo SSO, que não passa pelo fluxo clássico de auto-criação por sufixo).
  - Senha errada deixou de bloquear o login — **qualquer senha é aceita** para contas
    existentes (o log ainda registra a tentativa como aviso).
- **`src/login/login.cpp`** (`login_mmo_auth_new`):
  - Toda conta nova criada automaticamente já nasce com **`group_id 99` (Admin)** — não
    precisa rodar `UPDATE login SET group_id = 99` manualmente depois.
- **`src/char/char.cpp`** (`char_make_new_char`):
  - Checagem de classe inicial (`allowed_job_flag`, que só permite Novice/Doram por padrão)
    foi removida — o client FROSTUBE deixa escolher a classe já na criação (feature custom
    dele, não do rAthena vanilla), então qualquer `start_job` enviado pelo client é aceito.
  - Adicionados `ShowDebug` temporários nos pontos de rejeição silenciosa (que por padrão não
    logavam nada, dificultando diagnóstico). Aparecem no log do char-server como
    `DEBUG MAKECHAR: ...`.

**Nenhum desses patches é apropriado para um servidor multiplayer/público** — são
especificamente para reduzir fricção de um ambiente single-player local. Se algum dia este
fork for usado para outra coisa, reverter esses trechos antes.

## Problema conhecido, não resolvido: crash do client ao renderizar certos NPCs

Ao andar perto de um NPC ao sul de Prontera, o client crashou (access violation, `0xc0000005`,
dump mencionando `npc\1_etc_01.act`). É um crash **do lado do client** (não gera nada nos logs
do servidor) — provavelmente o client não tem o sprite/ator desse NPC nos dados dele (`.grf`),
ou há alguma diferença sutil de protocolo em pacotes de efeito/aparência que esse packetver
específico não cobre.

Contorno aplicado: reposicionamos o personagem manualmente via SQL (`UPDATE char SET
last_map=..., last_x=..., last_y=...`) para longe do NPC problemático — ver doc 05 para o
atalho via `make -f tools/docker/dev.mk reset-positions`. Se o crash se repetir perto de outros
NPCs/mobs específicos, o padrão de investigação é: anotar mapa + coordenada + o que estava por
perto, e comparar com a lista de sprites que o client realmente tem em `data.grf`/`rdata.grf`.
Não investigamos a fundo ainda — fica para uma sessão futura se voltar a acontecer.
