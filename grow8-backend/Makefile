# Recipes are POSIX sh. On Windows, make falls back to cmd.exe when no sh is on PATH
# (e.g. make run from PowerShell or cmd), so use the sh that ships with Git for Windows.
# Git's install dir comes from `git --exec-path`, which is always
# <git>/<variant>/libexec/git-core (variant: mingw64, ucrt64, clangarm64, ...), so
# going up three levels reaches <git> for any install location or Git build.
ifeq ($(OS),Windows_NT)
GIT_ROOT := $(subst \,/,$(shell git --exec-path))/../../..
export PATH := $(GIT_ROOT)/usr/bin;$(GIT_ROOT)/bin;C:/Program Files/Git/usr/bin;$(PATH)
endif
SHELL := sh
COMPOSE := docker compose
SERVICES := creator_service contributor_service admin_service

.PHONY: help env config build up down restart logs ps reset-db test test-services postman lint fmt mysql venv

help:
	@echo "env | config | build | up | down | restart | logs | ps | reset-db | test | test-services | postman | lint | fmt | mysql | venv"

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

# Runs the Postman collection with Newman inside the compose network; report -> tests/reports/.
# Writes a few 'Postman:' rows into the dev DB (`make reset-db` removes them).
# MSYS_NO_PATHCONV stops Git Bash on Windows from rewriting the container paths.
postman:
	MSYS_NO_PATHCONV=1 docker run --rm --network grow8_default -v "$(CURDIR)/tests:/etc/newman" 		postman/newman:6.1.3-alpine run postman/grow8.postman_collection.json 		--env-var baseUrl=http://api:8000 		--reporters cli,json --reporter-json-export reports/postman-report.json

lint:
	$(COMPOSE) exec -T api ruff check /app/api /app/shared
	@for s in $(SERVICES); do $(COMPOSE) exec -T $$s ruff check . || exit 1; done

fmt:
	$(COMPOSE) exec -T api ruff check --fix /app/api /app/shared
	$(COMPOSE) exec -T api ruff format /app/api /app/shared
	@for s in $(SERVICES); do $(COMPOSE) exec -T $$s ruff check --fix . && $(COMPOSE) exec -T $$s ruff format . || exit 1; done

mysql:
	$(COMPOSE) exec mysql sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE"'

# Editor-only venv for VS Code/Pylance/ruff (code still runs in Docker). See docs.md 4.
venv:
	sh scripts/setup-venv.sh
