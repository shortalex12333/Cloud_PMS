.PHONY: verify verify-quick build test docker logs

verify:
	@chmod +x scripts/verify-local.sh && ./scripts/verify-local.sh

verify-quick:
	@chmod +x scripts/verify-local.sh && ./scripts/verify-local.sh --quick

build:
	cd apps/web && npm run build

test:
	cd apps/web && npm run test:unit

docker:
	docker compose --profile full up --build -d

logs:
	@echo "=== projection-worker ===" && docker logs cloud_pms-projection-worker-1 --tail 10 2>/dev/null || true
	@echo "=== embedding-worker ===" && docker logs cloud_pms-embedding-worker-1 --tail 10 2>/dev/null || true
	@echo "=== cache-listener ===" && docker logs cloud_pms-cache-listener-1 --tail 10 2>/dev/null || true
	@echo "=== email-watcher ===" && docker logs cloud_pms-email-watcher-1 --tail 10 2>/dev/null || true
