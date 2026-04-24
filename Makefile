.PHONY: help setup start stop logs seed clean rebuild

help:
	@echo "Lab Informatics Commands:"
	@echo "  make setup   - Initial setup"
	@echo "  make start   - Start all services"
	@echo "  make rebuild - Force rebuild all images and start"
	@echo "  make stop    - Stop services"
	@echo "  make logs    - View logs"
	@echo "  make seed    - Load sample data"
	@echo "  make clean   - Remove everything (volumes + containers)"

setup:
	@cp .env.example .env
	@chmod +x scripts/*.sh scripts/*.py
	@echo "✅ Setup complete!"
	@echo "Edit .env then run: make start"

start:
	docker-compose up -d
	@echo "✅ Started!"
	@echo "Frontend: http://localhost:3000"
	@echo "API: http://localhost:8000/docs"
	@echo "Database: localhost:5433"

stop:
	docker-compose down

logs:
	docker-compose logs -f

seed:
	@sleep 5
	docker-compose exec backend python /app/scripts/seed_data.py

setup-chembl:
	@bash scripts/setup_chembl.sh $(FILE)

rebuild:
	docker-compose up -d --build
	@echo "✅ Rebuilt and started!"
	@echo "Frontend: http://localhost:3000"
	@echo "API: http://localhost:8000/docs"

clean:
	docker-compose down -v
