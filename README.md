# Invoice Parser

This project is a practical document-processing application built to reduce the time and effort involved in handling invoices. Instead of manually reading each invoice and typing out key details, the system is designed to accept invoice files, extract the important information, and present it in a structured format.

At its core, this project focuses on solving a common business problem: invoice processing is repetitive, slow, and prone to human error. The goal is to make that process faster, more accurate, and easier to scale.

## Why this project matters

Invoices contain valuable business information, but processing them manually is often inefficient. Common issues include:

- slow data entry
- mistakes in totals, dates, and supplier details
- delays in approval and payment workflows
- growing operational complexity as file volume increases

This project aims to reduce those problems by turning raw invoice documents into cleaner, machine-readable data.

## What the system does

The application is designed to receive invoice PDFs or images and extract useful information such as:

- vendor or supplier name
- invoice number
- invoice date
- due date
- tax amounts
- total payable amount
- line-item details when available

This creates a foundation for automating back-office finance tasks and reducing manual review.

## Project status

This is an early-stage MVP and a strong foundation for future development. The system is structured to grow, but some production features are intentionally still in progress.

The current version includes:

- a FastAPI-based backend
- a health-check endpoint for service monitoring
- a simple frontend for uploading invoice files and viewing results
- a modular architecture that can support OCR, AI extraction, and cloud-backed workflows later

## Architecture overview

The project is organized into a few key components:

- Backend: handles the API, request flow, and business logic
- frontend: small user interface for testing the workflow
- uploads: local folder used for invoice files during development

The backend is built with Python and FastAPI, while the frontend uses Streamlit to provide a simple interactive experience.

## Tech stack

- Python
- FastAPI
- Pydantic and Pydantic Settings
- Streamlit
- Docker
- Uvicorn

## How the workflow works

1. A user uploads an invoice file.
2. The frontend sends the file to the backend.
3. The backend validates and prepares the request.
4. The extraction logic identifies important invoice fields.
5. The structured result is returned to the user for review or further processing.

This project is designed to expand into more advanced OCR and AI-powered document workflows over time.

## Repository structure

- Backend/: contains the main API service and backend configuration
- frontend/: contains the simple UI for invoice uploads
- uploads/: local folder for uploaded files during development
- README.md: overview of the project for the repository as a whole

## Local setup

From the project root, run the following in PowerShell:

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Once the server is running, you can view:

- Health check: http://localhost:8080/api/v1/health
- API documentation: http://localhost:8080/api/v1/docs

## Docker setup

```powershell
cd Backend
docker build -t invoice-parser-api .
docker run --rm -p 8080:8080 --env-file .env invoice-parser-api
```

## Important notes

- Do not commit real secrets to the repository.
- Keep environment variables in a local `.env` file.
- The upload endpoint is intentionally not enabled for production use yet.
- This project is meant to be a scalable foundation for future AI and document automation work.

## Summary

This project is a clear example of applying practical AI and automation to a real business workflow. It sits in the space where software engineering meets operations: reducing repetitive work, improving data accuracy, and creating a cleaner foundation for intelligent document processing.


