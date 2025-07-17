.PHONY: help up down test migrate lint format pre-commit

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $1, $2}'

up:
	docker compose up

down:
	docker compose down

test:
	docker compose run --rm api poetry run pytest

migrate:
	docker compose run --rm api poetry run alembic upgrade head

migrate-generate:
	docker compose run --rm api poetry run alembic revision --autogenerate

lint:
	poetry run black --check app/ tests/
	poetry run isort --check-only app/ tests/
	poetry run flake8 app/ tests/

format:
	poetry run black app/ tests/
	poetry run isort app/ tests/

pre-commit:
	poetry run pre-commit run --all-files
