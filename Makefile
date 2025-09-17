
# Variables
IMAGE_NAME=curacel-claims-qa
PORT=8000

.PHONY: run test lint format docker-build docker-run demo k8s-deploy

# Run app locally
run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port $(PORT)

# Test codebase
test:
	pytest -v --maxfail=1 --disable-warnings

# Lint codebase
lint:
	flake8 src tests

# Format codebase
format:
	black src tests
	isort src tests

# Build Docker image
docker-build:
	docker build -t $(IMAGE_NAME) .

# Run Docker container
docker-run:
	docker run --rm -p $(PORT):$(PORT) $(IMAGE_NAME)

# Demo OCR modes for reviewers
demo:
	python demo_ocr_modes.py

# Deploy to Kubernetes
k8s-deploy:
	kubectl apply -f k8s/
