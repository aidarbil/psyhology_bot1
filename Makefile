.PHONY: build up down restart logs shell

# Default variables
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = telegram_bot

# Build the Docker image
build:
	docker compose -f $(COMPOSE_FILE) build

# Start the containers in detached mode
up:
	docker compose -f $(COMPOSE_FILE) up -d

# Stop and remove the containers
down:
	docker compose -f $(COMPOSE_FILE) down

# Restart the containers
restart:
	docker compose -f $(COMPOSE_FILE) restart

# Show logs of the running containers
logs:
	docker compose -f $(COMPOSE_FILE) logs -f $(SERVICE_NAME)

# Open a shell in the running container
shell:
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) /bin/bash

# Run tests
test:
	@echo "Running tests..."
	python -m pytest

# Run the bot locally (without Docker)
run:
	@echo "Running the bot locally..."
	python main.py

# Run the bot in test mode locally
run-test:
	@echo "Running the bot in test mode..."
	bash run_bot_in_test_mode.sh

# Update dependencies
update-deps:
	pip install -r requirements.txt

# Cleans up unused Docker resources
cleanup:
	docker system prune -f

# Help command
help:
	@echo "Available commands:"
	@echo " make build      - Build the Docker image"
	@echo " make up         - Start the containers in detached mode"
	@echo " make down       - Stop and remove the containers"
	@echo " make restart    - Restart the containers"
	@echo " make logs       - Show logs of the running containers"
	@echo " make shell      - Open a shell in the running container"
	@echo " make test       - Run tests"
	@echo " make run        - Run the bot locally (without Docker)"
	@echo " make run-test   - Run the bot in test mode"
	@echo " make update-deps - Update Python dependencies"
	@echo " make cleanup    - Clean up unused Docker resources"
	@echo " make help       - Show this help message" 