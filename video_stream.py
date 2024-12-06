from flask import Flask, Response, render_template_string
import cv2
import threading
import os
import zipfile
import requests
import subprocess
import platform
import mss
import numpy as np
import time

app = Flask(__name__)

def download_ngrok():
    try:
        if not os.path.exists('./ngrok.exe'):
            system = platform.system().lower()
            if system == 'windows':
                url = 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip'
            elif system == 'darwin':
                url = 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-amd64.zip'
            elif system == 'linux':
                url = 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip'
            else:
                raise Exception("Unsupported OS")

            response = requests.get(url)
            zip_path = 'ngrok.zip'
            with open(zip_path, 'wb') as file:
                file.write(response.content)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall()

            os.remove(zip_path)
    except Exception as e:
            print(f"Erreur lors du téléchargement de Ngrok : {e}")

def run_ngrok():
    try:
        processp = subprocess.Popen(['./ngrok', 'http', '5000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Ngrok lancé via script.")
    except Exception as e:
        print(f"Erreur lors du lancement de Ngrok : {e}")

def setup_ngrok():
    if not os.path.exists('./ngrok.exe'):
        download_ngrok()
    run_ngrok()

def get_ngrok_url():
    for _ in range(10):  # Réessaie plusieurs fois
        try:
            response = requests.get("http://127.0.0.1:4040/api/tunnels")
            data = response.json()
            public_url = data['tunnels'][0]['public_url']
            print(f"Ngrok public URL: {public_url}")
            return public_url
        except Exception as e:
            print(f"Waiting for Ngrok to be ready... {e}")
            time.sleep(2)
    raise Exception("Ngrok URL could not be retrieved.")


def generate_frames():
    camera = cv2.VideoCapture(0)  # 0 for the default webcam
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def generate_screen_frames():
    with mss.mss() as sct:
        while True:
            screen = sct.grab(sct.monitors[0])
            frame = np.array(screen)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Stream</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; }
            button { margin: 10px; padding: 10px 20px; font-size: 16px; }
            #stream { display: none; }
        </style>
    </head>
    <body>
        <h1>Video Stream</h1>
        <button onclick="showStream('webcam')">Webcam Stream</button>
        <button onclick="showStream('screen')">Screen Stream</button>
        <div id="stream">
            <img id="streamImg" width="640" height="480">
        </div>
        <script>
            function showStream(type) {
                const streamDiv = document.getElementById('stream');
                const streamImg = document.getElementById('streamImg');
                streamDiv.style.display = 'block';
                if (type === 'webcam') {
                    streamImg.src = "{{ url_for('video_feed') }}";
                } else if (type === 'screen') {
                    streamImg.src = "{{ url_for('screen_feed') }}";
                }
            }
        </script>
    </body>
    </html>
    """)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/screen_feed')
def screen_feed():
    return Response(generate_screen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    
    ngrok_thread = threading.Thread(target=setup_ngrok)
    ngrok_thread.start()
    print('Ngrok is starting...')
    time.sleep(2)  # Allow time for Ngrok to initialize
    public_url = get_ngrok_url()
    if public_url:
        print(f"Public URL: {public_url}")
    threading.Thread(target=app.run(host='0.0.0.0', port=5000)).start()
    
