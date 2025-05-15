import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")

if not BACKEND_URL:
    st.error("❌ Backend URL is not set. Please start Ngrok using 'start_ngrok.py'.")
    st.stop()

st.set_page_config(layout="wide")
st.title("📄 Invoice Parser - AI-Powered Data Extraction")
st.write("Upload an invoice (PDF or image), and the system will extract details.")

# Layout
left_col, right_col = st.columns([2, 1])
uploaded_file = left_col.file_uploader("📤 Upload an invoice", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    temp_folder = "temp"
    os.makedirs(temp_folder, exist_ok=True)
    file_path = os.path.join(temp_folder, uploaded_file.name)

    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        left_col.success("✅ File uploaded successfully. Processing...")

        with open(file_path, "rb") as f:
            files = {"file": f}
            try:
                response = requests.post(
                    BACKEND_URL, 
                    files=files, 
                    timeout=180,  # Increase timeout to 3 minutes
                    headers={"Connection": "keep-alive"}  # Keep connection alive
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                left_col.error(f"❌ Backend connection error: {e}")
                st.stop()

        # Parse response safely
        try:
            result = response.json()
        except Exception:
            left_col.error(f"❌ Failed to parse backend response as JSON. Status code: {response.status_code}")
            left_col.text("Raw response:\n" + response.text)
            st.stop()

        conversation_id = result.get("conversation_id", "unknown")
        left_col.empty()
        right_col.empty()

        for index, res in enumerate(result.get("results", [])):
            image_url = res["image_url"]
            left_col.image(image_url, caption=f"Processed Invoice {index + 1}", width=180)
            modal_key = f"modal_{conversation_id}_{index}"

            if left_col.button(f"🧾 View Extracted Data - Invoice {index + 1}", key=modal_key):
                with st.expander(f"📜 Invoice Extraction Results - {conversation_id} (File {index + 1})", expanded=True):
                    left_col.subheader("📜 OCR Output")
                    left_col.text(res["OCR_Text"])
                    left_col.subheader("🧠 AI Extracted Data")
                    left_col.json(res["Qwen_Response"])

        right_col.subheader("📊 JSON Extracted Data")
        right_col.json(result.get("results", []))

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                st.warning(f"⚠️ Could not delete temp file: {e}")
