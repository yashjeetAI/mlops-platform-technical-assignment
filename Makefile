.PHONY: up down reset logs seed backend-test frontend-test test

# Start the full stack (db, backend, worker, frontend). Sample data auto-seeds
# into an empty database on first run.
up:
	docker compose up --build

down:
	docker compose down

# Wipe the database volume and start fresh (re-seeds sample data).
reset:
	docker compose down -v && docker compose up --build

logs:
	docker compose logs -f backend worker

# Load the sample dataset on demand (no-op if the registry already has models).
seed:
	docker compose exec backend python -m app.db.seed_sample

backend-test:
	cd backend && . .venv/bin/activate && pytest

frontend-test:
	cd frontend && CI=true npx ng test --watch=false

test: backend-test frontend-test
