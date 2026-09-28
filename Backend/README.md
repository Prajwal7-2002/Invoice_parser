# Invoice Parser

This project is a document-processing application designed to help businesses capture invoice information faster and with less manual effort. Instead of a person reading every invoice and entering details by hand, the system is built to accept invoice files, process them, and extract key information such as vendor name, invoice number, totals, dates, and line items.

This repository contains the backend API and a simple frontend interface for testing and demonstration.

## What this project is solving

Many businesses still rely on manual invoice processing. That creates problems such as:

- slow data entry
- human error in extraction
- delays in approvals and payment cycles
- difficulty scaling when invoice volume increases

The goal of this project is to reduce those issues by creating an automated workflow for invoice intake and data extraction.

## Project status

This is an early-stage MVP and foundation project. The system is structured for future scaling, but some production features are intentionally not enabled yet.

For example:

- the API is running on FastAPI
- the health endpoint is available
- upload routes are reserved and not yet active for secure production use
- cloud storage, database integration, and production security controls are planned next

## Architecture at a glance

The application is separated into two main parts:

- Backend API: handles requests, configuration, and service logic
- Frontend UI: a lightweight interface for uploading invoice files and viewing extraction results

The current backend is built with Python and FastAPI, and the frontend uses Streamlit for a simple user experience.

## Tech stack

- Python
- FastAPI
- Pydantic and Pydantic Settings
- Streamlit
- Docker
- Uvicorn

## How the workflow works

1. A user uploads an invoice PDF or image.
2. The frontend sends the file to the backend.
3. The backend validates the request and prepares the processing environment.
4. The extraction layer can identify important invoice data.
5. The result is returned to the user in a readable format.

The project is designed to be extended with OCR, AI-based extraction, and cloud storage in later stages.

## Repository structure

- Backend: API and service logic
- frontend: simple UI for invoice upload and viewing results
- uploads: storage area for uploaded files during local testing

## Local setup

Follow these steps on Windows PowerShell:

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Once the server is running, you can check:

- API health: http://localhost:8080/api/v1/health
- API docs: http://localhost:8080/api/v1/docs

## Trying extraction locally

Extraction is off by default. To try it, add these to `Backend/.env`:

```
EXTRACTION_ENABLED=true
OPENROUTER_API_KEY=<your key>
# Windows only, if Tesseract/Poppler are not on PATH:
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\poppler-24.08.0\Library\bin
```

Then send a file to `POST /api/v1/extractions`, or run the Streamlit app in `frontend/`.
The response contains the extracted invoice, a list of issues found by the business-rule
checks, and a `status` of `ok` or `needs_review`.

## Tests and evaluation

```powershell
cd Backend
python -m pytest
python -m eval.run_eval   # scores field accuracy on eval/dataset (see eval/dataset/README.md)
```

## Docker setup

```powershell
cd Backend
docker build -t invoice-parser-api .
docker run --rm -p 8080:8080 --env-file .env invoice-parser-api
```

## Key notes for contributors and deployment

- Do not commit real secrets to the repository.
- Keep environment variables in a local `.env` file only.
- The upload endpoint is intentionally not enabled for production use yet.
- This project is structured for a future move into secure cloud deployment and real invoice data processing.

## Summary

This project demonstrates an automated invoice processing workflow built around modern Python web services and a simple user interface. It is a practical example of applying AI-driven document understanding to real business operations, while keeping the foundation clean, modular, and ready for future expansion.

If you are reviewing this project as a recruiter or stakeholder, the main message is simple: this is a document automation solution designed to save time, reduce errors, and create a scalable foundation for processing business documents intelligently.
