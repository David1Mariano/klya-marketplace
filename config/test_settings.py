from .settings import BASE_DIR  # noqa: F401
from .settings import *  # noqa: F401,F403

# Banco de teste local (SQLite). O settings.py mantem PostgreSQL como default;
# este modulo e usado apenas para rodar a suíte localmente quando o PostgreSQL
# nao estiver disponivel. Nao valida bloqueios de linha nem concorrencia real.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_test.sqlite3",
    }
}
