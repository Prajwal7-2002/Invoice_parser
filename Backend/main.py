import os
import base64
import logging
import uuid
import pytesseract
import requests
from flask_cors import CORS
from flask import Flask, request, jsonify, session, send_from_directory
from pdf2image import convert_from_path
from PIL import Image
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import time

import sys
print(f"Using Python from: {sys.executable}")

import json

def get_qwen_response(ocr_text):
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }

        # Truncate text to 3000 characters to stay within limits
        truncated_text = ocr_text[:3000]

        data = {
            "model": "qwen/qwen3-14b:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an invoice parser. Extract structured invoice information such as:\n"
                        "- invoice_number\n"
                        "- invoice_date\n"
                        "- due_date\n"
                        "- from (name, address, email)\n"
                        "- to (name, address, email)\n"
                        "- items (description, quantity, rate, subtotal)\n"
                        "- tax, total\n"
                        "- bank_details (bank_name, account_number, bsb)\n\n"
                        "Return the result as a valid JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": f"Extract structured data from the following invoice text:\n\n{truncated_text}"
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content, "error": "Failed to parse JSON"}

    except requests.exceptions.RequestException as e:
        logging.error(f"RequestException: {e}")
        logging.error(f"Request Payload: {json.dumps(data, indent=2)}")
        return {"error": str(e)}




# Load environment variables
load_dotenv()
UPLOAD_FOLDER = "uploads/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO)

# Tesseract & Poppler paths
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

# Flask app init
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise ValueError("SECRET_KEY is missing! Add it to the .env file.")

# PDF to Image Conversion (Optimized)
def convert_pdf_to_images(pdf_path):
    image_paths = []
    try:
        start_time = time.time()
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH, fmt='png')
        logging.info(f"Converted PDF to Images in {time.time() - start_time:.2f} seconds")

        for i, img in enumerate(images):
            image_path = pdf_path.replace(".pdf", f"_{i}.png")
            img.save(image_path, "PNG")
            image_paths.append(image_path)
            img.close()  # Free memory
        return image_paths
    except Exception as e:
        logging.error(f"PDF to Image conversion failed: {e}")
        return []

# OCR Processing (Asynchronous)
def process_ocr(image_path):
    try:
        return pytesseract.image_to_string(Image.open(image_path)).strip()
    except Exception as e:
        logging.error(f"OCR Processing failed for {image_path}: {e}")
        return ""

def process_images_concurrently(image_paths):
    with ThreadPoolExecutor() as executor:
        return list(executor.map(process_ocr, image_paths))

@app.route("/uploads/<conversation_id>/<filename>")
def get_uploaded_file(conversation_id, filename):
    file_path = os.path.join(UPLOAD_FOLDER, conversation_id, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(os.path.join(UPLOAD_FOLDER, conversation_id), filename)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    conversation_id = str(uuid.uuid4())
    session["conversation_id"] = conversation_id
    user_folder = os.path.join(UPLOAD_FOLDER, conversation_id)
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, file.filename)
    file.save(file_path)

    # Convert PDF to images or use directly if image file
    image_paths = convert_pdf_to_images(file_path) if file.filename.lower().endswith(".pdf") else [file_path]
    
    if not image_paths:
        return jsonify({"error": "Failed to process the file"}), 500
    
    start_time = time.time()
    ocr_texts = process_images_concurrently(image_paths)
    logging.info(f"OCR completed in {time.time() - start_time:.2f} seconds")

    results = []
    for img_path, ocr_text in zip(image_paths, ocr_texts):
        filename = os.path.basename(img_path)
        image_url = request.host_url.rstrip('/') + f"/uploads/{conversation_id}/{filename}"
        qwen_response = get_qwen_response(ocr_text)
        results.append({
            "image_url": image_url,
            "OCR_Text": ocr_text,
            "Qwen_Response": qwen_response
        })


    return jsonify({"conversation_id": conversation_id, "results": results})

if __name__ == "__main__":
    # Increase Flask timeout (optional for slow processing)
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080, threads=4)
