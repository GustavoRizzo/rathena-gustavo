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

define SQL_EXEC
docker exec $(DB_CONTAINER) mariadb -u$(DB_USER) -p$(DB_PASS) $(DB_NAME) -e
endef

.PHONY: new-char reset-positions list-chars help

help:
	@echo "Alvos disponiveis:"
	@echo "  make -f tools/docker/dev.mk new-char NAME=Foo SLOT=1 [ACCOUNT_ID=2000000]"
	@echo "      Cria um personagem novo direto no banco (sem passar pela tela de criacao)."
	@echo "  make -f tools/docker/dev.mk reset-positions [MAP=prontera X=155 Y=185]"
	@echo "      Reseta a posicao (last_map/save_map) de TODOS os personagens de TODAS as contas."
	@echo "  make -f tools/docker/dev.mk list-chars"
	@echo "      Lista personagens existentes (char_id, conta, nome, mapa)."

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
