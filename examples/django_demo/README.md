# Django demo

```bash
pip install -e ".[django]"
cd examples/django_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/strict/`. The first two requests are accepted and
later requests receive HTTP 429 until the fixed window resets. `/health/` is
exempt.
