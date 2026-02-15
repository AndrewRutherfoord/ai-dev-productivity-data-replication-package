variable "REGISTRY" {
  default = "ghcr.io/andrewrutherfoord/neorepro-msr-tool"
}

variable "IMAGE_TAG" {
  default = "latest"
}

variable "PLATFORMS" {
  default = ["linux/amd64", "linux/arm64"]
}

group "default" {
  targets = ["backend", "driller", "frontend"]
}

# ============================================================================
# BACKEND
# ============================================================================

target "backend" {
  context    = "."
  dockerfile = "./backend/Dockerfile.prod"
  platforms  = "${PLATFORMS}"

  tags = [
    "${REGISTRY}/backend:${IMAGE_TAG}"
  ]

  push = true
}

target "driller" {
  context    = "."
  dockerfile = "./driller/Dockerfile.prod"
  platforms  = "${PLATFORMS}"

  tags = [
    "${REGISTRY}/driller:${IMAGE_TAG}"
  ]


  push = true
}

target "frontend" {
  context    = "."
  dockerfile = "./frontend/Dockerfile.prod"
  platforms  = "${PLATFORMS}"

  tags = [
    "${REGISTRY}/frontend:${IMAGE_TAG}"
  ]


  push = true
}