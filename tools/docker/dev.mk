# Comandos de conveniência para o servidor rAthena local (single-player).
# Uso: make -f tools/docker/dev.mk <alvo> [VARS]
#
# Não é o Makefile de build do rAthena (esse é o ./Makefile gerado pelo configure,
# na raiz do repo). Este aqui só mexe no banco via docker exec.

DB_CONTAINER  := rathena-db
DB_USER       := ragnarok
DB_PASS       := ragnarok
DB_NAME       := ragnarok
ACCOUNT_ID    ?= 2000000
NAME          ?= NovoChar
SLOT          ?= 0
MAP           ?= prontera
X             ?= 155
Y             ?= 185

# Pasta de dumps: não versionada (ver .gitignore), fica ao lado deste Makefile
# independente de onde o `make` for chamado.
MK_DIR        := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_DIR      := $(abspath $(MK_DIR)../..)
DUMP_DIR      := $(MK_DIR)dumps
TIMESTAMP     := $(shell date +%Y%m%d_%H%M%S)
FILE          ?= $(DUMP_DIR)/ragnarok_$(TIMESTAMP).sql

COMPOSE       := docker compose -f $(MK_DIR)docker-compose.yml -f $(MK_DIR)docker-compose.override.yml
# Containers realmente necessários para jogar (db + os 4 servidores).
# Não inclui o builder, que só roda sob demanda no alvo "build".
APP_SERVICES  := db login char map web

define SQL_EXEC
docker exec $(DB_CONTAINER) mariadb -u$(DB_USER) -p$(DB_PASS) $(DB_NAME) -e
endef

.PHONY: build up new-char reset-positions list-chars db-dump db-restore help

help:
	@echo "Alvos disponiveis:"
	@echo "  make -f tools/docker/dev.mk build"
	@echo "      Recompila os binarios do servidor do zero (login/char/map/web-server)."
	@echo "      Usar sempre que mudar codigo em src/ ou o packetver."
	@echo "  make -f tools/docker/dev.mk up"
	@echo "      Sobe so os containers necessarios pra jogar: $(APP_SERVICES)."
	@echo "  make -f tools/docker/dev.mk new-char NAME=Foo SLOT=1 [ACCOUNT_ID=2000000]"
	@echo "      Cria um personagem novo direto no banco (sem passar pela tela de criacao)."
	@echo "  make -f tools/docker/dev.mk reset-positions [MAP=prontera X=155 Y=185]"
	@echo "      Reseta a posicao (last_map/save_map) de TODOS os personagens de TODAS as contas."
	@echo "  make -f tools/docker/dev.mk list-chars"
	@echo "      Lista personagens existentes (char_id, conta, nome, mapa)."
	@echo "  make -f tools/docker/dev.mk db-dump [FILE=caminho.sql]"
	@echo "      Salva um dump completo do banco em tools/docker/dumps/ (pasta nao versionada)."
	@echo "  make -f tools/docker/dev.mk db-restore FILE=caminho.sql"
	@echo "      Restaura o banco a partir de um dump (sobrescreve os dados atuais)."

build:
	@echo "Parando login/char/map/web..."
	@$(COMPOSE) stop login char map web
	@echo "Removendo binarios antigos para forcar recompilacao completa..."
	@rm -f $(REPO_DIR)/login-server $(REPO_DIR)/char-server $(REPO_DIR)/map-server $(REPO_DIR)/web-server
	@$(COMPOSE) rm -f builder
	@echo "Compilando (pode levar de 5 a 15 minutos na primeira vez apos mudar o packetver)..."
	@$(COMPOSE) run --rm builder
	@echo "Build concluido. Rode 'make -f tools/docker/dev.mk up' para subir os servidores."

up:
	@$(COMPOSE) up -d $(APP_SERVICES)
	@$(COMPOSE) ps $(APP_SERVICES)

new-char:
	@$(SQL_EXEC) "INSERT INTO \`char\` \
		(account_id, char_num, name, class, base_level, job_level, zeny, \
		 str, agi, vit, \`int\`, dex, luk, max_hp, hp, max_sp, sp, status_point, \
		 hair, hair_color, last_map, last_x, last_y, save_map, save_x, save_y, sex) \
		VALUES \
		($(ACCOUNT_ID), $(SLOT), '$(NAME)', 0, 1, 1, 0, \
		 1, 1, 1, 1, 1, 1, 40, 40, 11, 11, 48, \
		 1, 0, '$(MAP)', $(X), $(Y), '$(MAP)', $(X), $(Y), 'M');"
	@echo "Personagem '$(NAME)' criado na conta $(ACCOUNT_ID), slot $(SLOT)."

reset-positions:
	@$(SQL_EXEC) "UPDATE \`char\` SET \
		last_map='$(MAP)', last_x=$(X), last_y=$(Y), \
		save_map='$(MAP)', save_x=$(X), save_y=$(Y);"
	@echo "Todos os personagens foram reposicionados em $(MAP) ($(X),$(Y))."

list-chars:
	@$(SQL_EXEC) "SELECT char_id, account_id, char_num, name, last_map, last_x, last_y FROM \`char\` ORDER BY account_id, char_num;"

db-dump:
	@mkdir -p $(DUMP_DIR)
	@docker exec $(DB_CONTAINER) mariadb-dump -u$(DB_USER) -p$(DB_PASS) --single-transaction --routines --triggers $(DB_NAME) > $(FILE)
	@echo "Dump salvo em $(FILE)"

db-restore:
ifndef FILE
	$(error Informe FILE=caminho.sql, ex: make -f tools/docker/dev.mk db-restore FILE=tools/docker/dumps/ragnarok_20260101_120000.sql)
endif
	@test -f $(FILE) || (echo "Arquivo nao encontrado: $(FILE)"; exit 1)
	@docker exec -i $(DB_CONTAINER) mariadb -u$(DB_USER) -p$(DB_PASS) $(DB_NAME) < $(FILE)
	@echo "Banco restaurado a partir de $(FILE)"
