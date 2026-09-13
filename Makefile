# Reproducible commands. Assumes an activated virtualenv for the local targets.
.PHONY: install test eval demo docker-build docker-run

install:      ## install pinned dependencies
	pip install -r requirements.txt

test:         ## run the deterministic unit/contract tests (no API key)
	python -m pytest tests/ -q

eval:         ## run the five FIN evaluation cases (needs ANTHROPIC_API_KEY)
	python -m src.cli eval

demo:         ## start a sample FIN-001 run
	python -m src.cli start --case FIN-001 --invoice INV-7777 --vendor "Acme Supplies" \
		--amount 1250.00 --currency AUD --date 2026-09-10 --po PO-5001

docker-build: ## build the container image
	docker build -t finance-agent-monash .

docker-run:   ## run the eval cases in the container (pass the key from your env)
	docker run --rm -e ANTHROPIC_API_KEY finance-agent-monash eval
