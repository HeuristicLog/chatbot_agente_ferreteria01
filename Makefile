.PHONY: setup up down logs test db-seed ps
.DEFAULT_GOAL := up

setup:
	cp -n .env.example .env || true
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose exec -T backend pytest tests/

db-seed:
	@echo "Seeding main PostgreSQL database (Users, Sellers, FAQs)..."
	docker compose exec -T backend python scripts/seed_database.py
	@echo "Seeding Mock Logistics database (Tickets, Routes)..."
	docker compose exec -T backend curl -X POST http://mock-logistics-api:8080/api/v1/seed
	@echo "All databases seeded successfully."

ps:
	docker compose ps
