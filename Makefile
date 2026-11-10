.PHONY: setup start run test models-up models-down models-status warmup rehearse load-test
TEAMS ?= 15
setup:
	bash scripts/setup.sh
run:
	.venv/bin/python -m app.serve
start:
	bash scripts/start.sh
test:
	.venv/bin/python -m pytest -q
models-up:
	bash scripts/models_up.sh
models-down:
	bash scripts/models_down.sh
models-status:
	bash scripts/models_status.sh
warmup:
	.venv/bin/python scripts/warmup.py
rehearse:
	.venv/bin/python scripts/rehearse.py --teams $(TEAMS)
load-test:
	.venv/bin/python scripts/load_test.py --teams $(TEAMS)
