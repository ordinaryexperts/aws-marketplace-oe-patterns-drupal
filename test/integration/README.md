# Drupal integration tests

Run after `make deploy` to validate the dev stack:

```bash
AWS_PROFILE=oe-patterns-dev make test-integration
```

Override the URL or stack name via environment variables (`TEST_BASE_URL`, `TEST_STACK_NAME`) or CLI flags (`--base-url`, `--stack-name`).
