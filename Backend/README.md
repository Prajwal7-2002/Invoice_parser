# Invoice Parser API

This directory is the new production backend. The legacy Flask prototype remains
in `main.py` temporarily and must not be deployed.

## Local run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Check `http://localhost:8080/api/v1/health` and view local API documentation at
`http://localhost:8080/api/v1/docs`.

## Docker run

```powershell
docker build -t invoice-parser-api .
docker run --rm -p 8080:8080 --env-file .env invoice-parser-api
```

Do not place real secrets in `.env.example` or commit a real `.env` file.
