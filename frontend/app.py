import streamlit as st
import requests
import os

# Flask backend URL (Update with ngrok URL when needed)
BACKEND_URL = "http://127.0.0.1:5000/upload"

st.set_page_config(layout="wide")

st.title("📄 Invoice Parser - AI-Powered Data Extraction")

st.write("Upload an invoice (PDF or image), and the system will extract details.")

# Create layout
left_col, right_col = st.columns([2, 1])

uploaded_file = left_col.file_uploader("📤 Upload an invoice", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    temp_folder = "temp"
    os.makedirs(temp_folder, exist_ok=True)
    file_path = os.path.join(temp_folder, uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    left_col.success("✅ File uploaded successfully. Processing...")

    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(BACKEND_URL, files=files)

    if response.status_code == 200:
        result = response.json()
        conversation_id = result["conversation_id"]

        left_col.empty()
        right_col.empty()

        for index, res in enumerate(result["results"]):
            image_url = res["image_url"]
            left_col.image(image_url, caption=f"Processed Invoice {index + 1}", width=200)
            modal_key = f"modal_{conversation_id}_{index}"

            if left_col.button(f"🧾 View Extracted Data - Invoice {index + 1}", key=modal_key):
                with st.expander(f"📜 Invoice Extraction Results - {conversation_id} (File {index + 1})", expanded=True):
                    left_col.subheader("📜 OCR Output")
                    left_col.text(res["OCR_Text"])
                    left_col.subheader("🧠 AI Extracted Data")
                    left_col.json(res["Qwen_Response"])

        right_col.subheader("📊 JSON Extracted Data")
        right_col.json(result["results"])

    else:
        left_col.error("❌ Error processing the file!")

    os.remove(file_path)
