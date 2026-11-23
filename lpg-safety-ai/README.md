# LPG Safety AI

Advisory-only LPG tank and pipeline simulator with a Python/FastAPI AI service and Laravel HMI.

## 3-minute demo

1. Start Python: `make run` (Windows) or run `uvicorn app.main:app --app-dir service --port 8000`.
2. Start Laravel: `cd web && php artisan serve --port=8001`.
3. Open `http://127.0.0.1:8001`.
4. Register/sign in, open Playground, run `heat_wave`, `flange_seep`, or `weld_rupture`.
5. Toggle Answer key only after making an independent interpretation.

No write path to plant equipment exists.

## Safety

All plant limits except the 85% confirmed fill limit are marked PLACEHOLDER in `config/plant.yaml` and the UI. Plant procedures and the SIS/PSV/alarms always override this advisory system.
