.PHONY: help backfill backfill-quick ingest-real run-daily train-nlp inspect test clean harmonise inspect-silver dp-release test-privacy train-fusion detect evaluate-detection test-detection playbooks evidence-card test-decision serve test-api validate test-validation impact test-impact governance test-governance fhir-export drift-check test-interop test-sentinel sentinel-replay timemachine test-timemachine biascorrect test-biascorrect whatif test-whatif

PYTHON := ./bin/py

help:
	@echo "Munzir (منذر) Early Warning Platform - Automation"
	@echo "====================================================="
	@echo "  make backfill          : Reproduce 3+ years of bronze lakehouse data"
	@echo "  make backfill-quick    : Reproduce 1 year of bronze lakehouse data"
	@echo "  make ingest-real       : Ingest authentic OSHA Severe Injuries & CDC NSSP feeds"
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
	@echo "  make serve             : Launch Munzir web application and role-based API"
	@echo "  make test-api          : Run Phase 5 RBAC, privacy boundary & API unit tests"
	@echo "  make timemachine       : Run retrospective historical event time machine replay"
	@echo "  make test-timemachine  : Run Phase 6 Time Machine strict as-of-date tests"
	@echo "  make biascorrect       : Run Sentinel WBGT empirical bias correction"
	@echo "  make test-biascorrect  : Run microclimate bias correction validation tests"
	@echo "  make whatif            : Run What-If occupational intervention simulator (Monte Carlo)"
	@echo "  make test-whatif       : Run What-If simulator and assumptions ledger tests"
	@echo "  make test              : Run full unit test suite"
	@echo "  make clean             : Clean local test caches"

backfill:
	$(PYTHON) -m prahari backfill --years 3.0 --region uae --seed 42

backfill-quick:
	$(PYTHON) -m prahari backfill --years 1.0 --region uae --seed 42

ingest-real:
	$(PYTHON) -m prahari ingest-real --region uae

clinical-profile:
	$(PYTHON) -m prahari clinical-profile --hazard heat --severity alert --wbgt 34.0

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

fhir-export:
	$(PYTHON) -m prahari fhir-export --out fhir_surveillance_bundle.json

drift-check:
	$(PYTHON) -m prahari drift-check

test-interop:
	$(PYTHON) -m pytest tests/test_interop.py -v

test-sentinel:
	$(PYTHON) -m pytest tests/test_sentinel.py -v

sentinel-replay:
	$(PYTHON) hardware/replay/replay_trace.py --api-url http://localhost:8000

run-daily:
	$(PYTHON) -m prahari run-daily --region uae

train-nlp:
	$(PYTHON) -m prahari train-nlp

inspect:
	$(PYTHON) -m prahari inspect

timemachine:
	$(PYTHON) -m prahari timemachine --event $(or $(EVENT),pnw_2021)

test-timemachine:
	$(PYTHON) -m pytest tests/test_timemachine.py -v

biascorrect:
	$(PYTHON) -m prahari biascorrect --site $(or $(SITE),SITE-JA-01) --folds $(or $(FOLDS),5)

test-biascorrect:
	$(PYTHON) -m pytest tests/test_bias_correction.py -v

whatif:
	$(PYTHON) -m prahari whatif --site $(or $(SITE),SITE-JA-01) --action $(or $(ACTION),combined_protocol) --workforce $(or $(WORKFORCE),3200)

test-whatif:
	$(PYTHON) -m pytest tests/test_whatif.py -v

renal-scan:
	$(PYTHON) -m prahari renal-scan --site $(or $(SITE),SITE-JA-01) --cumulative-wbgt $(or $(WBGT_HOURS),65.0)

test-renal:
	$(PYTHON) -m pytest tests/test_biomarkers.py -v

deconvolve:
	$(PYTHON) -m prahari deconvolve --district $(or $(DISTRICT),Muhaisnah) --cases $(or $(CASES),45)

test-deconvolve:
	$(PYTHON) -m pytest tests/test_deconvolution.py -v

dispatch:
	$(PYTHON) -m prahari dispatch --site $(or $(SITE),SITE-JA-01) --workforce $(or $(WORKFORCE),1200)

test-dispatch:
	$(PYTHON) -m pytest tests/test_dispatch_optimizer.py -v

jais-dispatch:
	$(PYTHON) -m prahari jais-dispatch --site $(or $(SITE),SITE-JA-01) --tier $(or $(TIER),Warning)

test-jais:
	$(PYTHON) -m pytest tests/test_jais_integration.py -v

copilot:
	$(PYTHON) -m prahari copilot --query "$(or $(QUERY),What should I do right now for outdoor workers?)" --site $(or $(SITE),SITE-JA-01)

dossier:
	$(PYTHON) -m prahari dossier --site $(or $(SITE),SITE-JA-01) --export $(or $(EXPORT),terminal)

test-copilot:
	$(PYTHON) -m pytest tests/test_copilot.py -v

test-safeharbor:
	$(PYTHON) -m pytest tests/test_safe_harbor.py -v

test-compound:
	$(PYTHON) -m pytest tests/test_compound_hazard.py -v

test-championship:
	$(PYTHON) -m pytest tests/test_api_championship.py tests/test_causal_demix.py tests/test_biomarkers.py tests/test_deconvolution.py tests/test_dispatch_optimizer.py tests/test_jais_integration.py tests/test_copilot.py tests/test_safe_harbor.py tests/test_compound_hazard.py tests/test_iso7933.py tests/test_voice_intercom.py tests/test_policy_studio.py tests/test_championship_v2.py tests/test_cli.py -v

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf .pytest_cache data/cache/*.tmp __pycache__
