import streamlit as st
import requests
import os

# 🔹 Use Cloudflare Tunnel URL from environment variable
BACKEND_URL = os.getenv("BACKEND_URL", "https://703c7c84ac7ccd.lhr.life/upload")

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
        try:
            response = requests.post(BACKEND_URL, files=files, timeout=30)  # 🔹 Added timeout
            response.raise_for_status()  # 🔹 Raises error if request fails
        except requests.exceptions.RequestException as e:
            left_col.error(f"❌ Backend connection error: {e}")
            os.remove(file_path)
            st.stop()

    if response.status_code == 200:
        result = response.json()
        conversation_id = result["conversation_id"]

        left_col.empty()
        right_col.empty()

        for index, res in enumerate(result["results"]):
            image_url = res["image_url"]
            left_col.image(image_url, caption=f"Processed Invoice {index + 1}", width=180)  # 🔹 Smaller images
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
