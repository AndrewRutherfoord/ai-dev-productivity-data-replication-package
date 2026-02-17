-include Makefile.local

DCOMPOSE ?= docker compose

build:
	$(DCOMPOSE) build

up:
	$(DCOMPOSE) up -d

logs:
	$(DCOMPOSE) logs -f

down:
	$(DCOMPOSE) down

pull:
	$(DCOMPOSE) pull

# Remove all volumes (data will be lost). Has a confirm step to prevent accidental data loss.
clear-volumes:
	@read -p "This will remove all volumes and data. Are you sure? (y/N) " -n 1 -r; echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
			$(DCOMPOSE) down -v; \
			docker volume prune -f; \
			echo "All volumes removed."; \
	else \
			echo "Operation cancelled. No volumes were removed."; \
	fi

DOCKER_IMAGE = bscprojectgradingsystem-2023
DOCKER_REGISTRY = ghcr.io/bscgradingsystem
DOCKER_PLATFORM = linux/arm64
DOCKER_BUILDX_BUILDER = default

DOCKER_CONTEXT_NAME ?= default
DOCKER_NAMESPACE ?= bsc-grading-system

build-push-images:
	docker context use $(DOCKER_BUILDX_BUILDER)
	docker buildx use $(DOCKER_BUILDX_BUILDER)
	docker buildx bake --push -f docker-bake.hcl 
