PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest
RUFF := .venv/bin/ruff

.PHONY: install install-backend install-frontend migrate test test-backend test-frontend lint build dev-backend dev-frontend deploy clean

install: install-backend install-frontend

install-backend:
	python3 -m venv .venv
	$(PIP) install -r backend/requirements-dev.txt

install-frontend:
	cd frontend && pnpm install

migrate:
	cd backend && ../$(PYTHON) manage.py migrate

test: test-backend test-frontend

test-backend:
	cd backend && ../$(PYTEST) -q

test-frontend:
	cd frontend && pnpm test

lint:
	cd backend && ../$(RUFF) check .
	cd frontend && pnpm typecheck

build:
	cd frontend && pnpm build

dev-backend:
	cd backend && ../$(PYTHON) manage.py runserver 127.0.0.1:8000

dev-frontend:
	cd frontend && pnpm dev

deploy:
	./scripts/deploy.sh

clean:
	rm -rf backend/var frontend/dist frontend/node_modules .pytest_cache backend/.pytest_cache backend/.ruff_cache
