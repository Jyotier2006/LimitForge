# Contributing

## Development setup

```bash
git clone https://github.com/Jyotier2006/limitforge.git
cd limitforge
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
docker compose up -d redis
make quality
```

## Pull requests

1. Open an issue for behavioral changes.
2. Add tests that fail before the change and pass afterward.
3. Keep backend operations atomic; never introduce client-side
   check-then-increment logic for Redis.
4. Update documentation and `CHANGELOG.md`.
5. Run `make quality` and the Redis integration tests.

## Commit style

Use focused conventional commits, for example:

```text
feat(redis): add atomic token-bucket script
fix(sliding): correct retry time at boundary
bench(memory): record state bytes per key
```
