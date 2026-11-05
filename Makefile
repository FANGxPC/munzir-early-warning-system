.PHONY: help backfill backfill-quick run-daily train-nlp inspect test clean harmonise inspect-silver dp-release test-privacy train-fusion detect evaluate-detection test-detection playbooks evidence-card test-decision serve test-api validate test-validation impact test-impact governance test-governance

PYTHON := ./bin/py

help:
	@echo "PRAHARI Early Warning Platform - Automation"
	@echo "====================================================="
	@echo "  make backfill          : Reproduce 3+ years of bronze lakehouse data"
	@echo "  make backfill-quick    : Reproduce 1 year of bronze lakehouse data"
	@echo "  make run-daily         : Run daily ingestion timer step (simulates Azure Function)"
	@echo "  make train-nlp         : Train incident text classifier (OSHA narratives)"
	@echo "  make inspect           : Inspect Bronze storage statistics and sample rows"
	@echo "  make harmonise         : Execute Phase 2 Bronze -> Silver harmonisation"
	@echo "  make inspect-silver    : Inspect Silver harmonised lakehouse & suppressed view"
	@echo "  make dp-release        : Generate Differential Privacy release (OpenDP)"
	@echo "  make test-privacy      : Run dedicated Phase 2 privacy verification tests"
	@echo "  make train-fusion      : Train L4 LightGBM fusion model and calibrate"
	@echo "  make detect            : Run L1-L5 detection and alert generation"
	@echo "  make evaluate-detection: Evaluate detection lead time, sensitivity & decoys"
	@echo "  make test-detection    : Run Phase 3 detection unit & integration tests"
	@echo "  make playbooks         : List registered action playbooks and RACI matrix"
	@echo "  make evidence-card     : Generate and display decision-ready Evidence Card (<2s)"
	@echo "  make test-decision     : Run Phase 4 decision support unit tests"
	@echo "  make serve             : Launch PRAHARI web application and role-based API"
	@echo "  make test-api          : Run Phase 5 RBAC, privacy boundary & API unit tests"
	@echo "  make test              : Run full unit test suite"
	@echo "  make clean             : Clean local test caches"

backfill:
	$(PYTHON) -m prahari backfill --years 3.0 --region uae --seed 42

backfill-quick:
	$(PYTHON) -m prahari backfill --years 1.0 --region uae --seed 42

harmonise:
	$(PYTHON) -m prahari harmonise --region uae

inspect-silver:
	$(PYTHON) -m prahari inspect-silver

dp-release:
	$(PYTHON) -m prahari dp-release --epsilon 1.0

test-privacy:
	$(PYTHON) -m pytest tests/test_silver_store.py tests/test_spatial.py tests/test_suppression.py tests/test_differential_privacy.py -v

train-fusion:
	$(PYTHON) -m prahari train-fusion --start-date 2024-01-01 --end-date 2026-12-31 --split-date 2026-01-01 --step-days 2

detect:
	$(PYTHON) -m prahari detect --start-date 2024-01-01 --end-date 2026-10-31

evaluate-detection:
	$(PYTHON) -m prahari detect --start-date 2024-01-01 --end-date 2026-10-31 --evaluate

test-detection:
	$(PYTHON) -m pytest tests/test_detection_*.py -v

playbooks:
	$(PYTHON) -m prahari playbooks

evidence-card:
	$(PYTHON) -m prahari evidence-card --date 2025-08-20 --geo SITE-JA-01

test-decision:
	$(PYTHON) -m pytest tests/test_playbook_engine.py tests/test_evidence_card.py tests/test_acknowledgement.py tests/test_narrative.py -v

serve:
	$(PYTHON) -m prahari serve --host 0.0.0.0 --port 8000

test-api:
	$(PYTHON) -m pytest tests/test_api_*.py -v

validate:
	$(PYTHON) -m prahari validate --seed $(or $(SEED),42) --n-injections 100 --out-dir validation

test-validation:
	$(PYTHON) -m pytest tests/test_validation.py -v

impact:
	$(PYTHON) -m prahari impact --workforce 50000 --export-policy

test-impact:
	$(PYTHON) -m pytest tests/test_impact_model.py tests/test_api_impact.py -v

governance:
	$(PYTHON) -m prahari governance

test-governance:
	$(PYTHON) -m pytest tests/test_responsible_ai_governance.py -v

run-daily:
	$(PYTHON) -m prahari run-daily --region uae

train-nlp:
	$(PYTHON) -m prahari train-nlp

inspect:
	$(PYTHON) -m prahari inspect

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf .pytest_cache data/cache/*.tmp __pycache__
