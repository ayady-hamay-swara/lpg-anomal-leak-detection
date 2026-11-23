PYTHON=.venv/Scripts/python.exe
LARAVEL=php

setup:
	py -m venv .venv || true
	.venv/Scripts/python.exe -m pip install fastapi==0.115.12 uvicorn==0.34.2 pydantic==2.11.4 pyyaml==6.0.2 numpy==2.2.5 scikit-learn==1.6.1 pytest==8.3.5 httpx==0.28.1
	cd web && composer install

test:
	.venv/Scripts/python.exe -m pytest service/tests -q

run:
	start cmd /k "cd /d $(CURDIR) && .venv/Scripts/python.exe -m uvicorn app.main:app --app-dir service --host 127.0.0.1 --port 8000"
	start cmd /k "cd /d $(CURDIR)/web && php artisan serve --host=127.0.0.1 --port=8001"
