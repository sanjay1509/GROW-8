SHELL := sh
COMPOSE := docker compose
SERVICES := creator_service contributor_service admin_service

.PHONY: help env config build up down restart logs ps reset-db test test-services lint fmt mysql

help:
	@echo "env | config | build | up | down | restart | logs | ps | reset-db | test | test-services | lint | fmt | mysql"

env:
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "created .env from .env.example")

config: env
	$(COMPOSE) config -q

build: env
	$(COMPOSE) build

up: env
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

# DESTRUCTIVE: deletes all MySQL data so db/init/*.sql re-runs on next start.
reset-db: env
	$(COMPOSE) rm -sf mysql
	docker volume rm grow8_mysql_data || true
	$(COMPOSE) up -d --build

test:
	$(COMPOSE) exec -T api pytest

test-services:
	@for s in $(SERVICES); do echo "== $$s"; $(COMPOSE) exec -T $$s pytest || exit 1; done

lint:
	$(COMPOSE) exec -T api ruff check /app/api /app/shared
	@for s in $(SERVICES); do $(COMPOSE) exec -T $$s ruff check . || exit 1; done

fmt:
	$(COMPOSE) exec -T api ruff check --fix /app/api /app/shared
	$(COMPOSE) exec -T api ruff format /app/api /app/shared
	@for s in $(SERVICES); do $(COMPOSE) exec -T $$s ruff check --fix . && $(COMPOSE) exec -T $$s ruff format . || exit 1; done

mysql:
	$(COMPOSE) exec mysql sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE"'
