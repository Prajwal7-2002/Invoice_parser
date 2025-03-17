import os
import base64
import logging
import uuid  # Unique conversation ID
import pytesseract
import requests
from flask import Flask, request, jsonify, session, send_from_directory
from pdf2image import convert_from_path
from PIL import Image
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()
UPLOAD_FOLDER = "uploads/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set Tesseract OCR path manually
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Poppler path for PDF conversion
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

# OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Missing OpenRouter API Key. Set it in a .env file.")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise ValueError("SECRET_KEY is missing! Add it to the .env file.")


# ✅ Convert Image to Base64
def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logging.error(f"Failed to encode image: {e}")
        return ""

# ✅ OCR Processing (Extract text from image)
def process_ocr(image_path):
    try:
        return pytesseract.image_to_string(Image.open(image_path)).strip()
    except Exception as e:
        logging.error(f"OCR Processing failed: {e}")
        return ""

# ✅ Convert PDF to Images
def convert_pdf_to_images(pdf_path):
    image_paths = []
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        for i, img in enumerate(images):
            image_path = pdf_path.replace(".pdf", f"_{i}.png")
            img.save(image_path, "PNG")
            image_paths.append(image_path)
        return image_paths
    except Exception as e:
        logging.error(f"PDF to Image conversion failed: {e}")
        return []

# ✅ Call Qwen 2.5VL API for Invoice Extraction
def call_qwen_api(base64_image):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct",
        "messages": [
            {"role": "system", "content": "Extract invoice details and return a structured JSON output."},
            {"role": "user", "content": [
                {"type": "text", "text": "Extract invoice details from this image."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ]
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response_json = response.json()
        logging.info(f"Qwen API Response Status: {response.status_code}")
        if response.status_code == 402 or "error" in response_json:
            error_message = response_json.get("error", {}).get("message", "")
            if "More credits are required" in error_message:
                logging.warning("⚠️ Qwen API credits are insufficient. Skipping API call.")
                return {"error": "Insufficient Qwen API credits. Please upgrade your plan."}
        return response_json if response.status_code == 200 else {"error": "Qwen API call failed"}
    except requests.RequestException as e:
        logging.error(f"Failed to call Qwen API: {e}")
        return {"error": "Failed to reach OpenRouter API"}

# ✅ Serve Uploaded Images via URL
@app.route("/uploads/<conversation_id>/<filename>")
def get_uploaded_file(conversation_id, filename):
    file_path = os.path.join(UPLOAD_FOLDER, conversation_id, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(os.path.join(UPLOAD_FOLDER, conversation_id), filename)

# ✅ Upload and Process Files
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
    image_paths = convert_pdf_to_images(file_path) if file.filename.lower().endswith(".pdf") else [file_path]
    results = []
    for img_path in image_paths:
        filename = os.path.basename(img_path)
        image_url = f"{request.host_url}uploads/{conversation_id}/{filename}"
        base64_img = encode_image(img_path)
        ocr_text = process_ocr(img_path)
        qwen_response = call_qwen_api(base64_img)
        if "extracted_text" in qwen_response and qwen_response["extracted_text"] == ocr_text:
            del qwen_response["extracted_text"]
        results.append({"image_url": image_url, "OCR_Text": ocr_text, "Qwen_Response": qwen_response})
    return jsonify({"conversation_id": conversation_id, "results": results})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render assigns a dynamic port
    app.run(host="0.0.0.0", port=port)
