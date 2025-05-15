import subprocess
import threading
from pyngrok import ngrok
import time
import os


VENV_PYTHON = r"D:\Developer\invoice_parser\venv\Scripts\python.exe"

# Start Flask tunnel (port 5000)
flask_tunnel = ngrok.connect(8080)
print(f"🌐 Flask backend is live at: {flask_tunnel.public_url}")

os.environ["BACKEND_URL"] = f"{flask_tunnel.public_url}/upload"


# Start Streamlit tunnel (port 8501)
streamlit_tunnel = ngrok.connect(8501)
print(f"🌐 Streamlit frontend is live at: {streamlit_tunnel.public_url}")

# Start Flask backend
def run_flask():
    subprocess.run([VENV_PYTHON, "Backend/main.py"])

# Start Streamlit frontend
def run_streamlit():
    subprocess.run([VENV_PYTHON, "-m", "streamlit", "run", "frontend/app.py"])


    
# Run both servers in separate threads
flask_thread = threading.Thread(target=run_flask)
streamlit_thread = threading.Thread(target=run_streamlit)

flask_thread.start()
# Wait a bit so Streamlit doesn't race on logs
time.sleep(2)
streamlit_thread.start()
