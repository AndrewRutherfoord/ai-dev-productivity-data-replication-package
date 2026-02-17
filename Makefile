DCOMPOSE = docker compose

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
