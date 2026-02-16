.PHONY: test-container test-container-smoke test-container-phase8

test-container:
	docker compose exec api python -m pytest tests -v --tb=short

test-container-smoke:
	docker compose exec api python -m pytest backend/tests/test_health.py -v --tb=short || docker compose exec api python -m pytest tests/test_health.py -v --tb=short

test-container-phase8:
	docker compose exec api python -m pytest tests/test_llm_client.py tests/test_orchestration_graph.py tests/test_query_endpoint_orchestrated.py -v --tb=short
